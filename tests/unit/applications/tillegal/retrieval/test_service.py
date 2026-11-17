import asyncio
import hashlib
from copy import deepcopy
from uuid import UUID

import pytest
from pydantic import ValidationError

from src.application.services.retrieval_service import DEFAULT_SPARSE_INDEX, RetrievalService
from src.application.services.vbpl_markdown_indexing_service import tokenize_sparse_text
from src.applications.tillegal.retrieval.document_models import SparseSearchHit
from src.integrations.database.repositories.rpc import DatabaseRepositoryError
from tests.unit.applications.tillegal.retrieval.test_contracts import request


def index_row(**changes):
    return {
        "id": str(UUID(int=20)),
        "index_name": DEFAULT_SPARSE_INDEX,
        "index_version": "v1",
        "status": "READY",
        "updated_at": "2026-11-10T00:00:00Z",
        "algorithm": "BM25",
        "tokenizer": "unicode-nfc-lower-v1",
        "language_config": "simple",
        "k1": 1.2,
        "b": 0.75,
        "document_count": 2,
        "total_token_count": 10,
        "average_document_length": 5,
        "metadata": {},
        **changes,
    }


class FakeIndex:
    def __init__(self, before=None, after=None, *, missing=False, error=None):
        self.before = None if missing else index_row() if before is None else before
        self.after = self.before if after is None else after
        self.error = error
        self.calls = []

    async def get_index(self, name):
        self.calls.append(name)
        if self.error:
            raise self.error
        return deepcopy(self.before if len(self.calls) == 1 else self.after)


class Unused:
    def __getattr__(self, name):
        raise AssertionError(f"Unexpected dependency call: {name}")


class FakeSparse:
    def __init__(self, hits=(), error=None):
        self.hits = hits
        self.error = error
        self.requests = []

    async def search(self, req):
        self.requests.append(req)
        if self.error:
            raise self.error
        return self.hits


def service(indexes=None, sparse=None):
    return RetrievalService(sparse or FakeSparse(), Unused(), Unused(), indexes or FakeIndex(), tokenize_sparse_text)


@pytest.mark.parametrize(
    ("indexes", "code"),
    [
        (FakeIndex(missing=True), "INDEX_NOT_FOUND"),
        (FakeIndex(before=index_row(status="STALE")), "INDEX_NOT_READY"),
        (FakeIndex(before=index_row(status="BUILDING")), "INDEX_NOT_READY"),
        (FakeIndex(before=index_row(status="FAILED")), "INDEX_NOT_READY"),
        (FakeIndex(before=index_row(status="DISABLED")), "INDEX_NOT_READY"),
        (FakeIndex(before=index_row(tokenizer="other")), "INDEX_INCOMPATIBLE"),
        (FakeIndex(before=index_row(algorithm="other")), "INDEX_INCOMPATIBLE"),
        (FakeIndex(before=index_row(index_version="v2")), "INDEX_INCOMPATIBLE"),
        (FakeIndex(before=index_row(document_count=0)), "INDEX_EMPTY"),
        (FakeIndex(before={"id": "bad"}), "INVALID_INDEX_METADATA"),
        (FakeIndex(after=index_row(status="STALE")), "INDEX_CHANGED_DURING_SEARCH"),
        (FakeIndex(after=index_row(updated_at="2026-11-11T00:00:00Z")), "INDEX_CHANGED_DURING_SEARCH"),
        (FakeIndex(error=DatabaseRepositoryError("secret upstream diagnostic")), "DATABASE_READ_FAILED"),
    ],
)
def test_index_failures(indexes, code):
    result = asyncio.run(service(indexes).search(request()))
    assert result.status == "FAILED"
    assert result.error.code == code
    assert "secret" not in result.model_dump_json()
    assert result.consistency == "BEST_EFFORT"


def test_dense_not_configured_without_reads():
    indexes = FakeIndex()
    result = asyncio.run(service(indexes).search(request(mode="dense")))
    assert result.error.code == "MODE_NOT_CONFIGURED"
    assert indexes.calls == []


def test_invalid_request_makes_no_calls():
    indexes = FakeIndex()
    with pytest.raises(ValidationError):
        asyncio.run(service(indexes).search({"query": ""}))
    assert indexes.calls == []


