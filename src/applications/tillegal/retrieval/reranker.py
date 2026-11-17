"""Pure selection over verified Hybrid candidates. No model or database SDK."""

import hashlib
import math

from src.applications.tillegal.retrieval.contracts import UnifiedEvidence
from src.applications.tillegal.retrieval.errors import ErrorCategory, RetrievalErrorDetail, RetrievalServiceError


class RerankingOperationalError(RuntimeError):
    """Safe machine code, never underlying model exception text."""


def validate_candidates(candidates: tuple[UnifiedEvidence, ...]) -> None:
    ids = set()
    for rank, candidate in enumerate(candidates, 1):
        item = UnifiedEvidence.model_validate(candidate.model_dump())
        if (
            item.retrieval_chunk_id in ids
            or item.rank != rank
            or item.retrieval_method != "hybrid"
            or item.hash_check != "MATCHED_STORED"
            or hashlib.sha256(item.content.encode("utf-8")).hexdigest() != item.content_sha256
        ):
            raise RetrievalServiceError(
                RetrievalErrorDetail(
                    category=ErrorCategory.INCONSISTENT_EVIDENCE,
                    code="INVALID_RERANK_CANDIDATES",
                    stage="reranking",
                    message="Reranking candidates violate identity or integrity constraints.",
                )
            )
        ids.add(item.retrieval_chunk_id)


def select_candidates(
    candidates: tuple[UnifiedEvidence, ...],
    scores: tuple[float, ...] | None,
    top_k: int,
) -> tuple[UnifiedEvidence, ...]:
    validate_candidates(candidates)
    if type(top_k) is not int or not 1 <= top_k <= 50:
        raise ValueError("Invalid final top-k")
    if scores is not None and (
        len(scores) != len(candidates)
        or any(isinstance(x, bool) or not isinstance(x, (float, int)) or not math.isfinite(x) for x in scores)
    ):
        raise RerankingOperationalError("INVALID_SCORES")
    order = list(range(len(candidates)))
    if scores is not None:
        order.sort(key=lambda i: (-scores[i], candidates[i].rank, str(candidates[i].retrieval_chunk_id)))
    return tuple(
        UnifiedEvidence.model_validate({**candidates[i].model_dump(), "rank": rank})
        for rank, i in enumerate(order[:top_k], 1)
    )
