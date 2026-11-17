import asyncio
from copy import deepcopy
from uuid import UUID

import pytest
from pydantic import ValidationError

from src.application.services.retrieval_service import RetrievalService
from src.application.services.vbpl_markdown_indexing_service import tokenize_sparse_text
from src.applications.tillegal.retrieval.document_models import SparseSearchHit
from src.applications.tillegal.retrieval.hybrid_models import HybridConfig, HybridRetrievalResponse
from src.applications.tillegal.retrieval.retriever import RetrievalError
from src.integrations.database.repositories.rpc import DatabaseRepositoryError
from tests.unit.applications.tillegal.retrieval.test_contracts import request
from tests.unit.applications.tillegal.retrieval.test_dense_service import FakeDense, FakeEncoder, dense_hit, dense_index
from tests.unit.applications.tillegal.retrieval.test_service import (
    FakeIndex,
    FakeSources,
    FakeSparse,
    chunk_row,
    source_row,
)


class SelectedChunks:
    def __init__(self):
        self.rows = {UUID(int=n): chunk_row(n) for n in (1, 2, 3)}
        self.calls = []

    async def get_by_ids(self, ids):
        self.calls.append(ids)
        return tuple(deepcopy(self.rows[cid]) for cid in reversed(ids) if cid in self.rows)


def hybrid_service(
    *,
    sparse_hits=None,
    dense_hits=None,
    sparse_error=None,
    dense_error=None,
    sparse_indexes=None,
    encoder=None,
    config=None,
    timeout=30,
):
    sparse = FakeSparse(
        (
            SparseSearchHit(retrieval_chunk_id=UUID(int=1), score=7.2),
            SparseSearchHit(retrieval_chunk_id=UUID(int=2), score=5.4),
        )
        if sparse_hits is None
        else sparse_hits,
        sparse_error,
    )
    dense = FakeDense((dense_hit(2, 0.85), dense_hit(3, 0.8)) if dense_hits is None else dense_hits, dense_error)
    indexes = sparse_indexes or FakeIndex()
    d_indexes = FakeIndex(before=dense_index())
    enc = encoder or FakeEncoder()
    chunks = SelectedChunks()
    sources = FakeSources(source_row(effective_from=None, source_id="vbpl", source_record_id="demo", language="vi"))
    svc = RetrievalService(
        sparse,
        chunks,
        sources,
        indexes,
        tokenize_sparse_text,
        dense_retriever=dense,
        query_embedder=enc,
        dense_indexes=d_indexes,
        hybrid_config=config,
        timeout_seconds=timeout,
    )
    return svc, sparse, dense, enc, indexes, d_indexes, chunks


def test_real_service_branches_fuse_with_metadata_and_independent_candidate_limits():
    svc, sparse, dense, encoder, sindexes, dindexes, _ = hybrid_service(
        config=HybridConfig(bm25_candidates=3, dense_candidates=4)
    )
    result = asyncio.run(svc.search(request(mode="hybrid", top_k=2)))
    assert isinstance(result, HybridRetrievalResponse)
    assert result.status == "OK" and result.index is None
    assert [e.retrieval_chunk_id.int for e in result.evidence] == [2, 1]
    assert result.evidence[0].raw_score == pytest.approx(1 / 62 + 1 / 61)
    assert sparse.requests[0].top_k == 3 and dense.calls[0].top_k == 4
    assert sparse.requests[0].as_of_date == dense.calls[0].as_of_date == request().as_of_date
    assert sparse.requests[0].allowed_usage_policies == dense.calls[0].allowed_usage_policies
    assert encoder.calls == [request().query.strip()]
    assert len(sindexes.calls) == len(dindexes.calls) == 3
    assert [b.backend for b in result.fusion.branches] == ["bm25", "dense"]
    assert result.fusion.failure_policy == "STRICT"
    assert all(w.retrieval_chunk_id in {e.retrieval_chunk_id for e in result.evidence} for w in result.warnings)
    assert HybridRetrievalResponse.model_validate_json(result.model_dump_json()) == result


@pytest.mark.parametrize(
    ("sparse_empty", "dense_empty", "status"), [(True, False, "OK"), (False, True, "OK"), (True, True, "NO_MATCH")]
)
def test_empty_is_valid_not_a_backend_failure(sparse_empty, dense_empty, status):
    svc, *_ = hybrid_service(sparse_hits=() if sparse_empty else None, dense_hits=() if dense_empty else None)
    result = asyncio.run(svc.search(request(mode="hybrid")))
    assert result.status == status and result.error is None
    assert [b.status for b in result.fusion.branches] == [
        "NO_MATCH" if sparse_empty else "OK",
        "NO_MATCH" if dense_empty else "OK",
    ]


@pytest.mark.parametrize("backend", ["bm25", "dense"])
def test_backend_failure_never_becomes_degraded_success(backend):
    svc, sparse, dense, _, _, _, _ = hybrid_service(
        sparse_error=DatabaseRepositoryError("private") if backend == "bm25" else None,
        dense_error=RetrievalError("private") if backend == "dense" else None,
    )
    result = asyncio.run(svc.search(request(mode="hybrid")))
    assert result.status == "FAILED" and result.error.category == "DATABASE_FAILURE"
    assert result.error.stage.startswith(backend + ".")
    assert result.evidence == result.fusion.ranking == ()
    assert "private" not in result.model_dump_json()
    if backend == "bm25":
        assert dense.calls == []


