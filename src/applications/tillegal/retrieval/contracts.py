"""Text retrieval contracts. Scores and source claims retain their original meaning."""

from datetime import date, datetime
from enum import StrEnum
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, field_validator, model_validator

from src.applications.tillegal.retrieval.errors import RetrievalErrorDetail


class RetrievalMode(StrEnum):
    BM25 = "bm25"
    DENSE = "dense"
    HYBRID = "hybrid"


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)


class RetrievalRequest(ContractModel):
    """Explicit search filters; no implicit date or usage-policy defaults."""

    query: StrictStr = Field(min_length=1, max_length=10_000)
    mode: RetrievalMode
    top_k: StrictInt = Field(default=10, ge=1, le=50)
    as_of_date: date
    allowed_usage_policies: tuple[StrictStr, ...] = Field(min_length=1)

    @field_validator("query")
    @classmethod
    def nonblank_query(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("query must not be blank")
        return value

    @field_validator("allowed_usage_policies")
    @classmethod
    def policies(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(not value.strip() for value in values):
            raise ValueError("policies must not be blank")
        return tuple(dict.fromkeys(value.strip() for value in values))


class IndexIdentity(ContractModel):
    """Observed index metadata, not an immutable corpus snapshot."""

    id: UUID
    index_name: str = Field(min_length=1)
    index_version: str = Field(min_length=1)
    status: str
    updated_at: datetime
    algorithm: str | None = None
    tokenizer: str | None = None


class RetrievalWarning(ContractModel):
    code: str
    message: str
    retrieval_chunk_id: UUID | None = None


class UnifiedEvidence(ContractModel):
    """Stored chunk text, which may include breadcrumbs; never a verified raw quote."""

    retrieval_chunk_id: UUID
    source_document_id: UUID
    document_structure_id: UUID
    chunk_key: str = Field(min_length=1)
    content: str = Field(min_length=1)
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    hash_check: Literal["MATCHED_STORED", "PAYLOAD_ONLY"]
    content_representation: Literal["retrieval_chunk_content"] = "retrieval_chunk_content"
    rank: StrictInt = Field(ge=1)
    raw_score: float
    score_kind: Literal["BM25", "COSINE_SIMILARITY", "RRF"]
    retrieval_method: RetrievalMode
    node_id: str | None
    block_id: str | None
    chunk_type: str = Field(min_length=1)
    start_offset: int | None = Field(ge=0)
    end_offset: int | None = Field(ge=0)
    chunk_metadata: dict[str, object]
    source_id: str | None
    source_record_id: str | None
    source_snapshot_id: str | None
    title: str = Field(min_length=1)
    source_url: str | None
    language: str | None
    issued_on: date | None
    effective_from: date | None
    effective_to: date | None
    effect_status_reported: str | None
    usage_policy: str = Field(min_length=1)
    source_metadata: dict[str, object]

    @model_validator(mode="after")
    def validate_semantics(self) -> Self:
        expected = {RetrievalMode.BM25: "BM25", RetrievalMode.DENSE: "COSINE_SIMILARITY", RetrievalMode.HYBRID: "RRF"}[
            self.retrieval_method
        ]
        if self.score_kind != expected:
            raise ValueError("score kind must match retrieval method")
        if not self.content.strip() or not self.title.strip() or not self.usage_policy.strip():
            raise ValueError("content, title and usage policy must not be blank")
        if self.start_offset is not None and self.end_offset is not None and self.end_offset < self.start_offset:
            raise ValueError("invalid offset range")
        return self


class RetrievalResponse(ContractModel):
    schema_version: Literal["1"] = "1"
    request_id: UUID
    query: str
    query_used: str
    mode: RetrievalMode
    top_k: StrictInt = Field(ge=1, le=50)
    as_of_date: date
    allowed_usage_policies: tuple[str, ...]
    selected_index_name: str
    index: IndexIdentity | None
    status: Literal["OK", "NO_MATCH", "FAILED"]
    evidence: tuple[UnifiedEvidence, ...] = ()
    warnings: tuple[RetrievalWarning, ...] = ()
    error: RetrievalErrorDetail | None = None
    retrieved_at: datetime
    consistency: Literal["BEST_EFFORT"] = "BEST_EFFORT"

    @model_validator(mode="after")
    def validate_outcome(self) -> Self:
        if self.status == "OK" and (not self.evidence or self.error is not None):
            raise ValueError("OK requires evidence and no error")
        if self.status == "NO_MATCH" and (self.evidence or self.error is not None):
            raise ValueError("NO_MATCH requires empty evidence and no error")
        if self.status == "FAILED" and (self.evidence or self.error is None):
            raise ValueError("FAILED requires empty evidence and an error")
        if len(self.evidence) > self.top_k:
            raise ValueError("evidence exceeds requested top_k")
        ids = [item.retrieval_chunk_id for item in self.evidence]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate evidence identities")
        for rank, item in enumerate(self.evidence, 1):
            if item.rank != rank or item.retrieval_method != self.mode:
                raise ValueError("evidence rank/method mismatch")
        if self.retrieved_at.utcoffset() is None:
            raise ValueError("retrieved_at requires a timezone")
        return self
