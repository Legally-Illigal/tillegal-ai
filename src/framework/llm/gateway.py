"""Small shared boundary for transferred synchronous provider adapters."""

import threading
from copy import deepcopy


class ModelGateway:
    """Own a configured provider; serialize calls even after async caller cancellation.

    Provider enforces network timeout. Agents validate domain output schemas.
    No retries or implicit fallback are introduced here.
    """

    def __init__(self, provider):
        self.provider = provider
        self.model = provider.model
        self.mode = provider.mode
        self.provider_name = getattr(provider, "provider_name", None)
        self._lock = threading.Lock()

    def generate(self, messages: list[dict]) -> str:
        with self._lock:
            return self.provider.generate(deepcopy(messages))
