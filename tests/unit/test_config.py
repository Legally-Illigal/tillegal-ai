"""Application configuration tests."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from src.core.config import load_settings


def test_load_settings_applies_environment_overrides(tmp_path: Path) -> None:
    config_path = tmp_path / "app.yaml"
    config_path.write_text(
        "app:\n  name: configured-name\n  port: 8000\n"
        "api:\n  timeout_seconds: 30\n",
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
            "SUPABASE_VECTOR_TABLE": "documents",
        },
    )

    assert str(settings.supabase.url) == "https://example.supabase.co/"
    assert settings.supabase.service_role_key is not None
    assert settings.supabase.service_role_key.get_secret_value() == "server-secret"
    assert settings.supabase.vector_table == "documents"
    assert settings.supabase.is_configured is True


def test_supabase_vector_table_defaults_to_schema_embedding_table() -> None:
    settings = load_settings(environ={})

    assert settings.supabase.vector_table == "dense_chunk_embeddings"


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