@pytest.mark.parametrize(
    ("query", "terms"),
    [
        ("Thuế thuế, Điều 7.", ("thuế", "điều", "7")),
        ("THUE\u0302\u0301_thuế 123", ("thuế", "123")),
        ("Không được bỏ dấu!", ("không", "được", "bỏ", "dấu")),
    ],
)
def test_real_indexing_tokenizer_and_parameter_mapping(query, terms):
    sparse = FakeSparse()
    indexes = FakeIndex()
    req = request(query=query, top_k=3, allowed_usage_policies=["A", "B"])
    result = asyncio.run(service(indexes, sparse).search(req))
    assert result.status == "NO_MATCH"
    assert sparse.requests[0].terms == terms
    assert sparse.requests[0].top_k == 3
    assert sparse.requests[0].as_of_date == req.as_of_date
    assert sparse.requests[0].allowed_usage_policies == ("A", "B")
    assert sparse.requests[0].sparse_index_name == DEFAULT_SPARSE_INDEX
    assert indexes.calls == [DEFAULT_SPARSE_INDEX] * 2


def test_empty_terms_without_db_reads():
    indexes = FakeIndex()
    sparse = FakeSparse()
    result = asyncio.run(service(indexes, sparse).search(request(query=" _ --- ! ")))
    assert result.error.code == "EMPTY_TERMS"
    assert indexes.calls == sparse.requests == []


def test_sparse_hits_keep_original_order_and_scores():
    hits = (
        SparseSearchHit(retrieval_chunk_id=UUID(int=2), score=7.2),
        SparseSearchHit(retrieval_chunk_id=UUID(int=1), score=5.4),
    )
    sparse = FakeSparse(hits)
    result = asyncio.run(service(sparse=sparse)._search_sparse(request(), ("thuế",)))
    assert result == hits


def test_sparse_failure_is_not_no_match():
    result = asyncio.run(service(sparse=FakeSparse(error=DatabaseRepositoryError("private"))).search(request()))
    assert result.status == "FAILED"
    assert result.error.category == "DATABASE_FAILURE"
    assert result.error.stage == "search"


def chunk_row(number=1, **changes):
    content = f"Demo > Điều 1 > Thuế {number}."
    return {
        "id": str(UUID(int=number)),
        "source_document_id": str(UUID(int=30)),
        "document_structure_id": str(UUID(int=40)),
        "chunk_key": f"chunk-{number}",
        "content": content,
        "content_sha256": hashlib.sha256(content.encode()).hexdigest(),
        "chunk_type": "text",
        "metadata": {"breadcrumb": "Demo > Điều 1"},
        **changes,
    }


def source_row(**changes):
    return {
        "id": str(UUID(int=30)),
        "title": "Demo",
        "usage_policy": "EXPERIMENTAL_ONLY",
        "raw_metadata": {},
        "effective_from": "2026-01-01",
        "effective_to": None,
        **changes,
    }


class FakeChunks:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    async def get_by_ids(self, ids):
        self.calls.append(ids)
        return self.rows


class FakeSources:
    def __init__(self, row):
        self.row = row
        self.calls = []

    async def get(self, source_id):
        self.calls.append(source_id)
        return self.row


def hydrated_service(rows=None, source=None, hits=None, indexes=None):
    if hits is None:
        hits = (
            SparseSearchHit(retrieval_chunk_id=UUID(int=2), score=7.2),
            SparseSearchHit(retrieval_chunk_id=UUID(int=1), score=5.4),
        )
    chunks = FakeChunks((chunk_row(1), chunk_row(2)) if rows is None else rows)
    sources = FakeSources(source_row() if source is None else source)
    svc = RetrievalService(FakeSparse(hits), chunks, sources, indexes or FakeIndex(), tokenize_sparse_text)
    return svc, chunks, sources


def test_hydration_preserves_ranking_hash_and_reads_source_once():
    svc, chunks, sources = hydrated_service()
    result = asyncio.run(svc.search(request()))
    assert result.status == "OK"
    assert [e.retrieval_chunk_id.int for e in result.evidence] == [2, 1]
    assert [e.raw_score for e in result.evidence] == [7.2, 5.4]
    assert [e.rank for e in result.evidence] == [1, 2]
    assert all(e.score_kind == "BM25" and e.hash_check == "MATCHED_STORED" for e in result.evidence)
    assert all(e.source_url is None and e.effective_to is None for e in result.evidence)
    assert sources.calls == [UUID(int=30)]
    assert chunks.calls == [(UUID(int=2), UUID(int=1))]
    assert {w.code for w in result.warnings} == {"SOURCE_URL_MISSING", "TEMPORAL_METADATA_INCOMPLETE"}


