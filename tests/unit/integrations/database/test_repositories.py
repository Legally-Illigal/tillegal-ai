"""Unit tests for separated RAG database repositories."""

from __future__ import annotations

import asyncio
from datetime import date
from uuid import UUID

import httpx
import pytest
from pydantic import ValidationError

from src.integrations.database.repositories.dense_index_repository import (
    DenseEmbeddingStatusWrite,
    DenseEmbeddingWrite,
    DenseIndexRepository,
    DenseIndexWrite,
)
from src.integrations.database.repositories.parsed_document_repository import (
    DocumentBlockWrite,
    DocumentNodeWrite,
    DocumentStructureWrite,
    ParsedDocumentRepository,
    ParsedDocumentWrite,
    RetrievalChunkWrite,
)
from src.integrations.database.repositories.rpc import DatabaseRepositoryError
from src.integrations.database.repositories.source_document_repository import (
    SourceDocumentRepository,
    SourceDocumentWrite,
)
from src.integrations.database.repositories.sparse_index_repository import (
    SparseChunkWrite,
    SparseIndexRepository,
    SparseIndexWrite,
    SparsePostingWrite,
)
from src.integrations.database.repositories.sparse_retrieval_repository import (
    SparseRetrievalRepository,
    SparseSearchRequest,
)


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
        self.calls: list[tuple[str, dict[str, object]]] = []

    def rpc(self, function_name: str, parameters: dict[str, object]) -> _FakeQuery:
        self.calls.append((function_name, parameters))
        return _FakeQuery(self.response)


class _FakeTableQuery:
    def __init__(self, response: _FakeResponse) -> None:
        self.response = response

    def select(self, columns: str) -> _FakeTableQuery:
        return self

    def eq(self, column: str, value: str) -> _FakeTableQuery:
        return self

    def limit(self, count: int) -> _FakeTableQuery:
        return self

    def execute(self) -> _FakeResponse:
        return self.response


class _FakeTableClient(_FakeClient):
    def __init__(self, response: _FakeResponse) -> None:
        super().__init__(response)
        self.query = _FakeTableQuery(response)

    def table(self, name: str) -> _FakeTableQuery:
        return self.query


def test_source_document_repository_serializes_typed_upsert() -> None:
    client = _FakeClient(_FakeResponse({"id": "source-id"}))
    repository = SourceDocumentRepository(client)  # type: ignore[arg-type]
    document = SourceDocumentWrite(
        source_id="official-source",
        source_record_id="record-1",
        title="Legal document",
        issued_on=date(2026, 1, 2),
        raw_file_ref="vbpl-raw/path/document.pdf",
        raw_file_sha256="file-hash",
    )

    result = asyncio.run(repository.upsert(document))

    assert result == {"id": "source-id"}
    function_name, parameters = client.calls[0]
    assert function_name == "upsert_source_document"
    payload = parameters["p_document"]
    assert isinstance(payload, dict)
    assert payload["issued_on"] == "2026-01-02"
    assert payload["raw_file_ref"] == "vbpl-raw/path/document.pdf"
    assert payload["raw_file_sha256"] == "file-hash"


def test_source_document_repository_returns_none_for_empty_lookup() -> None:
    client = _FakeTableClient(_FakeResponse([]))
    repository = SourceDocumentRepository(client)  # type: ignore[arg-type]

    result = asyncio.run(repository.get_by_source_record_id("vbpl", "175384"))

    assert result is None


def test_source_document_repository_returns_matching_lookup_row() -> None:
    row = {"id": "source-id", "raw_metadata": {}}
    client = _FakeTableClient(_FakeResponse([row]))
    repository = SourceDocumentRepository(client)  # type: ignore[arg-type]

    result = asyncio.run(repository.get_by_source_record_id("vbpl", "175384"))

    assert result == row


def test_parsed_document_repository_uses_atomic_save_rpc() -> None:
    expected_id = "00000000-0000-0000-0000-000000000001"
    client = _FakeClient(_FakeResponse(expected_id))
    repository = ParsedDocumentRepository(client)  # type: ignore[arg-type]
    parsed_document = ParsedDocumentWrite(
        structure=DocumentStructureWrite(
            source_document_id=UUID("00000000-0000-0000-0000-000000000002"),
            schema_version="v1",
            parser_version="v1",
            content_sha256="doc-hash",
        ),
        nodes=(DocumentNodeWrite(node_id="article-1", kind="article"),),
        blocks=(DocumentBlockWrite(block_id="block-1", content="Content"),),
        chunks=(
            RetrievalChunkWrite(
                chunk_key="chunk-1",
                content="Content",
                content_sha256="chunk-hash",
            ),
        ),
    )

    result = asyncio.run(repository.save(parsed_document))

    assert result == UUID(expected_id)
    function_name, parameters = client.calls[0]
    assert function_name == "save_parsed_document"
    nodes = parameters["p_nodes"]
    assert isinstance(nodes, list)
    assert nodes[0]["node_id"] == "article-1"
    assert nodes[0]["kind"] == "article"


