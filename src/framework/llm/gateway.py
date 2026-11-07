"""Answer generation provider selection for the offline pilot."""
import json
from http.client import HTTPConnection, HTTPException

from ai_core.rag_generation import GenerationError, GenerationProvider, GenerationText, MockProvider
from src.framework.llm.providers.gemini import FreeTierPolicy, GeminiProvider


class LocalChatProvider:
    """One OpenAI-compatible request to a local, operator-managed runtime."""
    mode = "local"

    def __init__(self, model: str, port: int):
        if not model.strip() or not 1 <= port <= 65535:
            raise ValueError("Configure a local answer model and valid port")
        self.model = model
        self.port = port

    def generate(self, messages):
        return self._chat(messages, {})

    def generate_structured(self, messages, schema):
        return self._chat(messages, {"response_format": {"type": "json_schema", "json_schema":
                          {"name": schema.__name__, "strict": True, "schema": schema.model_json_schema()}}})

    def _chat(self, messages, options):
        connection = HTTPConnection("127.0.0.1", self.port, timeout=25)
        try:
            body = json.dumps({"model": self.model, "messages": messages, "stream": False,
                               "max_tokens": 1024, **options}, ensure_ascii=False).encode()
            connection.request("POST", "/v1/chat/completions", body, {"Content-Type": "application/json"})
            response = connection.getresponse()
            if response.status == 429:
                raise GenerationError("PROVIDER_RATE_LIMIT")
            if response.status != 200:
                raise GenerationError("PROVIDER_UNAVAILABLE")
            data = response.read(1048577)
            if len(data) > 1048576:
                raise GenerationError("PROVIDER_RESPONSE_LIMIT")
            obj = json.loads(data)
            choice, = obj["choices"]
            if (choice["finish_reason"] != "stop" or choice["message"].get("tool_calls")
                    or not isinstance(choice["message"]["content"], str)):
                raise GenerationError("INVALID_OUTPUT")
            usage = obj.get("usage") or {}
            counts = {key: usage[key] for key in ("prompt_tokens", "completion_tokens")
                      if type(usage.get(key)) is int and usage[key] >= 0}
            return GenerationText(choice["message"]["content"], counts)
        except TimeoutError:
            raise GenerationError("PROVIDER_TIMEOUT") from None
        except (OSError, HTTPException):
            raise GenerationError("PROVIDER_UNAVAILABLE") from None
        except (TypeError, KeyError, ValueError, AttributeError) as exc:
            if isinstance(exc, GenerationError):
                raise
            raise GenerationError("INVALID_OUTPUT") from None
        finally:
            connection.close()


def answer_provider(config, *, profile="ANSWER", gemini_policy: FreeTierPolicy | None = None) -> GenerationProvider:
    provider = config.get(f"TILLEGAL_{profile}_PROVIDER", config.get("TILLEGAL_ANSWER_PROVIDER", "mock"))
    if provider == "gemini":
        return GeminiProvider(config.get(f"TILLEGAL_{profile}_MODEL", ""), gemini_policy)
    if provider == "mock":
        return MockProvider()
    if provider == "local":
        return LocalChatProvider(config.get(f"TILLEGAL_{profile}_MODEL", config.get("TILLEGAL_ANSWER_MODEL", "")),
                                 int(config.get("TILLEGAL_LOCAL_PORT", "8080")))
    raise ValueError("Unsupported answer provider")
