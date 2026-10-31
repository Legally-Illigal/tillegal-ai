"""Tests for the Supabase vector-search repository."""

import asyncio
from datetime import date
from typing import Any

import httpx
import pytest
from pydantic import ValidationError

from src.applications.tillegal.retrieval.document_models import VectorSearchRequest
from src.applications.tillegal.retrieval.retriever import RetrievalError
from src.integrations.database.repositories.supabase_vector_repository import SupabaseVectorRepository


def _request(**overrides: Any) -> VectorSearchRequest:
    values: dict[str, Any] = {
        "dense_index_name": "legal-v1",
        "query_embedding": [0.1] * 1536,
        "as_of_date": date(2026, 10, 31),
        "allowed_legal_approvals": ["APPROVED"],
        "allowed_usage_policies": ["PRODUCTION"],
        "allowed_provenance_statuses": ["VERIFIED"],
        "allowed_temporal_statuses": ["IN_FORCE"],
        "allowed_rights_statuses": ["CLEARED"],
    }
    values.update(overrides)
    return VectorSearchRequest.model_validate(values)


def _evidence_row() -> dict[str, object]:
    return {
        "retrieval_chunk_id": "00000000-0000-0000-0000-000000000001",
        "source_document_id": "00000000-0000-0000-0000-000000000002",
        "document_structure_id": "00000000-0000-0000-0000-000000000003",
        "dense_index_id": "00000000-0000-0000-0000-000000000004",
        "chunk_key": "article-1-paragraph-1",
        "content": "Legal source text.",
        "similarity": 0.91,
        "node_id": "article-1",
        "block_id": "paragraph-1",
        "chunk_type": "text",
        "start_offset": 0,
        "end_offset": 17,
        "chunk_metadata": {},
        "source_id": "official-gazette",
        "source_record_id": "record-1",
        "source_snapshot_id": "snapshot-1",
        "document_number": "01/2026",
        "title": "Test legal document",
        "document_type": "LAW",
        "issuing_authority": "National Assembly",
        "language": "vi",
        "source_url": "https://example.test/law",
        "issued_on": "2026-01-01",
        "effective_from": "2026-02-01",
        "effective_to": None,
        "effect_status_reported": "IN_FORCE",
        "usage_policy": "PRODUCTION",
        "legal_approval": "APPROVED",
        "provenance_status": "VERIFIED",
        "temporal_status": "IN_FORCE",
        "rights_status": "CLEARED",
        "source_metadata": {},
    }


class _FakeResponse:
    def __init__(self, data: object) -> None:
        self.data = data


class _FakeQuery:
    def __init__(self, response: _FakeResponse | Exception) -> None:
        self._response = response

    def execute(self) -> _FakeResponse:
        if isinstance(self._response, Exception):
            raise self._response
        return self._response


class _FakeClient:
    def __init__(self, response: _FakeResponse | Exception) -> None:
        self.response = response
        self.function_name: str | None = None
        self.parameters: dict[str, object] | None = None

    def rpc(self, function_name: str, parameters: dict[str, object]) -> _FakeQuery:
        self.function_name = function_name
        self.parameters = parameters
        return _FakeQuery(self.response)


def test_search_calls_rpc_with_embedding_and_explicit_allowlists() -> None:
    client = _FakeClient(_FakeResponse([_evidence_row()]))
    repository = SupabaseVectorRepository(client)  # type: ignore[arg-type]

    results = asyncio.run(repository.search(_request()))

    assert client.function_name == "search_legal_chunks"
    assert client.parameters is not None
    assert client.parameters["p_query_embedding"] == f"[{','.join(['0.1'] * 1536)}]"
    assert client.parameters["p_as_of_date"] == "2026-10-31"
    assert client.parameters["p_legal_approvals"] == ["APPROVED"]
    assert client.parameters["p_usage_policies"] == ["PRODUCTION"]
    assert client.parameters["p_provenance_statuses"] == ["VERIFIED"]
    assert client.parameters["p_temporal_statuses"] == ["IN_FORCE"]
    assert client.parameters["p_rights_statuses"] == ["CLEARED"]
    assert len(results) == 1
    assert results[0].content == "Legal source text."
    assert results[0].effective_from == date(2026, 2, 1)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("query_embedding", [0.1] * 1535),
        ("query_embedding", [0.0] * 1536),
        ("allowed_legal_approvals", []),
        ("allowed_usage_policies", ["  "]),
        ("allowed_provenance_statuses", [None]),
        ("allowed_temporal_statuses", []),
        ("allowed_rights_statuses", []),
        ("top_k", 51),
    ],
)
def test_search_request_rejects_invalid_values(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        _request(**{field: value})


def test_search_maps_supabase_transport_failures() -> None:
    request = httpx.Request("POST", "https://example.supabase.co/rest/v1/rpc/search_legal_chunks")
    client = _FakeClient(httpx.ConnectError("offline", request=request))
    repository = SupabaseVectorRepository(client)  # type: ignore[arg-type]

    with pytest.raises(RetrievalError, match="Supabase legal-document search failed"):
        asyncio.run(repository.search(_request()))


def test_search_rejects_invalid_rpc_response_contract() -> None:
    client = _FakeClient(_FakeResponse([{"unexpected": "shape"}]))
    repository = SupabaseVectorRepository(client)  # type: ignore[arg-type]

    with pytest.raises(RetrievalError, match="violates the retrieval contract"):
        asyncio.run(repository.search(_request()))
