from datetime import UTC, date, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from src.applications.tillegal.retrieval.contracts import RetrievalRequest, RetrievalResponse, UnifiedEvidence
from src.applications.tillegal.retrieval.document_models import SparseSearchHit, SparseSearchRequest
from src.applications.tillegal.retrieval.errors import ErrorCategory, RetrievalErrorDetail
from src.integrations.database.repositories.sparse_retrieval_repository import (
    SparseSearchHit as OldHit,
)
from src.integrations.database.repositories.sparse_retrieval_repository import (
    SparseSearchRequest as OldRequest,
)


def request(**changes):
    return RetrievalRequest.model_validate(
        {
            "query": "  Thuế  ",
            "mode": "bm25",
            "as_of_date": "2026-11-10",
            "allowed_usage_policies": ["EXPERIMENTAL_ONLY"],
            **changes,
        }
    )


def evidence(**changes):
    return UnifiedEvidence.model_validate(
        {
            "retrieval_chunk_id": UUID(int=1),
            "source_document_id": UUID(int=2),
            "document_structure_id": UUID(int=3),
            "chunk_key": "c1",
            "content": "thuế",
            "content_sha256": "a" * 64,
            "hash_check": "MATCHED_STORED",
            "rank": 1,
            "raw_score": 2.0,
            "score_kind": "BM25",
            "retrieval_method": "bm25",
            "node_id": None,
            "block_id": None,
            "chunk_type": "text",
            "start_offset": None,
            "end_offset": None,
            "chunk_metadata": {},
            "source_id": "vbpl",
            "source_record_id": "demo",
            "source_snapshot_id": None,
            "title": "Demo",
            "source_url": None,
            "language": "vi",
            "issued_on": None,
            "effective_from": None,
            "effective_to": None,
            "effect_status_reported": None,
            "usage_policy": "EXPERIMENTAL_ONLY",
            "source_metadata": {},
            **changes,
        }
    )


def response(**changes):
    req = request()
    return RetrievalResponse.model_validate(
        {
            **req.model_dump(),
            "request_id": UUID(int=10),
            "query_used": req.query.strip(),
            "selected_index_name": "bm25",
            "index": None,
            "status": "NO_MATCH",
            "retrieved_at": datetime.now(UTC),
            **changes,
        }
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"query": " "},
        {"query": "x" * 10001},
        {"query": 123},
        {"top_k": True},
        {"top_k": "3"},
        {"top_k": 0},
        {"top_k": 51},
        {"mode": "unsupported"},
        {"allowed_usage_policies": []},
        {"allowed_usage_policies": [" "]},
        {"unknown_filter": "x"},
    ],
)
def test_invalid_request(changes):
    with pytest.raises(ValidationError):
        request(**changes)


def test_required_date_and_policies():
    for missing in ("as_of_date", "allowed_usage_policies"):
        payload = request().model_dump()
        del payload[missing]
        with pytest.raises(ValidationError):
            RetrievalRequest.model_validate(payload)


def test_query_preserved_policies_deduplicated_and_serialization():
    req = request(allowed_usage_policies=[" A ", "A", "B"])
    assert req.query == "  Thuế  "
    assert req.allowed_usage_policies == ("A", "B")
    assert req.top_k == 10
    assert req.as_of_date == date(2026, 11, 10)
    assert RetrievalRequest.model_validate_json(req.model_dump_json()) == req


def test_old_sparse_imports_are_same_classes():
    assert OldHit is SparseSearchHit
    assert OldRequest is SparseSearchRequest
    req = OldRequest(
        sparse_index_name=" x ", terms=(" a ", "a"), as_of_date=date(2026, 11, 10), allowed_usage_policies=("A",)
    )
    assert req.terms == ("a",)
    assert req.sparse_index_name == "x"


@pytest.mark.parametrize(
    "changes",
    [
        {"status": "OK"},
        {"status": "FAILED"},
        {"evidence": (evidence(),)},
        {
            "error": RetrievalErrorDetail(
                category=ErrorCategory.DATABASE_FAILURE, code="RPC_FAILED", stage="search", message="Search failed"
            )
        },
        {"status": "OK", "evidence": (evidence(rank=2),)},
        {"status": "OK", "evidence": (evidence(), evidence(rank=2))},
    ],
)
def test_response_invariants(changes):
    with pytest.raises(ValidationError):
        response(**changes)


def test_success_and_failure_roundtrip():
    success = response(status="OK", evidence=(evidence(),))
    assert RetrievalResponse.model_validate_json(success.model_dump_json()) == success
    failure = response(
        status="FAILED",
        error=RetrievalErrorDetail(
            category=ErrorCategory.INDEX_UNAVAILABLE, code="INDEX_NOT_READY", stage="index", message="Not ready"
        ),
    )
    assert not failure.evidence


def test_score_kinds_cannot_be_mixed():
    with pytest.raises(ValidationError):
        evidence(score_kind="COSINE_SIMILARITY")
    assert evidence(retrieval_method="dense", score_kind="COSINE_SIMILARITY").raw_score == 2.0
