"""Gemini wire adapter. A trusted project policy must authorize every disclosure."""
import json
import os
import re
from collections import deque
from hashlib import sha256
from http.client import HTTPSConnection, HTTPException
from threading import Lock
from time import monotonic
from typing import Protocol

from ai_core.rag_generation import GenerationError, GenerationText


class FreeTierPolicy(Protocol):
    allowed_models: frozenset[str]

    def reserve(self, *, key_fingerprint: str, model: str, prompt: bytes, max_output_tokens: int) -> bool:
        """Atomically enforce verified project/key binding, billing disabled, free model allowlist,
        data permission, per-minute/daily quotas and the model-specific input/output token budget.
        A missing, stale or unavailable decision must deny. No implementation is installed in the pilot.
        """
        ...


def gemini_payload(messages):
    system, user = messages
    if system["role"] != "system" or user["role"] != "user":
        raise GenerationError("INVALID_PROVIDER_INPUT")
    body = {"systemInstruction": {"parts": [{"text": system["content"]}]},
            "contents": [{"role": "user", "parts": [{"text": user["content"]}]}],
            "generationConfig": {"candidateCount": 1, "maxOutputTokens": 1024,
                                 "responseMimeType": "application/json"}}
    payload = json.dumps(body, ensure_ascii=False).encode()
    if len(payload) > 120000:
        raise GenerationError("PROVIDER_INPUT_LIMIT")
    return payload


def gemini_result(body):
    try:
        parsed = json.loads(body)
        candidate, = parsed["candidates"]
        part, = candidate["content"]["parts"]
        if candidate["finishReason"] != "STOP" or set(part) != {"text"} or not isinstance(part["text"], str):
            raise ValueError()
        usage = parsed.get("usageMetadata", {})
        counts = {name: usage[field] for field, name in (("promptTokenCount", "prompt_tokens"),
                  ("candidatesTokenCount", "completion_tokens"), ("totalTokenCount", "total_tokens"))
                  if type(usage.get(field)) is int and usage[field] >= 0}
        return GenerationText(part["text"], counts)
    except (TypeError, ValueError, KeyError, AttributeError, RecursionError):
        raise GenerationError("INVALID_OUTPUT") from None


class GeminiProvider:
    mode = "gemini"

    def __init__(self, model: str, policy: FreeTierPolicy | None):
        if policy is None:
            raise ValueError("GEMINI_DISABLED: project free tier, billing and data policy are unverified")
        if not re.fullmatch(r"gemini-[a-z0-9.-]{1,80}", model) or model not in policy.allowed_models:
            raise ValueError("Gemini model is outside the approved allowlist")
        self.model = model
        self.policy = policy
        self._attempts = deque()
        self._lock = Lock()

    def reserve_local_attempt(self):
        with self._lock:
            now = monotonic()
            while self._attempts and now - self._attempts[0] >= 86400:
                self._attempts.popleft()
            if len(self._attempts) >= 5 or (self._attempts and now - self._attempts[-1] < 60):
                raise GenerationError("PROVIDER_RATE_LIMIT")
            self._attempts.append(now)

    def generate(self, messages):
        payload = gemini_payload(messages)
        key = os.environ.get("GOOGLE_API_KEY", "")
        if not re.fullmatch(r"[A-Za-z0-9_-]+", key):
            raise GenerationError("PROVIDER_CONFIGURATION_ERROR")
        try:
            granted = self.policy.reserve(key_fingerprint=sha256(key.encode()).hexdigest(),
                                          model=self.model, prompt=payload, max_output_tokens=1024)
        except Exception:
            raise GenerationError("GEMINI_FREE_TIER_UNCONFIRMED") from None
        if granted is not True:
            raise GenerationError("GEMINI_FREE_TIER_UNCONFIRMED")
        self.reserve_local_attempt()
        conn = HTTPSConnection("generativelanguage.googleapis.com", timeout=25)
        try:
            conn.request("POST", f"/v1beta/models/{self.model}:generateContent", payload,
                         {"Content-Type": "application/json", "x-goog-api-key": key})
            response = conn.getresponse()
            if response.status == 429:
                raise GenerationError("PROVIDER_RATE_LIMIT")
            if response.status != 200:
                raise GenerationError("PROVIDER_UNAVAILABLE")
            body = response.read(1048577)
            if len(body) > 1048576:
                raise GenerationError("PROVIDER_RESPONSE_LIMIT")
            return gemini_result(body)
        except TimeoutError:
            raise GenerationError("PROVIDER_TIMEOUT") from None
        except (OSError, HTTPException):
            raise GenerationError("PROVIDER_UNAVAILABLE") from None
        finally:
            conn.close()
