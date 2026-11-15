import asyncio
from uuid import UUID

import pytest

from src.application.services.retrieval_service import DEFAULT_DENSE_INDEX, RetrievalService
from src.applications.tillegal.retrieval.document_models import RetrievedEvidence
from src.applications.tillegal.retrieval.errors import ErrorCategory, RetrievalErrorDetail, RetrievalServiceError
from src.applications.tillegal.retrieval.retriever import RetrievalError
from tests.unit.applications.tillegal.retrieval.test_contracts import request
from tests.unit.applications.tillegal.retrieval.test_service import FakeChunks, FakeIndex, Unused, chunk_row


def dense_index(**changes):
    return {
        "id": str(UUID(int=90)),
        "index_name": DEFAULT_DENSE_INDEX,
        "index_version": "v1",
        "status": "READY",
        "updated_at": "2026-11-10T00:00:00Z",
        "provider": "sentence-transformers",
        "model_name": "intfloat/multilingual-e5-small",
        "embedding_dimension": 384,
        "distance_metric": "cosine",
        "metadata": {"normalized": True, "query_prefix": "query: ", "passage_prefix": "passage: "},
        **changes,
    }


def dense_hit(number=1, similarity=0.8, **changes):
    c = chunk_row(number)
    return RetrievedEvidence.model_validate(
        {
            **{
                key: c[key]
                for key in ("source_document_id", "document_structure_id", "chunk_key", "content", "chunk_type")
            },
            "retrieval_chunk_id": c["id"],
            "dense_index_id": str(UUID(int=90)),
            "similarity": similarity,
            "node_id": None,
            "block_id": None,
            "start_offset": None,
            "end_offset": None,
            "chunk_metadata": c["metadata"],
            "source_id": "vbpl",
            "source_record_id": "demo",
            "source_snapshot_id": None,
            "title": "Demo",
            "language": "vi",
            "source_url": None,
            "issued_on": None,
            "effective_from": None,
            "effective_to": None,
            "effect_status_reported": None,
            "usage_policy": "EXPERIMENTAL_ONLY",
            "source_metadata": {},
            **changes,
        }
    )


class FakeEncoder:
    def __init__(self, vector=None, error=None):
        self.vector = (1.0,) + (0.0,) * 383 if vector is None else vector
        self.error = error
        self.calls = []

    async def encode_query(self, query):
        self.calls.append(query)
        if self.error:
            raise self.error
        return self.vector


class FakeDense:
    def __init__(self, hits=(), error=None):
        self.hits = hits
        self.error = error
        self.calls = []

    async def search(self, req):
        self.calls.append(req)
        if self.error:
            raise self.error
        return self.hits


def dense_service(hits=(), indexes=None, encoder=None, chunks=None, error=None):
    encoder = encoder or FakeEncoder()
    dense = FakeDense(hits, error)
    chunks = chunks or FakeChunks((chunk_row(1), chunk_row(2)))
    svc = RetrievalService(
        Unused(),
        chunks,
        Unused(),
        Unused(),
        Unused(),
        dense_retriever=dense,
        query_embedder=encoder,
        dense_indexes=indexes or FakeIndex(before=dense_index()),
    )
    return svc, dense, encoder, chunks


def test_dense_mapping_integrity_ranking_and_filters():
    svc, dense, encoder, chunks = dense_service((dense_hit(2, 0.85), dense_hit(1, 0.8)))
    result = asyncio.run(svc.search(request(query="  Hợp đồng? ", mode="dense", top_k=3)))
    assert result.status == "OK"
    assert encoder.calls == ["Hợp đồng?"]
    assert dense.calls[0].dense_index_name == DEFAULT_DENSE_INDEX
    assert len(dense.calls[0].query_embedding) == 384
    assert dense.calls[0].top_k == 3
    assert dense.calls[0].as_of_date == request().as_of_date
    assert dense.calls[0].allowed_usage_policies == ("EXPERIMENTAL_ONLY",)
    assert [e.retrieval_chunk_id.int for e in result.evidence] == [2, 1]
    assert [e.rank for e in result.evidence] == [1, 2]
    assert [e.raw_score for e in result.evidence] == [0.85, 0.8]
    assert all(e.hash_check == "MATCHED_STORED" and e.score_kind == "COSINE_SIMILARITY" for e in result.evidence)
    assert chunks.calls == [(UUID(int=2), UUID(int=1))]


def test_dense_no_match_does_not_fetch_chunks():
    svc, _, _, chunks = dense_service()
    assert asyncio.run(svc.search(request(mode="dense"))).status == "NO_MATCH"
    assert chunks.calls == []


