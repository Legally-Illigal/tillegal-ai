"""Validated metadata for a crawled legal source document."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class SourceDocumentWrite(BaseModel):
    """Validated document metadata accepted by the source-document repository."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str = Field(min_length=1)
    source_record_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    source_snapshot_id: str | None = None
    language: str | None = None
    source_url: str | None = None
    issued_on: date | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    effect_status_reported: str | None = None
    raw_file_ref: str | None = None
    raw_file_sha256: str | None = None
    raw_content_ref: str | None = None
    raw_content_sha256: str | None = None
    raw_metadata: dict[str, object] = Field(default_factory=dict)
    usage_policy: str = "EXPERIMENTAL_ONLY"
    collected_at: datetime | None = None
