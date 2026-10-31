"""Load and validate application configuration."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Literal

import yaml
from dotenv import load_dotenv
from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "configs" / "app.yaml"


class StrictConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ApplicationSettings(StrictConfig):
    name: str = "tillegal-ai"
    env: str = "development"
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    debug: bool = False
    log_level: Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"] = "INFO"


class APISettings(StrictConfig):
    timeout_seconds: float = Field(default=120, gt=0)
    max_body_size_mb: int = Field(default=25, ge=1)


class SecuritySettings(StrictConfig):
    redact_secrets: bool = True
    cors_allowed_origins: list[str] = Field(default_factory=list)


class SupabaseSettings(StrictConfig):
    url: AnyHttpUrl | None = None
    service_role_key: SecretStr | None = None
    anon_key: SecretStr | None = None
    database_url: SecretStr | None = None
    auto_migrate: bool = False

    @field_validator("url", mode="before")
    @classmethod
    def empty_url_is_unset(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("service_role_key", "anon_key", "database_url", mode="before")
    @classmethod
    def empty_key_is_unset(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @model_validator(mode="after")
    def validate_connection_settings(self) -> SupabaseSettings:
        if (self.url is None) != (self.api_key is None):
            raise ValueError("SUPABASE_URL and a Supabase API key must be configured together")
        if self.auto_migrate and self.database_url is None:
            raise ValueError("DATABASE_URL is required when SUPABASE_AUTO_MIGRATE=true")
        return self

    @property
    def api_key(self) -> SecretStr | None:
        """Prefer the server-only key while allowing an RLS-protected anon key."""
        return self.service_role_key or self.anon_key

    @property
    def is_configured(self) -> bool:
        return self.url is not None and self.api_key is not None


class AppSettings(StrictConfig):
    app: ApplicationSettings = Field(default_factory=ApplicationSettings)
    api: APISettings = Field(default_factory=APISettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    supabase: SupabaseSettings = Field(default_factory=SupabaseSettings)


def load_settings(
    config_path: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> AppSettings:
    """Load YAML settings and apply supported environment variable overrides."""
    if environ is None:
        load_dotenv(override=False)
        env = os.environ
    else:
        env = environ

    configured_path = config_path or (
        Path(env["CONFIG_FILE"]) if env.get("CONFIG_FILE") else DEFAULT_CONFIG_PATH
    )
    raw_config = yaml.safe_load(configured_path.read_text(encoding="utf-8"))
    if raw_config is None:
        raw_config = {}
    if not isinstance(raw_config, dict):
        raise ValueError(f"Configuration root in {configured_path} must be a YAML mapping")

    config = dict(raw_config)
    for section in ("app", "api", "security", "supabase"):
        value = config.get(section, {})
        if not isinstance(value, dict):
            raise ValueError(f"Configuration section '{section}' must be a YAML mapping")
        config[section] = dict(value)

    app_overrides = {
        "APP_NAME": "name",
        "APP_ENV": "env",
        "HOST": "host",
        "PORT": "port",
        "DEBUG": "debug",
        "LOG_LEVEL": "log_level",
    }
    for env_key, setting_key in app_overrides.items():
        if env_key in env:
            config["app"][setting_key] = env[env_key]

    api_overrides = {
        "API_TIMEOUT_SECONDS": "timeout_seconds",
        "API_MAX_BODY_SIZE_MB": "max_body_size_mb",
    }
    for env_key, setting_key in api_overrides.items():
        if env_key in env:
            config["api"][setting_key] = env[env_key]

    supabase_overrides = {
        "SUPABASE_URL": "url",
        "SUPABASE_SERVICE_ROLE_KEY": "service_role_key",
        "SUPABASE_ANON_KEY": "anon_key",
        "DATABASE_URL": "database_url",
        "SUPABASE_AUTO_MIGRATE": "auto_migrate",
    }
    for env_key, setting_key in supabase_overrides.items():
        if env_key in env:
            config["supabase"][setting_key] = env[env_key]

    if "SUPABASE_AUTO_MIGRATE" in env:
        auto_migrate_value = env["SUPABASE_AUTO_MIGRATE"].strip().lower()
        if auto_migrate_value not in {"true", "false"}:
            raise ValueError("SUPABASE_AUTO_MIGRATE must be either 'true' or 'false'")
        config["supabase"]["auto_migrate"] = auto_migrate_value == "true"

    if "DEBUG" in env:
        debug_value = env["DEBUG"].strip().lower()
        if debug_value not in {"true", "false"}:
            raise ValueError("DEBUG must be either 'true' or 'false'")
        config["app"]["debug"] = debug_value == "true"

    return AppSettings.model_validate(config)
