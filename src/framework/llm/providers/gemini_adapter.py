"""Gemini structured completion through the existing LiteLLM dependency."""

import asyncio
import json
from dataclasses import dataclass, field

from pydantic import SecretStr


class GeminiProviderError(RuntimeError):
    """Safe diagnostics only; upstream messages, headers and bodies stay private."""

    def __init__(self, code: str, http_status: int | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.http_status = http_status


async def _acompletion(**kwargs):
    # Keep the provider SDK out of deterministic/offline startup.
    def load_completion():
        from litellm import acompletion

        return acompletion

    completion = await asyncio.to_thread(load_completion)
    return await completion(**kwargs)


@dataclass(frozen=True)
class GeminiStructuredCompletion:
    api_key: SecretStr = field(repr=False)
    timeout_seconds: float = 30
    max_output_tokens: int = 4096

    def __post_init__(self) -> None:
        if not self.api_key.get_secret_value().strip():
            raise ValueError("GOOGLE_API_KEY_REQUIRED")
        if not 0 < self.timeout_seconds < float("inf") or not 128 <= self.max_output_tokens <= 8192:
            raise ValueError("GEMINI_INVALID_OPTIONS")

    async def __call__(self, *, model: str, system: str, user: str, schema: dict) -> str:
        """Return JSON text; SemanticQueryAgent remains the strict validation owner."""
        try:
            async with asyncio.timeout(self.timeout_seconds):
                response = await _acompletion(
                    model=f"gemini/{model}",
                    api_key=self.api_key.get_secret_value(),
                    messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                    response_format={"type": "json_object", "response_schema": schema},
                    max_tokens=self.max_output_tokens,
                    timeout=self.timeout_seconds,
                    num_retries=0,
                    caching=False,
                    **{"no-log": True},
                )
        except TimeoutError:
            raise TimeoutError("GEMINI_TIMEOUT") from None
        except Exception as error:
            if type(error).__name__ in {"Timeout", "APITimeoutError"}:
                raise TimeoutError("GEMINI_TIMEOUT") from None
            status = getattr(error, "status_code", None)
            status = status if type(status) is int and 100 <= status <= 599 else None
            code = {
                400: "GEMINI_INVALID_REQUEST",
                401: "GEMINI_AUTHENTICATION_FAILED",
                403: "GEMINI_PERMISSION_DENIED",
                404: "GEMINI_MODEL_NOT_FOUND",
                429: "GEMINI_RATE_LIMITED",
            }.get(status, "GEMINI_SERVICE_UNAVAILABLE" if status and status >= 500 else "GEMINI_REQUEST_FAILED")
            raise GeminiProviderError(code, status) from None
        try:
            choice = response.choices[0]
            if choice.finish_reason != "stop":
                raise ValueError("Incomplete or blocked response")
            content = choice.message.content
            if not isinstance(content, str) or not 1 <= len(content) <= 32000:
                raise ValueError("Invalid content")
            if not isinstance(json.loads(content), dict):
                raise ValueError("Expected JSON object")
        except (AttributeError, IndexError, TypeError, ValueError):
            raise GeminiProviderError("GEMINI_INVALID_RESPONSE") from None
        return content
