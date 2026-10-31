"""Application-facing retrieval contract."""

from typing import Protocol

from src.applications.tillegal.retrieval.document_models import RetrievedEvidence, VectorSearchRequest


class RetrievalError(RuntimeError):
    """Raised when a retrieval adapter cannot return valid evidence."""


class LegalRetriever(Protocol):
    """Port used by legal workflow tools to retrieve evidence."""

    async def search(self, request: VectorSearchRequest) -> tuple[RetrievedEvidence, ...]:
        """Return evidence matching the request or raise RetrievalError."""
