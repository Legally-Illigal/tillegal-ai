"""Application configuration tests."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from src.core.config import load_settings


def test_load_settings_applies_environment_overrides(tmp_path: Path) -> None:
    config_path = tmp_path / "app.yaml"
    config_path.write_text(
        "app:\n  name: configured-name\n  port: 8000\napi:\n  timeout_seconds: 30\n",
        encoding="utf-8",
    )

    settings = load_settings(
        config_path,
        environ={"APP_NAME": "override-name", "PORT": "9000", "DEBUG": "true"},
    )

    assert settings.app.name == "override-name"
    assert settings.app.port == 9000
    assert settings.app.debug is True
    assert settings.api.timeout_seconds == 30


def test_load_settings_rejects_invalid_debug_value(tmp_path: Path) -> None:
    config_path = tmp_path / "app.yaml"
    config_path.write_text("app: {}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="DEBUG must be either"):
        load_settings(config_path, environ={"DEBUG": "sometimes"})


def test_load_settings_rejects_invalid_port(tmp_path: Path) -> None:
    config_path = tmp_path / "app.yaml"
    config_path.write_text("app:\n  port: 70000\n", encoding="utf-8")

    with pytest.raises(ValidationError):
        load_settings(config_path, environ={})


def test_load_settings_configures_supabase_from_environment(tmp_path: Path) -> None:
    config_path = tmp_path / "app.yaml"
    config_path.write_text("app: {}\n", encoding="utf-8")

    settings = load_settings(
        config_path,
        environ={
            "SUPABASE_URL": "https://example.supabase.co",
            "SUPABASE_SERVICE_ROLE_KEY": "server-secret",
        },
    )

    assert str(settings.supabase.url) == "https://example.supabase.co/"
    assert settings.supabase.service_role_key is not None
    assert settings.supabase.service_role_key.get_secret_value() == "server-secret"
    assert settings.supabase.is_configured is True


def test_load_settings_rejects_partial_supabase_configuration(tmp_path: Path) -> None:
    config_path = tmp_path / "app.yaml"
    config_path.write_text("app: {}\n", encoding="utf-8")

    with pytest.raises(ValidationError, match="SUPABASE_URL and a Supabase API key"):
        load_settings(
            config_path,
            environ={"SUPABASE_URL": "https://example.supabase.co"},
        )


def test_load_settings_treats_empty_supabase_environment_as_unconfigured(tmp_path: Path) -> None:
    config_path = tmp_path / "app.yaml"
    config_path.write_text("app: {}\n", encoding="utf-8")

    settings = load_settings(
        config_path,
        environ={"SUPABASE_URL": "", "SUPABASE_SERVICE_ROLE_KEY": ""},
    )

    assert settings.supabase.is_configured is False


def test_load_settings_enables_supabase_auto_migrations(tmp_path: Path) -> None:
    config_path = tmp_path / "app.yaml"
    config_path.write_text("app: {}\n", encoding="utf-8")

    settings = load_settings(
        config_path,
        environ={
            "SUPABASE_AUTO_MIGRATE": "true",
            "DATABASE_URL": "postgresql://user:password@db.example.supabase.co:5432/postgres",
        },
    )

    assert settings.supabase.auto_migrate is True


def test_load_settings_requires_database_url_for_auto_migrations(tmp_path: Path) -> None:
    config_path = tmp_path / "app.yaml"
    config_path.write_text("app: {}\n", encoding="utf-8")

    with pytest.raises(ValidationError, match="DATABASE_URL is required"):
        load_settings(config_path, environ={"SUPABASE_AUTO_MIGRATE": "true"})


def test_load_settings_rejects_invalid_auto_migration_value(tmp_path: Path) -> None:
    config_path = tmp_path / "app.yaml"
    config_path.write_text("app: {}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="SUPABASE_AUTO_MIGRATE must be either"):
        load_settings(config_path, environ={"SUPABASE_AUTO_MIGRATE": "sometimes"})


def test_load_settings_enables_langgraph_checkpointer_with_database_url(tmp_path: Path) -> None:
    config_path = tmp_path / "app.yaml"
    config_path.write_text("app: {}\n", encoding="utf-8")

    settings = load_settings(
        config_path,
        environ={
            "LANGGRAPH_CHECKPOINTER_ENABLED": "true",
            "DATABASE_URL": "postgresql://db.example/postgres",
        },
    )

    assert settings.langgraph.checkpointer_enabled is True


def test_load_settings_requires_database_url_for_langgraph_checkpointer(tmp_path: Path) -> None:
    config_path = tmp_path / "app.yaml"
    config_path.write_text("app: {}\n", encoding="utf-8")

    with pytest.raises(ValidationError, match="DATABASE_URL is required"):
        load_settings(config_path, environ={"LANGGRAPH_CHECKPOINTER_ENABLED": "true"})


def test_load_settings_rejects_invalid_langgraph_checkpointer_value(tmp_path: Path) -> None:
    config_path = tmp_path / "app.yaml"
    config_path.write_text("app: {}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="LANGGRAPH_CHECKPOINTER_ENABLED must be either"):
        load_settings(config_path, environ={"LANGGRAPH_CHECKPOINTER_ENABLED": "sometimes"})


def test_load_settings_applies_vbpl_environment_overrides(tmp_path: Path) -> None:
    config_path = tmp_path / "app.yaml"
    config_path.write_text("app: {}\n", encoding="utf-8")

    settings = load_settings(
        config_path,
        environ={
            "VBPL_MAX_ATTACHMENT_SIZE_MB": "150",
            "VBPL_REQUEST_PAUSE_SECONDS": "0.5",
            "VBPL_WORKER_LEASE_SECONDS": "240",
            "VBPL_CHUNK_MAX_TOKENS": "400",
            "VBPL_EMBEDDING_BATCH_SIZE": "16",
        },
    )

    assert settings.vbpl.max_attachment_size_mb == 150
    assert settings.vbpl.request_pause_seconds == 0.5
    assert settings.vbpl.worker_lease_seconds == 240
    assert settings.vbpl.chunk_max_tokens == 400
    assert settings.vbpl.embedding_batch_size == 16


def test_load_settings_preserves_vbpl_defaults(tmp_path: Path) -> None:
    config_path = tmp_path / "app.yaml"
    config_path.write_text("app: {}\n", encoding="utf-8")

    settings = load_settings(config_path, environ={})

    assert settings.vbpl.max_sitemap_size_mb == 10
    assert settings.vbpl.max_page_size_mb == 5
    assert settings.vbpl.max_attachment_size_mb == 100
    assert settings.vbpl.worker_poll_interval_seconds == 5


def test_load_settings_rejects_vbpl_heartbeat_not_shorter_than_lease(tmp_path: Path) -> None:
    config_path = tmp_path / "app.yaml"
    config_path.write_text("app: {}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="heartbeat interval must be shorter"):
        load_settings(
            config_path,
            environ={
                "VBPL_WORKER_LEASE_SECONDS": "45",
                "VBPL_WORKER_HEARTBEAT_INTERVAL_SECONDS": "45",
            },
        )
