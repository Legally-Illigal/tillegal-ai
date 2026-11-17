"""Opt-in diagnostics; evidence raw_score always retains its RRF meaning."""

from pathlib import Path
from typing import Literal, Self
from uuid import UUID

from pydantic import Field, StrictInt, field_validator, model_validator

from src.applications.tillegal.retrieval.contracts import ContractModel
from src.applications.tillegal.retrieval.hybrid_models import HybridRetrievalResponse

MODEL_NAME = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
MODEL_REVISION = "1427fd652930e4ba29e8149678df786c240d8825"


class RerankConfig(ContractModel):
    enabled: bool = False
    model_path: Path | None = None
    candidate_pool: StrictInt = Field(default=20, ge=1, le=50)
    batch_size: StrictInt = Field(default=4, ge=1, le=16)
    max_length: StrictInt = Field(default=512, ge=32, le=512)
    inference_timeout_seconds: float = Field(default=10, gt=0)
    total_timeout_seconds: float = Field(default=40, gt=0)


class PairScores(ContractModel):
    scores: tuple[float, ...]
    truncated: tuple[bool, ...]
    cold: bool
    load_seconds: float = Field(ge=0)
    inference_seconds: float = Field(ge=0)

    @field_validator("scores", mode="before")
    @classmethod
    def numeric_scores(cls, values: object) -> object:
        if not isinstance(values, (tuple, list)) or any(
            isinstance(x, bool) or not isinstance(x, (float, int)) for x in values
        ):
            raise ValueError("Scores must be scalar numbers, not booleans or strings")
        return values


class CandidateScore(ContractModel):
    retrieval_chunk_id: UUID
    original_rank: StrictInt = Field(ge=1)
    rrf_score: float
    cross_encoder_score: float | None
    final_rank: StrictInt | None = Field(default=None, ge=1)


class RerankingMetadata(ContractModel):
    schema_version: Literal["1"] = "1"
    status: Literal["APPLIED", "FALLBACK", "SKIPPED_EMPTY", "FAILED"]
    model_name: str = MODEL_NAME
    model_revision: str = MODEL_REVISION
    config: RerankConfig
    requested_candidates: int
    candidates: tuple[CandidateScore, ...] = ()
    diagnostics: PairScores | None = None
    failure_code: str | None = None


class RerankedHybridRetrievalResponse(HybridRetrievalResponse):
    """Consumers MUST use evidence order/rank, not sort retained RRF raw_score."""

    reranking: RerankingMetadata

    @model_validator(mode="after")
    def validate_reranking(self) -> Self:
        meta = self.reranking
        rows = meta.candidates
        if self.status == "FAILED":
            if meta.status != "FAILED":
                raise ValueError("Failed response requires failed reranking")
            return self
        ids = [r.retrieval_chunk_id for r in rows]
        if len(set(ids)) != len(ids) or [r.original_rank for r in rows] != list(range(1, len(rows) + 1)):
            raise ValueError("Invalid original candidate ranking")
        if len(rows) > meta.requested_candidates:
            raise ValueError("Candidate budget exceeded")
        if meta.status == "SKIPPED_EMPTY":
            if rows or self.status != "NO_MATCH":
                raise ValueError("Empty reranking requires NO_MATCH")
            return self
        if meta.status == "APPLIED":
            if any(r.cross_encoder_score is None for r in rows) or meta.diagnostics is None:
                raise ValueError("Applied ranking requires all scores")
            if tuple(r.cross_encoder_score for r in rows) != meta.diagnostics.scores:
                raise ValueError("Scores do not match diagnostics")
            if len(meta.diagnostics.truncated) != len(rows):
                raise ValueError("Truncation count mismatch")
            ordered = sorted(rows, key=lambda r: (-r.cross_encoder_score, r.original_rank, str(r.retrieval_chunk_id)))
        elif meta.status == "FALLBACK":
            if not meta.failure_code or any(r.cross_encoder_score is not None for r in rows):
                raise ValueError("Fallback must not expose partial scores")
            ordered = list(rows)
        else:
            raise ValueError("Invalid successful reranking state")
        selected = ordered[: self.top_k]
        if [r.retrieval_chunk_id for r in selected] != [e.retrieval_chunk_id for e in self.evidence]:
            raise ValueError("Final evidence order differs from reranking")
        ranks = {r.retrieval_chunk_id: i for i, r in enumerate(selected, 1)}
        if any(r.final_rank != ranks.get(r.retrieval_chunk_id) for r in rows):
            raise ValueError("Invalid final rank mapping")
        if any(e.raw_score != rows[ids.index(e.retrieval_chunk_id)].rrf_score for e in self.evidence):
            raise ValueError("Original RRF score changed")
        return self
