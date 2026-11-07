"""Create the FastAPI application and wire runtime components."""

import os
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.middleware.request_context import RequestContextMiddleware
from src.api.routes.health import router as health_router
from src.core.config import AppSettings, load_settings
from src.framework.observability.logging import configure_logging
from src.integrations.database.migrator import run_supabase_migrations
from src.integrations.database.session import create_supabase_client
from src.integrations.langgraph.postgres_checkpointer import PostgresCheckpointer


def create_app(settings: AppSettings | None = None) -> FastAPI:
    """Build the application using validated configuration."""
    app_settings = settings or load_settings()
    configure_logging(app_settings.app.log_level)
    pilot_enabled = os.environ.get("TILLEGAL_RAG_PILOT") == "1"
    if pilot_enabled and app_settings.app.env != "development":
        raise ValueError("The RAG pilot requires APP_ENV=development")
    if pilot_enabled and (app_settings.supabase.is_configured or app_settings.supabase.auto_migrate
                          or app_settings.langgraph.checkpointer_enabled):
        raise ValueError("Run the RAG pilot with database integrations disabled")

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        if pilot_enabled:
            from src.applications.tillegal.graphs.legal_qa import LegalQA

            application.state.legal_qa = LegalQA(os.environ)
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

        try:
            yield
        finally:
            if pilot_enabled:
                del application.state.legal_qa
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
    application.state.supabase_client = (
        create_supabase_client(app_settings.supabase) if app_settings.supabase.is_configured else None
    )
    application.add_middleware(RequestContextMiddleware)
    application.include_router(health_router)
    if pilot_enabled:
        from src.api.routes.chat import router as pilot_router

        application.include_router(pilot_router)

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
