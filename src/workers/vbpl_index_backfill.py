"""Repair existing chunk indexes without crawling or parsing source documents."""

import asyncio
import hashlib
import logging
from uuid import UUID

import httpx
from postgrest.exceptions import APIError

from src.application.services.vbpl_markdown_indexing_service import DENSE_INDEX_NAME, VbplSparseIndexingService
from src.applications.tillegal.ingestion.crawler.embeddings.sentence_transformer import (
    EMBEDDING_DIMENSION,
    MODEL_NAME,
    PASSAGE_PREFIX,
    SentenceTransformerPassageEmbedder,
)
from src.core.config import load_settings
from src.integrations.database.repositories.dense_index_repository import DenseEmbeddingWrite, DenseIndexRepository
from src.integrations.database.repositories.rpc import DatabaseRepositoryError
from src.integrations.database.repositories.sparse_index_repository import SparseIndexRepository
from src.integrations.database.session import create_supabase_client
from src.integrations.database.transaction import PostgresTransactionManager

logger = logging.getLogger(__name__)


class RetryBackfillRpc:
    """Only used for this worker's reads and idempotent index upserts."""

    async def call_rpc(self, function_name, parameters):
        for attempt in range(3):
            try:
                return await super().call_rpc(function_name, parameters)
            except DatabaseRepositoryError as error:
                cause = error.__cause__
                transient = isinstance(cause, httpx.TransportError) or (
                    isinstance(cause, APIError) and str(cause.code) in ("57014", "40001", "40P01")
                )
                if not transient or attempt == 2:
                    raise
                delay = 2 ** (attempt + 1)
                logger.warning("Transient connection failure in %s; retry in %ss", function_name, delay)
                await asyncio.sleep(delay)


class BackfillDenseRepository(RetryBackfillRpc, DenseIndexRepository):
    def __init__(self, client, transactions=None):
        super().__init__(client)
        self._transactions = transactions

    async def list_embedding_work(self, index_name, statuses=("PENDING", "STALE", "FAILED"), limit=100):
        if self._transactions is None:
            return await super().list_embedding_work(index_name, statuses, limit)

        def read(connection):
            # Backfill-only read: avoid PostgREST's short statement timeout and
            # returning full chunk JSON. No transaction spans model execution.
            connection.execute("SET TRANSACTION READ ONLY")
            connection.execute("SET LOCAL statement_timeout = '60s'")
            connection.execute("SET LOCAL search_path = public, extensions")
            return tuple(
                connection.execute(
                    """SELECT chunk.id, chunk.content
                FROM public.retrieval_chunks chunk
                JOIN public.dense_indexes i ON i.index_name = %s
                LEFT JOIN public.dense_chunk_embeddings e
                  ON e.dense_index_id = i.id AND e.retrieval_chunk_id = chunk.id
                WHERE COALESCE(e.status, 'PENDING') = ANY(%s)
                   OR (e.status = 'INDEXED' AND
                       (e.embedding IS NULL OR vector_dims(e.embedding) <> i.embedding_dimension))
                ORDER BY chunk.created_at, chunk.id
                LIMIT %s""",
                    (index_name, list(statuses), min(max(limit, 1), 500)),
                ).fetchall()
            )

        return await self._transactions.run(read)


class BackfillSparseRepository(RetryBackfillRpc, SparseIndexRepository):
    pass


async def backfill_dense(repository, embedder, batch_size: int):
    index = await repository.get_index(DENSE_INDEX_NAME)
    if index is None:
        raise ValueError(f"Index {DENSE_INDEX_NAME} does not exist; ingest a document first")
    if index.get("model_name") != MODEL_NAME or index.get("embedding_dimension") != EMBEDDING_DIMENSION:
        raise ValueError("Existing index model/dimension does not match E5-small")
    count = 0
    previous_ids = None
    # Include SKIPPED because refresh_dense_index_status requires all chunks to be INDEXED.
    while chunks := await repository.list_embedding_work(
        DENSE_INDEX_NAME,
        statuses=("PENDING", "STALE", "FAILED", "SKIPPED"),
        limit=batch_size,
    ):
        ids = tuple(str(chunk["id"]) for chunk in chunks)
        if ids == previous_ids:
            raise RuntimeError("Dense backfill made no progress; stopping")
        previous_ids = ids
        texts = [str(chunk["content"]) for chunk in chunks]
        vectors = await asyncio.to_thread(embedder.embed_passages, texts, batch_size)
        if len(vectors) != len(chunks) or any(len(v) != EMBEDDING_DIMENSION for v in vectors):
            raise ValueError("Embedding model returned incorrect vector count or dimensions")
        writes = tuple(
            DenseEmbeddingWrite(
                retrieval_chunk_id=UUID(str(chunk["id"])),
                embedding=vector,
                embedded_text_sha256=hashlib.sha256(f"{PASSAGE_PREFIX}{text}".encode()).hexdigest(),
                metadata={"prefix": PASSAGE_PREFIX.strip(), "model": MODEL_NAME},
            )
            for chunk, text, vector in zip(chunks, texts, vectors, strict=True)
        )
        saved = await repository.upsert_embeddings(DENSE_INDEX_NAME, writes)
        if saved != len(chunks):
            raise RuntimeError("Database did not persist the full embedding batch")
        count += saved
        logger.info("Dense: saved %s embeddings (total repaired: %s)", saved, count)
    status = await repository.refresh_index_status(DENSE_INDEX_NAME)
    logger.info("Dense: %s (%s embeddings repaired)", status, count)
    if status != "READY":
        raise RuntimeError("Dense remains STALE; inspect INDEXED rows for null/wrong-dimension vectors")
    return {"count": count, "status": status}


async def run():
    settings = load_settings()
    if settings.supabase.service_role_key is None:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required")
    transactions = (
        PostgresTransactionManager(settings.supabase.database_url)
        if settings.supabase.database_url is not None
        else None
    )
    with httpx.Client(http2=False, timeout=120, limits=httpx.Limits(max_connections=2)) as transport:
        client = create_supabase_client(settings.supabase, http_client=transport)
        logger.info("Starting sparse backfill (HTTP/1.1, batch size 10)")
        sparse = await VbplSparseIndexingService(BackfillSparseRepository(client), batch_size=10).backfill()
        logger.info("Sparse: %s", sparse)
        await backfill_dense(
            BackfillDenseRepository(client, transactions),
            SentenceTransformerPassageEmbedder(),
            settings.vbpl.embedding_batch_size,
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(run())
