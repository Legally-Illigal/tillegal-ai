"""ASGI application entry point."""

import uvicorn

from src.bootstrap import create_app
from src.core.config import load_settings

settings = load_settings()
app = create_app(settings)

if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=settings.app.host,
        port=settings.app.port,
        reload=settings.app.debug,
        log_level=settings.app.log_level.lower(),
    )
