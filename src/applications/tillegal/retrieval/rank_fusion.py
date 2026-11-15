"""Pure Reciprocal Rank Fusion over already retrieved, integrity-checked evidence."""

import hashlib
from dataclasses import dataclass

from pydantic import ValidationError

from src.applications.tillegal.retrieval.contracts import RetrievalMode, UnifiedEvidence
from src.applications.tillegal.retrieval.errors import ErrorCategory, RetrievalErrorDetail, RetrievalServiceError
from src.applications.tillegal.retrieval.hybrid_models import FusedRank, RankContribution


@dataclass(frozen=True)
class FusionResult:
    """Final evidence and corresponding original-backend rank/score explanations."""

    evidence: tuple[UnifiedEvidence, ...]
    ranking: tuple[FusedRank, ...]


def _invalid(code: str, message: str) -> RetrievalServiceError:
    """Create a safe integrity failure; no retrieved text is logged or echoed."""
    return RetrievalServiceError(
        RetrievalErrorDetail(
            category=ErrorCategory.INCONSISTENT_EVIDENCE,
            code=code,
            stage="fusion",
            message=message,
        )
    )


def reciprocal_rank_fusion(
    bm25: tuple[UnifiedEvidence, ...],
    dense: tuple[UnifiedEvidence, ...],
    *,
    k: int = 60,
    top_k: int = 10,
) -> FusionResult:
    """Sum 1/(k+rank), deduplicate by chunk UUID, break ties by canonical UUID string.

    Raw scores never affect fusion. Same-ID content/provenance conflicts and
    duplicates within one backend are errors, not extra votes or silent merges.
    """
    if type(k) is not int or k < 1 or type(top_k) is not int or not 1 <= top_k <= 50:
        raise ValueError("RRF requires positive integer k and top_k in 1-50")
    items = {}
    scores = {}
    contributions = {}
    excluded = {"rank", "raw_score", "score_kind", "retrieval_method"}
    for backend, candidates in ((RetrievalMode.BM25, bm25), (RetrievalMode.DENSE, dense)):
        seen = set()
        for rank, original in enumerate(candidates, 1):
            try:
                item = UnifiedEvidence.model_validate(original.model_dump())
            except ValidationError as error:
                raise _invalid("INVALID_FUSION_CANDIDATE", "A fusion candidate violates its contract.") from error
            cid = item.retrieval_chunk_id
            if cid in seen or item.rank != rank or item.retrieval_method != backend:
                raise _invalid("INVALID_BRANCH_RANKING", "Backend ranks, methods or chunk identities are invalid.")
            seen.add(cid)
            if (
                item.hash_check != "MATCHED_STORED"
                or hashlib.sha256(item.content.encode("utf-8")).hexdigest() != item.content_sha256
            ):
                raise _invalid("UNVERIFIED_FUSION_CONTENT", "Fusion requires verified stored chunk content.")
            if cid in items and items[cid].model_dump(exclude=excluded) != item.model_dump(exclude=excluded):
                raise _invalid("CROSS_BACKEND_EVIDENCE_CONFLICT", "The same chunk differs across backend observations.")
            items[cid] = item
            scores[cid] = scores.get(cid, 0.0) + 1 / (k + rank)
            contributions.setdefault(cid, []).append(
                RankContribution(
                    backend=backend.value,
                    rank=rank,
                    raw_score=item.raw_score,
                    score_kind=item.score_kind,
                )
            )
    ordered = sorted(scores, key=lambda cid: (-scores[cid], str(cid)))[:top_k]
    evidence = tuple(
        UnifiedEvidence.model_validate(
            {
                **items[cid].model_dump(),
                "rank": rank,
                "raw_score": scores[cid],
                "score_kind": "RRF",
                "retrieval_method": RetrievalMode.HYBRID,
            }
        )
        for rank, cid in enumerate(ordered, 1)
    )
    return FusionResult(
        evidence=evidence,
        ranking=tuple(FusedRank(retrieval_chunk_id=cid, contributions=tuple(contributions[cid])) for cid in ordered),
    )
