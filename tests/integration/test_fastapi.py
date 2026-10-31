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


def test_app_initializes_supabase_client_when_configured(monkeypatch) -> None:
    expected_client = object()
    monkeypatch.setattr("src.bootstrap.create_supabase_client", lambda settings: expected_client)
    settings = AppSettings(
        supabase={
            "url": "https://example.supabase.co",
            "anon_key": "public-key",
        }
    )

    app = create_app(settings)

    assert app.state.supabase_client is expected_client


def test_app_runs_without_supabase_configuration() -> None:
    app = create_app(AppSettings())

    assert app.state.supabase_client is None


def test_app_runs_supabase_migrations_on_startup_when_enabled(monkeypatch) -> None:
    migration_calls: list[str] = []

    async def fake_run_migrations(database_url) -> None:
        migration_calls.append(database_url.get_secret_value())

    monkeypatch.setattr("src.bootstrap.run_supabase_migrations", fake_run_migrations)
    app = create_app(
        AppSettings(
            supabase={
                "auto_migrate": True,
                "database_url": "postgresql://user:password@db.example.supabase.co:5432/postgres",
            }
        )
    )

    with TestClient(app):
        pass

    assert migration_calls == ["postgresql://user:password@db.example.supabase.co:5432/postgres"]


def test_asgi_entry_point_loads_project_configuration() -> None:
    assert configured_app.title == "tillegal-ai"
