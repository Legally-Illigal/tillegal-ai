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
