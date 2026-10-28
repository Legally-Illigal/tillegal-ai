"""Create the FastAPI application and wire runtime components."""

import logging
from collections.abc import Sequence

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes.health import router as health_router
from src.core.config import AppSettings, load_settings
from src.integrations.database.session import create_supabase_client


def create_app(settings: AppSettings | None = None) -> FastAPI:
    """Build the application using validated configuration."""
    app_settings = settings or load_settings()
    logging.basicConfig(
        level=app_settings.app.log_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    application = FastAPI(
        title=app_settings.app.name,
        debug=app_settings.app.debug,
        docs_url="/docs" if app_settings.app.env == "development" else None,
        redoc_url=None,
    )
    application.state.settings = app_settings
    application.state.supabase_client = (
        create_supabase_client(app_settings.supabase) if app_settings.supabase.is_configured else None
    )
    application.include_router(health_router)

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