@pytest.mark.parametrize(
    ("rows", "code"),
    [
        ((), "CHUNK_IDENTITY_MISMATCH"),
        ((chunk_row(1), chunk_row(1)), "CHUNK_IDENTITY_MISMATCH"),
        ((chunk_row(1), chunk_row(9)), "CHUNK_IDENTITY_MISMATCH"),
        ((chunk_row(1), chunk_row(2, id="invalid")), "INVALID_CHUNK"),
        ((chunk_row(1), chunk_row(2, content_sha256="0" * 64)), "CONTENT_HASH_MISMATCH"),
        ((chunk_row(1), chunk_row(2, start_offset=10, end_offset=1)), "INVALID_EVIDENCE"),
        ((chunk_row(1), chunk_row(2, metadata=None)), "INVALID_CHUNK"),
    ],
)
def test_bad_chunks_fail_without_partial_evidence(rows, code):
    svc, _, _ = hydrated_service(rows=rows)
    result = asyncio.run(svc.search(request()))
    assert result.status == "FAILED"
    assert result.error.code == code
    assert result.evidence == ()


@pytest.mark.parametrize(
    ("source", "code"),
    [
        (source_row(id=str(UUID(int=31))), "SOURCE_IDENTITY_MISMATCH"),
        (source_row(title=" "), "INVALID_EVIDENCE"),
        (source_row(raw_metadata=None), "INVALID_SOURCE"),
        (source_row(usage_policy="DISALLOWED"), "ELIGIBILITY_CHANGED"),
        (source_row(effective_from="2026-11-11"), "ELIGIBILITY_CHANGED"),
        (source_row(effective_to="2026-11-09"), "ELIGIBILITY_CHANGED"),
        (source_row(effective_from="2026-12-01", effective_to="2026-01-01"), "INVALID_EFFECTIVE_DATES"),
    ],
)
def test_bad_sources_fail(source, code):
    svc, _, _ = hydrated_service(source=source)
    result = asyncio.run(svc.search(request()))
    assert result.error.code == code
    assert result.evidence == ()


def test_missing_source():
    svc, _, sources = hydrated_service()
    sources.row = None
    assert asyncio.run(svc.search(request())).error.code == "SOURCE_MISSING"


def test_duplicate_hits_block_hydration():
    hit = SparseSearchHit(retrieval_chunk_id=UUID(int=1), score=1)
    svc, chunks, sources = hydrated_service(hits=(hit, hit))
    assert asyncio.run(svc.search(request())).error.code == "DUPLICATE_HITS"
    assert chunks.calls == sources.calls == []


def test_dates_are_inclusive_and_nullable():
    for dates in (
        {"effective_from": "2026-11-10", "effective_to": "2026-11-10"},
        {"effective_from": None, "effective_to": None},
    ):
        svc, _, _ = hydrated_service(source=source_row(**dates))
        assert asyncio.run(svc.search(request())).status == "OK"


def test_postflight_change_discards_hydrated_results():
    svc, _, _ = hydrated_service(indexes=FakeIndex(after=index_row(document_count=3)))
    result = asyncio.run(svc.search(request()))
    assert result.error.code == "INDEX_CHANGED_DURING_SEARCH"
    assert result.evidence == ()


def test_timeout_is_not_no_match():
    class SlowIndex:
        async def get_index(self, name):
            await asyncio.sleep(1)

    svc = RetrievalService(Unused(), Unused(), Unused(), SlowIndex(), tokenize_sparse_text, timeout_seconds=0.001)
    result = asyncio.run(svc.search(request()))
    assert result.error.category == "TIMEOUT"
    assert result.status == "FAILED"


def test_invalid_repository_schema_cause_is_classified():
    try:
        SparseSearchHit.model_validate({})
    except ValidationError as cause:
        failure = DatabaseRepositoryError("sensitive raw response")
        failure.__cause__ = cause
    result = asyncio.run(service(sparse=FakeSparse(error=failure)).search(request()))
    assert result.error.code == "INVALID_REPOSITORY_RESPONSE"
    assert "sensitive" not in result.model_dump_json()