def test_bad_embedding_stops_hybrid_before_vector_rpc():
    svc, _, dense, _, _, _, _ = hybrid_service(encoder=FakeEncoder((0.0,) * 384))
    result = asyncio.run(svc.search(request(mode="hybrid")))
    assert result.error.code == "INVALID_EMBEDDING" and result.error.category == "MODEL_UNAVAILABLE"
    assert dense.calls == [] and result.evidence == ()


def test_missing_local_checkpoint_is_not_no_match(tmp_path):
    from src.integrations.embeddings.e5_query_encoder import E5QueryEncoder

    svc, _, dense, _, _, _, _ = hybrid_service(encoder=E5QueryEncoder(tmp_path / "missing"))
    result = asyncio.run(svc.search(request(mode="hybrid")))
    assert result.error.code == "MODEL_NOT_PROVISIONED" and result.evidence == ()
    assert dense.calls == []


def test_integrity_failure_never_reaches_fusion():
    svc, _, dense, _, _, _, chunks = hybrid_service()
    chunks.rows[UUID(int=1)]["content_sha256"] = "0" * 64
    result = asyncio.run(svc.search(request(mode="hybrid")))
    assert result.error.code == "CONTENT_HASH_MISMATCH"
    assert dense.calls == [] and result.evidence == ()


def test_same_chunk_conflicting_source_metadata_blocks_fusion():
    svc, *_ = hybrid_service(dense_hits=(dense_hit(2, title="different source title"),))
    result = asyncio.run(svc.search(request(mode="hybrid")))
    assert result.error.code == "CROSS_BACKEND_EVIDENCE_CONFLICT"
    assert result.error.category == "INCONSISTENT_EVIDENCE"
    assert result.evidence == ()


def test_closing_index_check_covers_interval_between_branches():
    class ChangedIndex(FakeIndex):
        async def get_index(self, name):
            row = await super().get_index(name)
            if len(self.calls) == 3:
                row["updated_at"] = "2026-11-11T00:00:00Z"
            return row

    svc, *_ = hybrid_service(sparse_indexes=ChangedIndex())
    result = asyncio.run(svc.search(request(mode="hybrid")))
    assert result.error.code == "INDEX_CHANGED_DURING_HYBRID"
    assert result.evidence == ()


def test_hybrid_index_unavailable_stops_dense():
    svc, _, dense, *_ = hybrid_service(sparse_indexes=FakeIndex(missing=True))
    result = asyncio.run(svc.search(request(mode="hybrid")))
    assert result.error.category == "INDEX_UNAVAILABLE" and dense.calls == []


def test_outer_timeout_does_not_return_first_branch_hits():
    svc, _, dense, *_ = hybrid_service(timeout=0.01)

    async def slow(req):
        await asyncio.sleep(1)

    dense.search = slow
    result = asyncio.run(svc.search(request(mode="hybrid")))
    assert result.error.category == "TIMEOUT" and result.evidence == ()


def test_single_backend_payloads_keep_original_shape():
    svc, *_ = hybrid_service()
    for mode in ("bm25", "dense"):
        result = asyncio.run(svc.search(request(mode=mode)))
        assert result.status == "OK"
        assert "fusion" not in result.model_dump()


def test_closing_read_failure_is_not_no_match():
    class FailedClosing(FakeIndex):
        async def get_index(self, name):
            if len(self.calls) == 2:
                raise DatabaseRepositoryError("private diagnostic")
            return await super().get_index(name)

    svc, *_ = hybrid_service(sparse_indexes=FailedClosing())
    result = asyncio.run(svc.search(request(mode="hybrid")))
    assert result.error.category == "DATABASE_FAILURE" and result.evidence == ()
    assert "private" not in result.model_dump_json()


def test_branch_context_mismatch_is_an_integrity_failure():
    svc, *_ = hybrid_service()
    original = svc.search

    async def changed(req):
        result = await original(req)
        return result.model_copy(update={"as_of_date": request(as_of_date="2026-11-11").as_of_date})

    from src.application.services.hybrid_retrieval import search_hybrid

    result = asyncio.run(
        search_hybrid(
            request(mode="hybrid"),
            run_branch=changed,
            sparse_indexes=svc._indexes,
            dense_indexes=svc._dense_indexes,
            sparse_index_name=svc._index_name,
            dense_index_name=svc._dense_index_name,
            dense_configured=True,
            config=HybridConfig(),
            timeout_seconds=30,
        )
    )
    assert result.error.code == "BRANCH_CONTEXT_MISMATCH" and result.evidence == ()


def test_source_filter_failure_is_not_hidden_by_other_backend():
    svc, _, dense, *_ = hybrid_service()
    svc._sources.row["usage_policy"] = "NOT_ALLOWED"
    result = asyncio.run(svc.search(request(mode="hybrid")))
    assert result.error.code == "ELIGIBILITY_CHANGED" and result.evidence == ()
    assert dense.calls == []


@pytest.mark.parametrize("tamper", ["score", "rank", "budget", "no_match"])
def test_hybrid_explanation_contract_rejects_tampering(tamper):
    svc, *_ = hybrid_service()
    result = asyncio.run(svc.search(request(mode="hybrid")))
    payload = result.model_dump()
    if tamper == "score":
        payload["evidence"][0]["raw_score"] += 0.1
    elif tamper == "rank":
        payload["fusion"]["ranking"][0]["contributions"][0]["rank"] = 99
    elif tamper == "budget":
        payload["fusion"]["branches"][0]["requested_candidates"] = 19
    elif tamper == "no_match":
        payload.update(status="NO_MATCH", evidence=())
        payload["fusion"]["ranking"] = ()
    with pytest.raises(ValidationError):
        HybridRetrievalResponse.model_validate(payload)
