"""Versioned evaluation annotations and predictions. Human review is an external attestation."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Verdict = Literal["SUPPORTED", "CONTRADICTED", "INSUFFICIENT_EVIDENCE", "NOT_EVALUATED"]


class StrictRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Span(StrictRecord):
    evidence_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    document_version_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    quote_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    article: str | None
    clause: str | None
    point: str | None
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    role: Literal["evidence", "condition", "exception"] = "evidence"

    @model_validator(mode="after")
    def bounds(self):
        if self.end <= self.start:
            raise ValueError("span must be nonempty [start,end)")
        return self


class ClaimLabel(StrictRecord):
    claim_id: str = Field(min_length=1)
    verdict: Verdict
    evidence_ids: list[str]

    @model_validator(mode="after")
    def source_required(self):
        if self.verdict in {"SUPPORTED", "CONTRADICTED"} and not self.evidence_ids:
            raise ValueError("Supported or contradicted gold requires evidence")
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("Duplicate evidence identity")
        return self


class Annotation(StrictRecord):
    schema_version: Literal["2"] = "2"
    question_id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    legal_domain: str
    query_intent: str
    provenance: Literal["human_approved", "draft", "synthetic", "exploratory", "held_out"]
    reviewer_id: str | None = None
    reviewer_type: Literal["human"] | None = None
    reviewed_at: str | None = None
    relevant_units: list[str] | None = None
    spans: list[Span] | None = None
    temporal_applicability: Literal["APPLICABLE", "INAPPLICABLE", "UNKNOWN"]
    as_of_date: str | None = None
    expected_answer: str | None = None
    expected_abstention: bool | None = None
    claims: list[ClaimLabel] | None = None

    @model_validator(mode="after")
    def review_and_identity(self):
        if self.provenance in {"human_approved", "held_out"}:
            if self.reviewer_type != "human" or not self.reviewer_id or not self.reviewed_at:
                raise ValueError("Human-reviewed and held-out labels require reviewer attestation")
            if datetime.fromisoformat(self.reviewed_at).tzinfo is None:
                raise ValueError("Review timestamp must include timezone")
        if self.relevant_units is not None and len(set(self.relevant_units)) != len(self.relevant_units):
            raise ValueError("relevant units must be unique")
        if self.claims is not None and len({c.claim_id for c in self.claims}) != len(self.claims):
            raise ValueError("claim IDs must be unique")
        return self


class ClaimPrediction(StrictRecord):
    claim_id: str
    verdict: Verdict
    evidence_ids: list[str]


class Prediction(StrictRecord):
    question_id: str
    ranked_units: list[str] = Field(default_factory=list)
    context: list[Span] = Field(default_factory=list)
    claims: list[ClaimPrediction] = Field(default_factory=list)
    abstained: bool | None = None
    failed: bool = False
    latency_ms: float | int = Field(ge=0, allow_inf_nan=False)
    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def unique_predictions(self):
        if len(set(self.ranked_units)) != len(self.ranked_units):
            raise ValueError("deduplicate retrieval units while preserving unresolved slots")
        if len({c.claim_id for c in self.claims}) != len(self.claims):
            raise ValueError("duplicate predicted claim ID")
        if self.failed and self.abstained is not None:
            raise ValueError("failure is not an abstention decision")
        return self
