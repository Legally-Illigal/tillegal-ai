"""Persistence contract for crawled source-document metadata."""

from typing import Protocol

from src.application.dto.source_document import SourceDocumentWrite


class SourceDocumentStore(Protocol):
    """Load and upsert source documents by their stable source identity."""

    async def get_by_source_record_id(
        self,
        source_id: str,
        source_record_id: str,
    ) -> dict[str, object] | None: ...

    async def upsert(self, document: SourceDocumentWrite) -> dict[str, object]: ...
