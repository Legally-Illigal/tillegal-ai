"""Live Gemini transport; full Judge validation remains local."""

import asyncio

from src.applications.tillegal.agents.judge.schemas import OUTPUT_SCHEMA
from src.applications.tillegal.agents.judge.support import GenerationError
from src.framework.llm.providers.gemini_adapter import GeminiProviderError, GeminiStructuredCompletion


def wire_schema(value):
    omitted = {
        "minLength",
        "maxLength",
        "minItems",
        "maxItems",
        "uniqueItems",
        "pattern",
        "format",
        "minimum",
        "maximum",
    }
    if isinstance(value, dict):
        return {k: wire_schema(v) for k, v in value.items() if k not in omitted}
    if isinstance(value, list):
        return [wire_schema(v) for v in value]
    return value


class LiveGeminiJudge:
    mode = "live"
    provider_name = "gemini"
    structured_output = True
    output_schema = OUTPUT_SCHEMA

    def __init__(self, api_key, model):
        self.api_key = api_key
        self.model = model

    def generate(self, messages):
        completion = GeminiStructuredCompletion(self.api_key, timeout_seconds=90, max_output_tokens=8192)
        try:
            return asyncio.run(
                completion(
                    model=self.model,
                    system=messages[0]["content"],
                    user=messages[1]["content"],
                    schema=wire_schema(OUTPUT_SCHEMA),
                )
            )
        except GeminiProviderError as error:
            raise GenerationError(error.code) from None
