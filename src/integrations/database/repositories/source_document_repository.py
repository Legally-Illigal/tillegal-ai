"""Repository operations for crawled source-document metadata."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from supabase import Client

from src.integrations.database.repositories.rpc import DatabaseRepositoryError, SupabaseRpcRepository


class SourceDocumentWrite(BaseModel):
    """Validated document metadata accepted by the source-document RPC."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str = Field(min_length=1)
    source_record_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    source_snapshot_id: str | None = None
    document_number: str | None = None
    document_type: str | None = None
    issuing_authority: str | None = None
    language: str | None = None
    source_url: str | None = None
    raw_content_format: Literal["html", "text"] | None = None
    raw_content: str | None = None
    issued_on: date | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    effect_status_reported: str | None = None
    status_observed_at: datetime | None = None
    raw_file_ref: str | None = None
    raw_content_ref: str | None = None
    raw_file_sha256: str | None = None
    raw_content_sha256: str | None = None
    raw_metadata: dict[str, object] = Field(default_factory=dict)
    usage_policy: str = "EXPERIMENTAL_ONLY"
    legal_approval: str = "QUARANTINE"
    provenance_status: str = "UNVERIFIED"
    temporal_status: str = "UNKNOWN"
    rights_status: str = "UNVERIFIED"
    collected_at: datetime | None = None


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
