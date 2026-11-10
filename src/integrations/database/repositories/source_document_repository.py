"""Repository operations for crawled source-document metadata."""

import asyncio
from uuid import UUID

import httpx
from postgrest.exceptions import APIError
from supabase import Client

from src.application.dto.source_document import SourceDocumentWrite
from src.integrations.database.repositories.rpc import DatabaseRepositoryError, SupabaseRpcRepository


class SourceDocumentRepository(SupabaseRpcRepository):
    """Create/update crawled documents and load source metadata."""

    def __init__(self, client: Client) -> None:
        super().__init__(client)

    async def upsert(self, document: SourceDocumentWrite) -> dict[str, object]:
        """Insert or update a source using its stable upstream identity."""
        result = await self.call_rpc(
            "upsert_source_document",
            {"p_document": document.model_dump(mode="json")},
        )
        if not isinstance(result, dict):
            raise DatabaseRepositoryError("upsert_source_document returned an invalid response")
        return result

    async def get(self, source_document_id: UUID) -> dict[str, object] | None:
        """Load a source document by its database identifier."""
        result = await self.call_rpc(
            "get_source_document",
            {"p_source_document_id": str(source_document_id)},
        )
        if result is None:
            return None
        if not isinstance(result, dict):
            raise DatabaseRepositoryError("get_source_document returned an invalid response")
        return result

    async def get_by_source_record_id(
        self,
        source_id: str,
        source_record_id: str,
    ) -> dict[str, object] | None:
        """Load a source document using its stable upstream identity."""
        try:
            response = await asyncio.to_thread(
                lambda: (
                    self._client.table("source_documents")
                    .select("id,raw_file_ref,raw_file_sha256,raw_content_ref,raw_content_sha256,raw_metadata")
                    .eq("source_id", source_id)
                    .eq("source_record_id", source_record_id)
                    .limit(1)
                    .execute()
                )
            )
        except (APIError, httpx.HTTPError) as error:
            raise DatabaseRepositoryError("Loading source document by source identity failed") from error
        if response is None:
            raise DatabaseRepositoryError("Source-document lookup returned no response")
        rows = response.data
        if not isinstance(rows, list):
            raise DatabaseRepositoryError("Source-document lookup returned an invalid response")
        if not rows:
            return None
        if len(rows) != 1 or not isinstance(rows[0], dict):
            raise DatabaseRepositoryError("Source-document lookup returned an invalid response")
        return rows[0]
