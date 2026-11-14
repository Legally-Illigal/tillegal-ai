import asyncio
import hashlib
import unicodedata
from uuid import UUID

import pytest

from src.application.services.vbpl_markdown_indexing_service import (
    DENSE_INDEX_NAME,
    VbplMarkdownIndexingService,
    VbplSparseIndexingService,
    tokenize_sparse_text,
)
from src.core.config import VbplCrawlSettings

_SOURCE_DOCUMENT_ID = UUID("00000000-0000-0000-0000-000000000001")
_CHUNK_IDS = (
    "00000000-0000-0000-0000-000000000011",
    "00000000-0000-0000-0000-000000000012",
)


class FakeParsedDocuments:
    def __init__(self) -> None:
        self.saved = None

    async def save(self, parsed_document):
        self.saved = parsed_document
        return UUID("00000000-0000-0000-0000-000000000021")


class FakeChunks:
    async def list_for_document(self, source_document_id):
        return tuple(
            {
                "id": chunk_id,
                "content": f"legal passage {index}",
                "content_sha256": f"chunk-hash-{index}",
            }
            for index, chunk_id in enumerate(_CHUNK_IDS)
        )


class FakeDenseIndexes:
    def __init__(self) -> None:
        self.indexes = []
        self.embedding_batches = []

    async def get_index(self, index_name):
        return None

    async def upsert_index(self, index):
        self.indexes.append(index)
        return {"index_name": index.index_name}

    async def upsert_embeddings(self, index_name, embeddings):
        self.embedding_batches.append((index_name, embeddings))
        return len(embeddings)

    async def refresh_index_status(self, index_name):
        return "READY"


class FakeEmbedder:
    def count_tokens(self, text: str) -> int:
        return len(text.split())

    def embed_passages(self, texts: list[str], batch_size: int) -> list[tuple[float, ...]]:
        return [(0.01,) * 384 for _ in texts]


def test_indexing_service_saves_chunks_and_e5_embeddings() -> None:
    parsed_documents = FakeParsedDocuments()
    dense_indexes = FakeDenseIndexes()
    sparse_indexes = FakeSparseIndexes()
    service = VbplMarkdownIndexingService(
        parsed_documents,  # type: ignore[arg-type]
        FakeChunks(),  # type: ignore[arg-type]
        dense_indexes,  # type: ignore[arg-type]
        VbplCrawlSettings(embedding_batch_size=1),
        embedder=FakeEmbedder(),
        sparse_indexes=sparse_indexes,
    )

    result = asyncio.run(
        service.index(
            _SOURCE_DOCUMENT_ID,
            "Nghị định số 25/2026/NĐ-CP",
            "## Chương I. Quy định chung\n\n"
            "### Điều 1. Phạm vi điều chỉnh\n\n"
            "1. Nghị định quy định về hồ sơ điện tử.\n\n"
            "2. Nghị định áp dụng đối với cơ quan nhà nước.",
        )
    )

    assert parsed_documents.saved is not None
    assert len(parsed_documents.saved.chunks) == 2
    assert dense_indexes.indexes[0].index_name == DENSE_INDEX_NAME
    assert dense_indexes.indexes[0].model_name == "intfloat/multilingual-e5-small"
    assert dense_indexes.indexes[0].embedding_dimension == 384
    assert [len(batch[1]) for batch in dense_indexes.embedding_batches] == [1, 1]
    first_embedding = dense_indexes.embedding_batches[0][1][0]
    assert len(first_embedding.embedding) == 384
    assert first_embedding.embedded_text_sha256 == hashlib.sha256(b"passage: legal passage 0").hexdigest()
    assert result["chunk_count"] == 2
    assert result["embedding_count"] == 2
    assert result["dense_index_status"] == "READY"
    assert result["sparse_chunk_count"] == 2
    assert result["sparse_index_status"] == "READY"
    assert len(sparse_indexes.documents) == 2


class FakeSparseIndexes:
    def __init__(self, chunks=()) -> None:
        self.chunks = chunks
        self.documents = {}
        self.status = None
        self.fail = False

    async def upsert_index(self, index):
        self.status = index.status
        return {}

    async def list_index_work(self, index_name, limit=100):
        return tuple(c for c in self.chunks if UUID(c["id"]) not in self.documents)[:limit]

    async def upsert_chunk_documents(self, index_name, chunks):
        if self.fail:
            return 0
        for chunk in chunks:
            self.documents[chunk.retrieval_chunk_id] = chunk
        return len(chunks)


def test_sparse_normalizes_vietnamese_without_removing_accents() -> None:
    text = unicodedata.normalize("NFD", "THUẾ, thuế! Điều 7; điểm đ.")
    assert tokenize_sparse_text(text) == ("thuế", "thuế", "điều", "7", "điểm", "đ")


def test_sparse_backfill_resumes_and_records_frequencies_positions_and_hash() -> None:
    content = "Thuế thuế; Điều 7."
    indexes = FakeSparseIndexes(tuple({"id": i, "content": content} for i in _CHUNK_IDS))
    service = VbplSparseIndexingService(indexes, batch_size=1)
    first = asyncio.run(service.backfill())
    assert first["sparse_chunk_count"] == 2
    assert first["sparse_index_status"] == "READY"
    document = indexes.documents[UUID(_CHUNK_IDS[0])]
    assert document.token_count == 4
    assert document.indexed_text_sha256 == hashlib.sha256(content.encode()).hexdigest()
    posting = next(p for p in document.postings if p.term == "thuế")
    assert posting.term_frequency == 2
    assert posting.positions == (0, 1)
    assert asyncio.run(service.backfill())["sparse_chunk_count"] == 0


def test_sparse_remains_stale_until_all_chunks_are_indexed_and_replaces_changed_postings() -> None:
    chunks = tuple({"id": i, "content": "thuế"} for i in _CHUNK_IDS)
    indexes = FakeSparseIndexes(chunks)
    service = VbplSparseIndexingService(indexes)
    assert asyncio.run(service.index_chunks(chunks[:1]))["sparse_index_status"] == "STALE"
    changed = ({"id": _CHUNK_IDS[0], "content": "đất"},)
    asyncio.run(service.index_chunks(changed))
    assert [p.term for p in indexes.documents[UUID(_CHUNK_IDS[0])].postings] == ["đất"]
    assert asyncio.run(service.backfill())["sparse_index_status"] == "READY"


def test_sparse_partial_write_does_not_mark_index_ready() -> None:
    indexes = FakeSparseIndexes(({"id": _CHUNK_IDS[0], "content": "thuế"},))
    indexes.fail = True
    with pytest.raises(RuntimeError, match="stored 0 of 1"):
        asyncio.run(VbplSparseIndexingService(indexes).backfill())
    assert indexes.status != "READY"
