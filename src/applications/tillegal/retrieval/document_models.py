"""Typed contracts for legal-document retrieval."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictStr, field_validator

EMBEDDING_DIMENSION = 1536
MAX_RETRIEVAL_RESULTS = 50


class VectorSearchRequest(BaseModel):
    """A dense-search request with explicit source-governance filters."""

    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)

    dense_index_name: str = Field(min_length=1, max_length=128)
    query_embedding: tuple[float, ...] = Field(
        min_length=EMBEDDING_DIMENSION,
        max_length=EMBEDDING_DIMENSION,
    )
    top_k: int = Field(default=10, ge=1, le=MAX_RETRIEVAL_RESULTS)
    as_of_date: date
    allowed_legal_approvals: tuple[StrictStr, ...] = Field(min_length=1)
    allowed_usage_policies: tuple[StrictStr, ...] = Field(min_length=1)
    allowed_provenance_statuses: tuple[StrictStr, ...] = Field(min_length=1)
    allowed_temporal_statuses: tuple[StrictStr, ...] = Field(min_length=1)
    allowed_rights_statuses: tuple[StrictStr, ...] = Field(min_length=1)

    @field_validator("dense_index_name")
    @classmethod
    def validate_dense_index_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("dense_index_name must not be blank")
        return normalized

    @field_validator(
        "allowed_legal_approvals",
        "allowed_usage_policies",
        "allowed_provenance_statuses",
        "allowed_temporal_statuses",
        "allowed_rights_statuses",
        mode="before",
    )
    @classmethod
    def validate_status_allowlist(cls, values: object) -> tuple[str, ...]:
        if not isinstance(values, (list, tuple)) or not values:
            raise ValueError("Each source-governance status allowlist must be non-empty")
        if any(not isinstance(value, str) or not value.strip() for value in values):
            raise ValueError("Source-governance statuses must be non-blank strings")
        return tuple(dict.fromkeys(value.strip() for value in values))

    @field_validator("query_embedding")
    @classmethod
    def validate_query_embedding(cls, values: tuple[float, ...]) -> tuple[float, ...]:
        if not any(value != 0 for value in values):
            raise ValueError("query_embedding must not be a zero vector")
        if any(abs(value) > 3.4028235e38 for value in values):
            raise ValueError("query_embedding values must fit PostgreSQL vector components")
        return values


class RetrievedEvidence(BaseModel):
    """Evidence returned by the PostgreSQL vector-search function."""

    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)

    retrieval_chunk_id: UUID
    source_document_id: UUID
    document_structure_id: UUID
    dense_index_id: UUID
    chunk_key: str
    content: str
    similarity: float
    node_id: str | None
    block_id: str | None
    chunk_type: str
    start_offset: int | None
    end_offset: int | None
    chunk_metadata: dict[str, object]
    source_id: str | None
    source_record_id: str | None
    source_snapshot_id: str | None
    document_number: str | None
    title: str
    document_type: str | None
    issuing_authority: str | None
    language: str | None
    source_url: str | None
    issued_on: date | None
    effective_from: date | None
    effective_to: date | None
    effect_status_reported: str | None
    usage_policy: str
    legal_approval: str
    provenance_status: str
    temporal_status: str
    rights_status: str
    source_metadata: dict[str, object]
