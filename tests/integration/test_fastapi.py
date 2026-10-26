"""FastAPI integration tests."""

from fastapi.testclient import TestClient

from src.bootstrap import create_app
from src.core.config import AppSettings
from src.main import app as configured_app


def test_root_reports_running_service() -> None:
    app = create_app(AppSettings(app={"name": "test-service", "env": "test"}))

    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert response.json() == {
        "service": "test-service",
        "status": "running",
        "environment": "test",
    }


def test_liveness_endpoint_reports_ok() -> None:
    app = create_app(AppSettings())

    response = TestClient(app).get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_asgi_entry_point_loads_project_configuration() -> None:
    assert configured_app.title == "tillegal-ai"
