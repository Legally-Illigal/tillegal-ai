"""Hybrid-only response extension: single-backend JSON payloads stay unchanged."""

import math
from typing import Literal, Self
from uuid import UUID

from pydantic import Field, StrictInt, model_validator

from src.applications.tillegal.retrieval.contracts import ContractModel, IndexIdentity, RetrievalResponse
from src.applications.tillegal.retrieval.errors import RetrievalErrorDetail


class HybridConfig(ContractModel):
    """Fixed candidate budgets per branch, independent of final top-k. No fallback."""

    rrf_k: StrictInt = Field(default=60, ge=1)
    bm25_candidates: StrictInt = Field(default=20, ge=1, le=50)
    dense_candidates: StrictInt = Field(default=20, ge=1, le=50)


class RankContribution(ContractModel):
    """Preserve each backend's original score and one-based position."""

    backend: Literal["bm25", "dense"]
    rank: StrictInt = Field(ge=1)
    raw_score: float
    score_kind: Literal["BM25", "COSINE_SIMILARITY"]

    @model_validator(mode="after")
    def validate_score_kind(self) -> Self:
        """Keep backend score scales distinct in fusion explanations."""
        if self.score_kind != ("BM25" if self.backend == "bm25" else "COSINE_SIMILARITY"):
            raise ValueError("Contribution score kind does not match its backend")
        return self


class FusedRank(ContractModel):
    """Explain the RRF score of one final chunk without replacing source metadata."""

    retrieval_chunk_id: UUID
    contributions: tuple[RankContribution, ...] = Field(min_length=1, max_length=2)

    @model_validator(mode="after")
    def unique_backends(self) -> Self:
        """A backend can vote only once for a canonical chunk."""
        names = [item.backend for item in self.contributions]
        if len(set(names)) != len(names):
            raise ValueError("Duplicate backend contributions")
        return self


class BranchObservation(ContractModel):
    """Record completed backend calls, including an explicit failure if present."""

    backend: Literal["bm25", "dense"]
    status: Literal["OK", "NO_MATCH", "FAILED"]
    requested_candidates: StrictInt = Field(ge=1, le=50)
    returned_candidates: StrictInt = Field(ge=0, le=50)
    index: IndexIdentity | None
    error: RetrievalErrorDetail | None

    @model_validator(mode="after")
    def validate_outcome(self) -> Self:
        """Do not present a backend failure as a successful empty list."""
        if self.returned_candidates > self.requested_candidates:
            raise ValueError("Backend exceeded its candidate budget")
        if self.status == "FAILED":
            if self.error is None or self.returned_candidates:
                raise ValueError("Failed branch must have an error and no candidates")
        elif self.error is not None or (self.status == "OK") != bool(self.returned_candidates):
            raise ValueError("Invalid branch outcome")
        return self


class FusionMetadata(ContractModel):
    """No degraded mode: a failed backend never contributes a partial ranking."""

    algorithm: Literal["RRF"] = "RRF"
    failure_policy: Literal["STRICT"] = "STRICT"
    execution: Literal["SEQUENTIAL"] = "SEQUENTIAL"
    config: HybridConfig
    branches: tuple[BranchObservation, ...] = ()
    ranking: tuple[FusedRank, ...] = ()


class HybridRetrievalResponse(RetrievalResponse):
    """Only Hybrid adds fusion metadata; legacy response models remain usable."""

    fusion: FusionMetadata

    @model_validator(mode="after")
    def validate_fusion(self) -> Self:
        """Ensure successful fused evidence has an explanation from both completed branches."""
        if self.mode != "hybrid" or self.index is not None:
            raise ValueError("Hybrid requires mode=hybrid and per-branch index identities")
        if self.status == "FAILED":
            if self.fusion.ranking:
                raise ValueError("Failed hybrid requests must not expose a partial ranking")
            return self
        if [branch.backend for branch in self.fusion.branches] != ["bm25", "dense"]:
            raise ValueError("Both branches must complete before fusion")
        if any(branch.status == "FAILED" or branch.index is None for branch in self.fusion.branches):
            raise ValueError("Hybrid success requires valid branch observations")
        if [row.retrieval_chunk_id for row in self.fusion.ranking] != [e.retrieval_chunk_id for e in self.evidence]:
            raise ValueError("Fusion explanations must match final evidence order")
        counts = {branch.backend: branch.returned_candidates for branch in self.fusion.branches}
        budgets = {"bm25": self.fusion.config.bm25_candidates, "dense": self.fusion.config.dense_candidates}
        if any(branch.requested_candidates != budgets[branch.backend] for branch in self.fusion.branches):
            raise ValueError("Branch observations differ from configured candidate budgets")
        if self.status == "NO_MATCH" and any(counts.values()):
            raise ValueError("NO_MATCH requires both branches to have no candidates")
        for item, explanation in zip(self.evidence, self.fusion.ranking):
            if any(c.rank > counts[c.backend] for c in explanation.contributions):
                raise ValueError("Contribution rank exceeds backend candidate count")
            score = sum(1 / (self.fusion.config.rrf_k + c.rank) for c in explanation.contributions)
            if not math.isclose(item.raw_score, score, rel_tol=1e-12):
                raise ValueError("Evidence RRF score differs from its explanation")
        return self
