"""Parse, chunk, and embed normalized VBPL Markdown."""

from __future__ import annotations

import asyncio
import hashlib
from uuid import UUID

from src.applications.tillegal.ingestion.crawler.embeddings.sentence_transformer import (
    EMBEDDING_DIMENSION,
    MODEL_NAME,
    PASSAGE_PREFIX,
    PassageEmbedder,
    SentenceTransformerPassageEmbedder,
)
from src.applications.tillegal.ingestion.crawler.parsers.legal_markdown import parse_legal_markdown
from src.core.config import VbplCrawlSettings
from src.integrations.database.repositories.chunk_repository import ChunkRepository
from src.integrations.database.repositories.dense_index_repository import (
    DenseEmbeddingWrite,
    DenseIndexRepository,
    DenseIndexWrite,
)
from src.integrations.database.repositories.parsed_document_repository import ParsedDocumentRepository

DENSE_INDEX_NAME = "vbpl-multilingual-e5-small-v1"


class VbplMarkdownIndexingService:
    """Persist legal Markdown structure and index its chunks with E5-small."""

    def __init__(
        self,
        parsed_documents: ParsedDocumentRepository,
        chunks: ChunkRepository,
        dense_indexes: DenseIndexRepository,
        settings: VbplCrawlSettings,
        *,
        embedder: PassageEmbedder | None = None,
    ) -> None:
        self._parsed_documents = parsed_documents
        self._chunks = chunks
        self._dense_indexes = dense_indexes
        self._settings = settings
        self._embedder = embedder or SentenceTransformerPassageEmbedder()

    async def index(self, source_document_id: UUID, title: str, markdown: str) -> dict[str, object]:
        """Parse one Markdown document and persist chunks and their dense embeddings."""
        parsed = await asyncio.to_thread(
            parse_legal_markdown,
            markdown,
            source_document_id=source_document_id,
            title=title,
            token_counter=self._embedder.count_tokens,
            max_chunk_tokens=self._settings.chunk_max_tokens,
        )
        existing_index = await self._dense_indexes.get_index(DENSE_INDEX_NAME)
        index_status = "STALE" if existing_index is not None else "BUILDING"
        index = DenseIndexWrite(
            index_name=DENSE_INDEX_NAME,
            provider="sentence-transformers",
            model_name=MODEL_NAME,
            embedding_dimension=EMBEDDING_DIMENSION,
            distance_metric="cosine",
            index_version="v1",
            status=index_status,
            metadata={
                "normalized": True,
                "passage_prefix": "passage: ",
                "query_prefix": "query: ",
            },
        )
        await self._dense_indexes.upsert_index(index)
        structure_id = await self._parsed_documents.save(parsed)
        document_chunks = await self._chunks.list_for_document(source_document_id)
        if len(document_chunks) != len(parsed.chunks):
            raise RuntimeError(
                f"Parsed-document persistence returned {len(document_chunks)} chunks; expected {len(parsed.chunks)}"
            )
        embedding_count = 0

        for start in range(0, len(document_chunks), self._settings.embedding_batch_size):
            batch = document_chunks[start : start + self._settings.embedding_batch_size]
            texts = [_required_string(chunk, "content") for chunk in batch]
            vectors = await asyncio.to_thread(
                self._embedder.embed_passages,
                texts,
                self._settings.embedding_batch_size,
            )
            if len(vectors) != len(batch):
                raise RuntimeError(f"Embedding model returned {len(vectors)} vectors for {len(batch)} VBPL chunks")
            embeddings = tuple(
                DenseEmbeddingWrite(
                    retrieval_chunk_id=UUID(_required_string(chunk, "id")),
                    embedding=vector,
                    embedded_text_sha256=hashlib.sha256(
                        f"{PASSAGE_PREFIX}{_required_string(chunk, 'content')}".encode()
                    ).hexdigest(),
                    metadata={"prefix": PASSAGE_PREFIX.strip(), "model": MODEL_NAME},
                )
                for chunk, vector in zip(batch, vectors, strict=True)
            )
            persisted_count = await self._dense_indexes.upsert_embeddings(DENSE_INDEX_NAME, embeddings)
            if persisted_count != len(batch):
                raise RuntimeError(f"Embedding persistence stored {persisted_count} of {len(batch)} VBPL chunk vectors")
            embedding_count += persisted_count

        final_status = await self._dense_indexes.refresh_index_status(DENSE_INDEX_NAME)
        return {
            "document_structure_id": str(structure_id),
            "block_count": len(parsed.blocks),
            "node_count": len(parsed.nodes),
            "chunk_count": len(parsed.chunks),
            "embedding_count": embedding_count,
            "dense_index_name": DENSE_INDEX_NAME,
            "dense_index_status": final_status,
            "content_sha256": parsed.structure.content_sha256,
        }


def _required_string(row: dict[str, object], key: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value:
        raise RuntimeError(f"Retrieval chunk is missing required string field '{key}'")
    return value
