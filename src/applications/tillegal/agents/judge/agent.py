"""Pre-generation sufficiency Judge; output is the final Judge contract directly."""

import json
import re
from copy import deepcopy
from dataclasses import dataclass
from time import perf_counter
from typing import Protocol

from src.applications.tillegal.agents.judge.prompts import PROMPT_VERSION, SYSTEM_PROMPT
from src.applications.tillegal.agents.judge.schemas import (
    OUTPUT_SCHEMA,
    JudgeError,
    anthropic_output_schema,
    error_result,
    validate_input,
    validate_output,
)
from src.applications.tillegal.agents.judge.support import GenerationError, GenerationText, canonical_json, strict_json


class JudgeProvider(Protocol):
    mode: str
    model: str

    def generate(self, messages: list[dict]) -> str: ...


@dataclass(frozen=True)
class JudgeLimits:
    max_input_bytes: int = 100000
    max_output_chars: int = 24000

    def __post_init__(self):
        if (
            type(self.max_input_bytes) is not int
            or not 1024 <= self.max_input_bytes <= 120000
            or type(self.max_output_chars) is not int
            or not 128 <= self.max_output_chars <= 65536
        ):
            raise JudgeError("JUDGE_CONFIGURATION_ERROR")


def judge_messages(value, limits=None):
    limits = limits or JudgeLimits()
    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
            + "\nPROMPT_VERSION="
            + PROMPT_VERSION
            + "\nOUTPUT_SCHEMA="
            + json.dumps(OUTPUT_SCHEMA, ensure_ascii=False),
        },
        {"role": "user", "content": canonical_json(value).decode("utf-8")},
    ]
    if len(canonical_json(messages)) > limits.max_input_bytes:
        raise JudgeError("JUDGE_INPUT_LIMIT")
    return messages


class FixtureJudgeProvider:
    """Replay an explicitly supplied response. No semantic evaluation or keyword rules."""

    mode = "mock"
    model = "fixture-replay-no-semantic-evaluation"

    def __init__(self, response):
        self.response = deepcopy(response)

    def generate(self, messages):
        return self.response if isinstance(self.response, str) else json.dumps(self.response, ensure_ascii=False)


class JudgeAgent:
    def __init__(self, provider: JudgeProvider, limits=None):
        self.provider = provider
        self.limits = limits or JudgeLimits()

    def evaluate(self, value, *, telemetry=None):
        """Return Judge output only; optional caller-owned telemetry dict is separate.

        No automatic retry. The provider must enforce its I/O timeout. A custom
        synchronous provider cannot be forcibly cancelled here; use an outer
        worker/process deadline in the Orchestrator when needed.
        """
        started, stage = perf_counter(), "input"
        info = {
            "prompt_version": PROMPT_VERSION,
            "model": getattr(self.provider, "model", None),
            "provider_mode": getattr(self.provider, "mode", None),
            "provider_name": getattr(self.provider, "provider_name", None),
            "provider_calls": 0,
            "error_code": None,
            "stage": stage,
        }
        try:
            validated = validate_input(value)
            # Bound all input, including the empty-evidence fast path, without slicing.
            messages = judge_messages(validated, self.limits)
            info["input_bytes"] = len(canonical_json(messages))
            if not validated["evidence"]:
                result = {
                    "status": "INSUFFICIENT",
                    "issue_checks": [
                        {"issue_id": i["issue_id"], "evidence_ids": [], "coverage": "none"}
                        for i in validated["query_plan"]["issues"]
                    ],
                    "missing_items": [
                        "Chưa có evidence cho " + i["issue_id"] for i in validated["query_plan"]["issues"]
                    ],
                    "next_queries": [],
                    "usable_evidence_ids": [],
                    "explanation": "Evidence rỗng; chưa có căn cứ để đánh giá các issue.",
                    "error_code": None,
                }
                return validate_output(result, validated)
            stage = "provider"
            # Anthropic's legacy structured default is the three-field draft schema.
            # Never send Judge prompts under that constraint, even through Python API.
            if getattr(self.provider, "structured_output", False):
                schema = getattr(self.provider, "output_schema", None)
                if schema not in (OUTPUT_SCHEMA, anthropic_output_schema()):
                    raise JudgeError("JUDGE_PROVIDER_SCHEMA_MISMATCH")
            info["provider_calls"] = 1
            raw = self.provider.generate(deepcopy(messages))
            # Only allowlisted metadata, never raw text, prompts, keys, or exception messages.
            if isinstance(raw, GenerationText):
                info["provider"] = {
                    k: deepcopy(v)
                    for k, v in raw.metadata.items()
                    if k
                    in (
                        "requested_model",
                        "returned_model",
                        "usage",
                        "stop_reason",
                        "http_status",
                        "latency_ms",
                        "stream_summary",
                        "api_status",
                        "error_reason",
                        "timeout_kind",
                    )
                }
            stage = "output"
            if not isinstance(raw, str):
                raise JudgeError("INVALID_OUTPUT_SCHEMA")
            if len(raw) > self.limits.max_output_chars:
                raise JudgeError("JUDGE_OUTPUT_LIMIT")
            try:
                parsed = strict_json(raw)
            except (ValueError, RecursionError):
                raise JudgeError("INVALID_OUTPUT_JSON") from None
            result = validate_output(parsed, validated)
            info["error_code"] = result["error_code"]
            return result
        except JudgeError as exc:
            info["error_code"] = exc.code
            return error_result(exc.code)
        except GenerationError as exc:
            if isinstance(getattr(exc, "metadata", None), dict):
                info["provider"] = {
                    k: deepcopy(v)
                    for k, v in exc.metadata.items()
                    if k
                    in (
                        "requested_model",
                        "returned_model",
                        "usage",
                        "stop_reason",
                        "http_status",
                        "latency_ms",
                        "stream_summary",
                        "api_status",
                        "error_reason",
                        "timeout_kind",
                    )
                }
            # Existing provider codes contain no credentials. No exception text is logged.
            code = (
                exc.code
                if isinstance(exc.code, str) and re.fullmatch(r"[A-Z][A-Z0-9_]{0,127}", exc.code)
                else "PROVIDER_ERROR"
            )
            info["error_code"] = code
            return error_result(code)
        except TimeoutError:
            info["error_code"] = "PROVIDER_TIMEOUT" if stage == "provider" else "JUDGE_INTERNAL_ERROR"
            return error_result(info["error_code"])
        except Exception:
            info["error_code"] = "PROVIDER_ERROR" if stage == "provider" else "JUDGE_INTERNAL_ERROR"
            return error_result(info["error_code"])
        finally:
            info.update(stage=stage, latency_ms=round((perf_counter() - started) * 1000, 3))
            if telemetry is not None:
                telemetry.update(deepcopy(info))
