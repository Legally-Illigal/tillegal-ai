"""Propagate a validated request ID through the ASGI request lifecycle."""

import logging
import re
import time
from collections.abc import Iterable
from uuid import uuid4

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from src.framework.observability.correlation import bind_request_context
from src.framework.observability.events import log_event

_REQUEST_ID_HEADER = b"x-request-id"
_REQUEST_ID_PATTERN = re.compile(r"[A-Za-z0-9._:-]{1,128}\Z")


class RequestContextMiddleware:
    """Add request correlation to logs and echo the ID in the response."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = self._request_id_from_headers(scope.get("headers", ()))
        state = scope.setdefault("state", {})
        state["request_id"] = request_id
        started_at = time.perf_counter()
        status_code: int | None = None

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = [
                    (name, value)
                    for name, value in message.get("headers", [])
                    if name.lower() != _REQUEST_ID_HEADER
                ]
                headers.append((_REQUEST_ID_HEADER, request_id.encode("ascii")))
                message["headers"] = headers
            await send(message)

        with bind_request_context(request_id):
            log_event("request_started", component="api.request")
            try:
                await self.app(scope, receive, send_with_request_id)
            except Exception as error:
                log_event(
                    "request_failed",
                    component="api.request",
                    level=logging.ERROR,
                    duration_ms=self._duration_ms(started_at),
                    error_category=type(error).__name__,
                    status_code=status_code,
                )
                raise
            else:
                route = scope.get("route")
                log_level = logging.INFO
                if status_code is not None and status_code >= 500:
                    log_level = logging.ERROR
                elif status_code is not None and status_code >= 400:
                    log_level = logging.WARNING
                log_event(
                    "request_completed",
                    component="api.request",
                    level=log_level,
                    duration_ms=self._duration_ms(started_at),
                    method=scope.get("method"),
                    route=getattr(route, "path", None),
                    status_code=status_code,
                )

    @staticmethod
    def _request_id_from_headers(headers: Iterable[tuple[bytes, bytes]]) -> str:
        for name, value in headers:
            if name.lower() == _REQUEST_ID_HEADER:
                try:
                    candidate = value.decode("ascii")
                except UnicodeDecodeError:
                    break
                if _REQUEST_ID_PATTERN.fullmatch(candidate):
                    return candidate
                break
        return str(uuid4())

    @staticmethod
    def _duration_ms(started_at: float) -> float:
        return round((time.perf_counter() - started_at) * 1000, 3)