def test_dense_index_repository_writes_indexed_embeddings() -> None:
    client = _FakeClient(_FakeResponse(1))
    repository = DenseIndexRepository(client)  # type: ignore[arg-type]
    index = DenseIndexWrite(index_name="legal-v1", provider="test", model_name="embed-v1")
    embedding = DenseEmbeddingWrite(
        retrieval_chunk_id=UUID("00000000-0000-0000-0000-000000000001"),
        embedding=(0.1,) * 1536,
        embedded_text_sha256="hash",
    )

    count = asyncio.run(repository.upsert_embeddings("legal-v1", (embedding,)))

    assert count == 1
    function_name, parameters = client.calls[0]
    assert function_name == "upsert_dense_embeddings"
    assert parameters["p_index_name"] == index.index_name
    embedding_rows = parameters["p_embeddings"]
    assert isinstance(embedding_rows, list)
    assert len(embedding_rows[0]["embedding"]) == 1536


def test_dense_index_contract_rejects_invalid_embedding_dimension() -> None:
    with pytest.raises(ValidationError):
        DenseIndexWrite(
            index_name="legal-v1",
            provider="test",
            model_name="embed-v1",
            embedding_dimension=0,
        )


def test_dense_index_repository_records_embedding_failures_without_a_vector() -> None:
    client = _FakeClient(_FakeResponse(1))
    repository = DenseIndexRepository(client)  # type: ignore[arg-type]
    status = DenseEmbeddingStatusWrite(
        retrieval_chunk_id=UUID("00000000-0000-0000-0000-000000000001"),
        embedded_text_sha256="hash",
        status="FAILED",
        error_message="provider unavailable",
    )

    count = asyncio.run(repository.record_embedding_statuses("legal-v1", (status,)))

    assert count == 1
    function_name, parameters = client.calls[0]
    assert function_name == "upsert_dense_embedding_statuses"
    status_rows = parameters["p_statuses"]
    assert isinstance(status_rows, list)
    assert status_rows[0]["status"] == "FAILED"
    assert status_rows[0]["error_message"] == "provider unavailable"


def test_sparse_index_repository_writes_postings() -> None:
    client = _FakeClient(_FakeResponse(1))
    repository = SparseIndexRepository(client)  # type: ignore[arg-type]
    index = SparseIndexWrite(index_name="bm25-vi")
    chunk = SparseChunkWrite(
        retrieval_chunk_id=UUID("00000000-0000-0000-0000-000000000001"),
        token_count=3,
        indexed_text_sha256="hash",
        postings=(SparsePostingWrite(term="luat", term_frequency=2, positions=(0, 2)),),
    )

    count = asyncio.run(repository.upsert_chunk_documents(index.index_name, (chunk,)))

    assert count == 1
    function_name, parameters = client.calls[0]
    assert function_name == "upsert_sparse_chunk_documents"
    chunk_rows = parameters["p_chunks"]
    assert isinstance(chunk_rows, list)
    assert chunk_rows[0]["postings"] == [{"term": "luat", "term_frequency": 2, "positions": [0, 2]}]


def test_sparse_retrieval_uses_governance_allowlists() -> None:
    client = _FakeClient(_FakeResponse([{"retrieval_chunk_id": "00000000-0000-0000-0000-000000000001", "score": 1.2}]))
    repository = SparseRetrievalRepository(client)  # type: ignore[arg-type]
    request = SparseSearchRequest(
        sparse_index_name="bm25-vi",
        terms=("luat", "hop-dong"),
        as_of_date=date(2026, 10, 31),
        allowed_usage_policies=("PRODUCTION",),
    )

    hits = asyncio.run(repository.search(request))

    assert len(hits) == 1
    assert hits[0].score == 1.2
    assert client.calls[0][0] == "search_sparse_legal_chunks"
    assert client.calls[0][1]["p_usage_policies"] == ["PRODUCTION"]


def test_sparse_search_requires_nonblank_terms_and_statuses() -> None:
    with pytest.raises(ValidationError):
        SparseSearchRequest(
            sparse_index_name="bm25-vi",
            terms=(" ",),
            as_of_date=date(2026, 10, 31),
            allowed_usage_policies=("PRODUCTION",),
        )


def test_repository_surfaces_transport_errors() -> None:
    request = httpx.Request("POST", "https://example.supabase.co/rest/v1/rpc/get_sparse_index")
    client = _FakeClient(httpx.ConnectError("offline", request=request))
    repository = SparseIndexRepository(client)  # type: ignore[arg-type]

    with pytest.raises(DatabaseRepositoryError, match="get_sparse_index"):
        asyncio.run(repository.get_index("bm25-vi"))
