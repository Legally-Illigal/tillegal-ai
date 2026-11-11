import asyncio
import hashlib
from uuid import UUID

from src.application.services.vbpl_markdown_indexing_service import (
    DENSE_INDEX_NAME,
    VbplMarkdownIndexingService,
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
    service = VbplMarkdownIndexingService(
        parsed_documents,  # type: ignore[arg-type]
        FakeChunks(),  # type: ignore[arg-type]
        dense_indexes,  # type: ignore[arg-type]
        VbplCrawlSettings(embedding_batch_size=1),
        embedder=FakeEmbedder(),
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
