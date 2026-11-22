"""Background worker entry points."""

import asyncio

from src.application.services.vbpl_document_ingestion_service import VbplDocumentIngestionService
from src.application.services.vbpl_markdown_indexing_service import VbplMarkdownIndexingService
from src.core.config import AppSettings, load_settings
from src.core.identifiers import new_id
from src.framework.observability.logging import configure_logging
from src.integrations.database.repositories.chunk_repository import ChunkRepository
from src.integrations.database.repositories.crawl_job_repository import CrawlJobRepository
from src.integrations.database.repositories.dense_index_repository import DenseIndexRepository
from src.integrations.database.repositories.parsed_document_repository import ParsedDocumentRepository
from src.integrations.database.repositories.source_document_repository import SourceDocumentRepository
from src.integrations.database.repositories.sparse_index_repository import SparseIndexRepository
from src.integrations.database.session import create_supabase_client
from src.integrations.database.supabase.storage import SupabaseObjectStorage
from src.integrations.database.transaction import PostgresTransactionManager
from src.workers.tasks import VbplCrawlWorker


def create_ingestor(settings: AppSettings) -> VbplDocumentIngestionService:
    """Wire the same storage, parsing and indexing pipeline for both discovery sources."""
    if settings.supabase.service_role_key is None:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required for VBPL file storage")
    supabase_client = create_supabase_client(settings.supabase)
    markdown_indexer = VbplMarkdownIndexingService(
        ParsedDocumentRepository(supabase_client),
        ChunkRepository(supabase_client),
        DenseIndexRepository(supabase_client),
        settings.vbpl,
        sparse_indexes=SparseIndexRepository(supabase_client),
    )
    return VbplDocumentIngestionService(
        SourceDocumentRepository(supabase_client),
        SupabaseObjectStorage(supabase_client),
        settings=settings.vbpl,
        markdown_indexer=markdown_indexer.index,
    )


async def run_worker() -> None:
    """Run the ingestion worker as a standalone process."""
    settings = load_settings()
    configure_logging(settings.app.log_level)
    database_url = settings.supabase.database_url
    if database_url is None:
        raise ValueError("DATABASE_URL must be set before running the ingestion worker")
    repository = CrawlJobRepository(PostgresTransactionManager(database_url))
    ingestor = create_ingestor(settings)
    await VbplCrawlWorker(
        repository,
        document_ingestor=ingestor.ingest,
        settings=settings.vbpl,
    ).run_forever(str(new_id()))


def main() -> None:
    """Start the worker event loop."""
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
