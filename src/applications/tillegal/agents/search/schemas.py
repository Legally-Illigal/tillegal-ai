"""Additive evidence/provenance contract; scores remain local to each response."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.applications.tillegal.retrieval.contracts import UnifiedEvidence


class EvidenceOccurrence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    subquery_index: int = Field(ge=0)
    response_index: int = Field(ge=0)
    query: str
    request_id: str
    rank: int = Field(ge=1)
    raw_score: float
    score_kind: Literal["BM25", "COSINE_SIMILARITY", "RRF"]
    issue_indices: tuple[int, ...] = ()


class AggregatedEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    evidence: UnifiedEvidence
    occurrences: tuple[EvidenceOccurrence, ...] = Field(min_length=1)
