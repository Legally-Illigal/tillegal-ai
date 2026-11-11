"""Create the FastAPI application and wire runtime components."""

import asyncio
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from supabase import Client

from src.api.middleware.request_context import RequestContextMiddleware
from src.api.routes.health import router as health_router
from src.api.routes.ingestion import router as ingestion_router
from src.application.services.vbpl_document_ingestion_service import VbplDocumentIngestionService
from src.application.services.vbpl_markdown_indexing_service import VbplMarkdownIndexingService
from src.core.config import AppSettings, load_settings
from src.core.identifiers import new_id
from src.framework.observability.logging import configure_logging
from src.integrations.database.migrator import run_supabase_migrations
from src.integrations.database.repositories.chunk_repository import ChunkRepository
from src.integrations.database.repositories.crawl_job_repository import CrawlJobRepository
from src.integrations.database.repositories.dense_index_repository import DenseIndexRepository
from src.integrations.database.repositories.parsed_document_repository import ParsedDocumentRepository
from src.integrations.database.repositories.source_document_repository import SourceDocumentRepository
from src.integrations.database.session import create_supabase_client
from src.integrations.database.supabase.storage import SupabaseObjectStorage
from src.integrations.database.transaction import PostgresTransactionManager
from src.integrations.langgraph.postgres_checkpointer import PostgresCheckpointer
from src.workers.tasks import VbplCrawlWorker


def create_app(settings: AppSettings | None = None) -> FastAPI:
    """Build the application using validated configuration."""
    app_settings = settings or load_settings()
    configure_logging(app_settings.app.log_level)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        if app_settings.supabase.auto_migrate:
            database_url = app_settings.supabase.database_url
            if database_url is None:
                raise ValueError("DATABASE_URL is required when SUPABASE_AUTO_MIGRATE=true")
            await run_supabase_migrations(database_url)

        checkpointer: PostgresCheckpointer | None = None
        if app_settings.langgraph.checkpointer_enabled:
            database_url = app_settings.supabase.database_url
            if database_url is None:
                raise ValueError("DATABASE_URL is required when LANGGRAPH_CHECKPOINTER_ENABLED=true")
            checkpointer = PostgresCheckpointer(database_url)
            application.state.langgraph_checkpointer = await checkpointer.open()

        worker_task: asyncio.Task[None] | None = None
        if app_settings.supabase.database_url is not None:
            supabase_client = application.state.supabase_client
            document_ingestor = (
                _create_vbpl_document_ingestor(supabase_client, app_settings) if supabase_client is not None else None
            )
            worker = VbplCrawlWorker(
                application.state.crawl_job_store,
                document_ingestor=document_ingestor,
                settings=app_settings.vbpl,
            )
            worker_task = asyncio.create_task(
                worker.run_forever(str(new_id())),
                name="vbpl-crawl-worker",
            )

        try:
            yield
        finally:
            if worker_task is not None:
                worker_task.cancel()
                try:
                    await worker_task
                except asyncio.CancelledError:
                    pass
            if checkpointer is not None:
                await checkpointer.close()

    application = FastAPI(
        title=app_settings.app.name,
        debug=app_settings.app.debug,
        docs_url="/docs" if app_settings.app.env == "development" else None,
        redoc_url=None,
        lifespan=lifespan,
    )
    application.state.settings = app_settings
    application.state.langgraph_checkpointer = None
    application.state.crawl_job_store = (
        CrawlJobRepository(PostgresTransactionManager(app_settings.supabase.database_url))
        if app_settings.supabase.database_url is not None
        else None
    )
    application.state.supabase_client = (
        create_supabase_client(app_settings.supabase) if app_settings.supabase.is_configured else None
    )
    application.add_middleware(RequestContextMiddleware)
    application.include_router(health_router)
    application.include_router(ingestion_router)

    allowed_origins: Sequence[str] = app_settings.security.cors_allowed_origins
    if allowed_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=list(allowed_origins),
            allow_credentials=True,
            allow_methods=["GET", "POST"],
            allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        )

    @application.get("/", include_in_schema=False)
    def get_service_info() -> dict[str, str]:
        return {
            "service": app_settings.app.name,
            "status": "running",
            "environment": app_settings.app.env,
        }

    return application


def _create_vbpl_document_ingestor(supabase_client: Client, settings: AppSettings):
    markdown_indexer = VbplMarkdownIndexingService(
        ParsedDocumentRepository(supabase_client),
        ChunkRepository(supabase_client),
        DenseIndexRepository(supabase_client),
        settings.vbpl,
    )
    return VbplDocumentIngestionService(
        SourceDocumentRepository(supabase_client),
        SupabaseObjectStorage(supabase_client),
        settings=settings.vbpl,
        markdown_indexer=markdown_indexer.index,
    ).ingest
