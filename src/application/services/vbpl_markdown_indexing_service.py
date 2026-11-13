"""Parse, chunk, and embed normalized VBPL Markdown."""

from __future__ import annotations

import asyncio
import hashlib
import re
import unicodedata
from typing import Literal
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
from src.integrations.database.repositories.sparse_index_repository import (
    SparseChunkWrite,
    SparseIndexRepository,
    SparseIndexWrite,
    SparsePostingWrite,
)

DENSE_INDEX_NAME = "vbpl-multilingual-e5-small-v1"
SPARSE_INDEX_NAME = "vbpl-bm25-unicode-v1"


def tokenize_sparse_text(text: str) -> tuple[str, ...]:
    """Normalize Unicode and case, retaining Vietnamese accents and numbers."""
    return tuple(re.findall(r"[^\W_]+", unicodedata.normalize("NFC", text).lower()))


def _sparse_chunk(chunk: dict[str, object]) -> SparseChunkWrite:
    content = _required_string(chunk, "content")
    tokens = tokenize_sparse_text(content)
    positions: dict[str, list[int]] = {}
    for position, term in enumerate(tokens):
        positions.setdefault(term, []).append(position)
    return SparseChunkWrite(
        retrieval_chunk_id=UUID(_required_string(chunk, "id")),
        token_count=len(tokens),
        indexed_text_sha256=hashlib.sha256(content.encode("utf-8")).hexdigest(),
        postings=tuple(
            SparsePostingWrite(term=term, term_frequency=len(offsets), positions=tuple(offsets))
            for term, offsets in positions.items()
        ),
    )


class VbplSparseIndexingService:
    """Build BM25 postings from persisted chunks without loading an embedding model."""

    def __init__(self, indexes: SparseIndexRepository, batch_size: int = 100) -> None:
        if not 1 <= batch_size <= 500:
            raise ValueError("Sparse batch size must be between 1 and 500")
        self._indexes = indexes
        self._batch_size = batch_size

    async def _set_status(self, status: Literal["BUILDING", "STALE", "READY"]) -> None:
        await self._indexes.upsert_index(
            SparseIndexWrite(
                index_name=SPARSE_INDEX_NAME,
                tokenizer="unicode-nfc-lower-v1",
                status=status,
            )
        )

    async def _write(self, chunks: tuple[dict[str, object], ...]) -> int:
        documents = tuple(_sparse_chunk(chunk) for chunk in chunks)
        count = await self._indexes.upsert_chunk_documents(SPARSE_INDEX_NAME, documents)
        if count != len(documents):
            raise RuntimeError(f"Sparse persistence stored {count} of {len(documents)} chunks")
        return count

    async def _finish(self) -> str:
        pending = await self._indexes.list_index_work(SPARSE_INDEX_NAME, limit=1)
        status: Literal["STALE", "READY"] = "STALE" if pending else "READY"
        await self._set_status(status)
        return status

    async def index_chunks(self, chunks: tuple[dict[str, object], ...]) -> dict[str, object]:
        await self._set_status("BUILDING")
        count = 0
        for start in range(0, len(chunks), self._batch_size):
            count += await self._write(chunks[start : start + self._batch_size])
        return {
            "sparse_chunk_count": count,
            "sparse_index_name": SPARSE_INDEX_NAME,
            "sparse_index_status": await self._finish(),
        }

    async def backfill(self) -> dict[str, object]:
        """Resume pending/stale/failed chunks; successful batches are safe to rerun."""
        await self._set_status("BUILDING")
        count = 0
        while chunks := await self._indexes.list_index_work(SPARSE_INDEX_NAME, limit=self._batch_size):
            count += await self._write(chunks)
        return {
            "sparse_chunk_count": count,
            "sparse_index_name": SPARSE_INDEX_NAME,
            "sparse_index_status": await self._finish(),
        }


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
        sparse_indexes: SparseIndexRepository | None = None,
    ) -> None:
        self._parsed_documents = parsed_documents
        self._chunks = chunks
        self._dense_indexes = dense_indexes
        self._settings = settings
        self._embedder = embedder or SentenceTransformerPassageEmbedder()
        self._sparse = VbplSparseIndexingService(sparse_indexes) if sparse_indexes is not None else None

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
        sparse_result = await self._sparse.index_chunks(document_chunks) if self._sparse is not None else {}

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
            **sparse_result,
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