@pytest.mark.parametrize(
    ("row", "code"),
    [
        (dense_index(status="STALE"), "INDEX_NOT_READY"),
        (dense_index(status="BUILDING"), "INDEX_NOT_READY"),
        (dense_index(model_name="other"), "INDEX_INCOMPATIBLE"),
        (dense_index(embedding_dimension=1536), "INDEX_INCOMPATIBLE"),
        (dense_index(distance_metric="l2"), "INDEX_INCOMPATIBLE"),
        (dense_index(metadata={}), "INDEX_INCOMPATIBLE"),
        ({"id": "bad"}, "INVALID_INDEX_METADATA"),
    ],
)
def test_dense_preflight_failure_before_encoder(row, code):
    svc, dense, encoder, _ = dense_service(indexes=FakeIndex(before=row))
    result = asyncio.run(svc.search(request(mode="dense")))
    assert result.error.code == code
    assert encoder.calls == dense.calls == []


def test_dense_missing_index():
    svc, _, encoder, _ = dense_service(indexes=FakeIndex(missing=True))
    assert asyncio.run(svc.search(request(mode="dense"))).error.code == "INDEX_NOT_FOUND"
    assert encoder.calls == []


@pytest.mark.parametrize("vector", [(0.1,) * 383, (0.0,) * 384, (1.0,) * 384, (float("nan"),) + (0.0,) * 383])
def test_bad_vector_blocks_rpc(vector):
    svc, dense, _, _ = dense_service(encoder=FakeEncoder(vector))
    assert asyncio.run(svc.search(request(mode="dense"))).error.code == "INVALID_EMBEDDING"
    assert dense.calls == []


def test_model_failure_is_classified_without_raw_message():
    error = RetrievalServiceError(
        RetrievalErrorDetail(
            category=ErrorCategory.MODEL_UNAVAILABLE,
            code="MODEL_LOAD_FAILED",
            stage="encoding",
            message="Safe model failure",
        )
    )
    svc, dense, _, _ = dense_service(encoder=FakeEncoder(error=error))
    assert asyncio.run(svc.search(request(mode="dense"))).error.category == "MODEL_UNAVAILABLE"
    assert dense.calls == []


@pytest.mark.parametrize(
    "hits",
    [
        (dense_hit(), dense_hit()),
        (dense_hit(1, 0.1), dense_hit(2, 0.9)),
        (dense_hit(similarity=1.2),),
        (dense_hit(dense_index_id=str(UUID(int=91))),),
        ({"unexpected": "shape"},),
    ],
)
def test_invalid_dense_hits(hits):
    svc, _, _, _ = dense_service(hits)
    result = asyncio.run(svc.search(request(mode="dense")))
    assert result.status == "FAILED" and result.error.category == "INCONSISTENT_EVIDENCE"
    assert result.evidence == ()


@pytest.mark.parametrize(
    "changes",
    [{"usage_policy": "OTHER"}, {"effective_from": "2026-12-01"}, {"effective_to": "2026-01-01"}, {"title": " "}],
)
def test_dense_source_filters_and_metadata(changes):
    svc, _, _, _ = dense_service((dense_hit(**changes),), chunks=FakeChunks((chunk_row(),)))
    assert asyncio.run(svc.search(request(mode="dense"))).status == "FAILED"


@pytest.mark.parametrize(
    ("rows", "code"),
    [
        ((), "CHUNK_IDENTITY_MISMATCH"),
        ((chunk_row(content_sha256="0" * 64),), "CONTENT_HASH_MISMATCH"),
        ((chunk_row(content="changed"),), "DENSE_CHUNK_CHANGED"),
        ((chunk_row(source_document_id=str(UUID(int=99))),), "DENSE_CHUNK_CHANGED"),
    ],
)
def test_dense_stored_integrity(rows, code):
    svc, _, _, _ = dense_service((dense_hit(),), chunks=FakeChunks(rows))
    assert asyncio.run(svc.search(request(mode="dense"))).error.code == code


def test_dense_postflight_change_and_network_error():
    svc, _, _, _ = dense_service(indexes=FakeIndex(before=dense_index(), after=dense_index(status="STALE")))
    assert asyncio.run(svc.search(request(mode="dense"))).error.code == "INDEX_CHANGED_DURING_SEARCH"
    svc, _, _, _ = dense_service(error=RetrievalError("private upstream message"))
    result = asyncio.run(svc.search(request(mode="dense")))
    assert result.error.category == "DATABASE_FAILURE"
    assert "private" not in result.model_dump_json()
