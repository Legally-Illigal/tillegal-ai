"""Small read-only ports; concrete SDKs stay in integration adapters."""

from typing import Protocol
from uuid import UUID

from src.applications.tillegal.retrieval.document_models import SparseSearchHit, SparseSearchRequest


class SparseRetriever(Protocol):
    async def search(self, request: SparseSearchRequest) -> tuple[SparseSearchHit, ...]: ...


class ChunkReader(Protocol):
    async def get_by_ids(self, chunk_ids: tuple[UUID, ...]) -> tuple[dict[str, object], ...]: ...


class SourceReader(Protocol):
    async def get(self, source_document_id: UUID) -> dict[str, object] | None: ...


class IndexReader(Protocol):
    async def get_index(self, index_name: str) -> dict[str, object] | None: ...


class QueryEmbedder(Protocol):
    """Reserved for Task 5; no encoder implementation or model loading here."""

    async def encode_query(self, query: str) -> tuple[float, ...]: ...
