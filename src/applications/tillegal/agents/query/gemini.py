"""Query-only Gemini configuration; preserve unrelated provider settings."""

import os
from collections.abc import Mapping
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError, field_validator

from src.applications.tillegal.agents.query.semantic import SemanticQueryAgent
from src.framework.llm.providers.gemini_adapter import GeminiStructuredCompletion

DEFAULT_MODEL_CONFIG = Path(__file__).resolve().parents[5] / "configs/models.yaml"


class GeminiQuerySettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)
    api_key: SecretStr = Field(repr=False)
    model: str = Field(pattern=r"^gemini-[a-z0-9][a-z0-9._-]*$")
    timeout_seconds: float = Field(gt=0, le=120)
    max_output_tokens: int = Field(default=4096, ge=128, le=8192, strict=True)

    @field_validator("api_key")
    @classmethod
    def configured_key(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().strip():
            raise ValueError("GOOGLE_API_KEY_REQUIRED")
        return value


def create_gemini_query_agent(
    *,
    environ: Mapping[str, str] | None = None,
    config_path: Path = DEFAULT_MODEL_CONFIG,
) -> SemanticQueryAgent:
    """Read GOOGLE_API_KEY without changing process env or loading/rewriting .env.

    Explicit mapping supports isolated tests. Only the query_semantic profile is
    consumed: other agents keep their existing provider/default-model choices.
    """
    env = os.environ if environ is None else environ
    try:
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        profile = config["profiles"]["query_semantic"]
        provider = config["providers"]["gemini"]
        if profile["provider"] != "gemini" or provider["api_key_env"] != "GOOGLE_API_KEY":
            raise ValueError("Invalid query provider")
        if provider["enabled"] is not True:
            raise ValueError("Disabled query provider")
        settings = GeminiQuerySettings(
            api_key=env.get("GOOGLE_API_KEY", ""),
            model=env.get("GEMINI_MODEL", profile["model"]),
            timeout_seconds=env.get("QUERY_LLM_TIMEOUT_SECONDS", provider["timeout_seconds"]),
            max_output_tokens=profile.get("max_output_tokens", 4096),
        )
    except (OSError, KeyError, TypeError, ValueError, yaml.YAMLError, ValidationError):
        # Do not include Pydantic input_values or raw YAML/provider data in errors.
        raise ValueError("GEMINI_QUERY_CONFIGURATION_INVALID") from None
    return SemanticQueryAgent(
        complete=GeminiStructuredCompletion(
            settings.api_key,
            timeout_seconds=settings.timeout_seconds,
            max_output_tokens=settings.max_output_tokens,
        ),
        model=settings.model,
        timeout_seconds=settings.timeout_seconds,
    )
