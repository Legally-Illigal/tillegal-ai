"""Optional post-Hybrid stage; operational fallback cannot hide retrieval/integrity errors."""

import asyncio
from collections.abc import Awaitable, Callable

from pydantic import ValidationError

from src.application.services.hybrid_retrieval import _check_closing_index
from src.applications.tillegal.retrieval.contracts import RetrievalRequest, RetrievalWarning
from src.applications.tillegal.retrieval.errors import ErrorCategory, RetrievalErrorDetail, RetrievalServiceError
from src.applications.tillegal.retrieval.hybrid_models import FusionMetadata, HybridConfig, HybridRetrievalResponse
from src.applications.tillegal.retrieval.ports import IndexReader, PairScorer
from src.applications.tillegal.retrieval.reranker import (
    RerankingOperationalError,
    select_candidates,
    validate_candidates,
)
from src.applications.tillegal.retrieval.reranking_models import (
    CandidateScore,
    PairScores,
    RerankConfig,
    RerankedHybridRetrievalResponse,
    RerankingMetadata,
)
from src.core.clock import utc_now
from src.core.identifiers import new_id
from src.integrations.database.repositories.rpc import DatabaseRepositoryError


async def search_reranked(
    request: RetrievalRequest,
    *,
    run_hybrid: Callable[[RetrievalRequest], Awaitable[HybridRetrievalResponse]],
    scorer: PairScorer | None,
    config: RerankConfig,
    sparse_indexes: IndexReader,
    dense_indexes: IndexReader | None,
    hybrid_config: HybridConfig,
) -> RerankedHybridRetrievalResponse:
    pool = max(config.candidate_pool, request.top_k)
    response = None
    payload = None
    try:
        async with asyncio.timeout(config.total_timeout_seconds):
            internal = RetrievalRequest.model_validate({**request.model_dump(), "top_k": pool})
            response = await run_hybrid(internal)
            if response.error:
                raise RetrievalServiceError(response.error)
            candidates = response.evidence
            validate_candidates(candidates)
            diagnostics = None
            code = None
            scores = None
            selected = ()
            if candidates:
                try:
                    if scorer is None:
                        raise RerankingOperationalError("MODEL_NOT_CONFIGURED")
                    async with asyncio.timeout(config.inference_timeout_seconds):
                        diagnostics = PairScores.model_validate(
                            await scorer.score_pairs(
                                request.query.strip(),
                                tuple(c.content for c in candidates),
                            )
                        )
                    if len(diagnostics.truncated) != len(candidates):
                        raise RerankingOperationalError("INVALID_SCORES")
                    selected = select_candidates(candidates, diagnostics.scores, request.top_k)
                    scores = diagnostics.scores
                except (RerankingOperationalError, TimeoutError, ValidationError) as failure:
                    code = (
                        str(failure)
                        if isinstance(failure, RerankingOperationalError)
                        else ("RERANK_TIMEOUT" if isinstance(failure, TimeoutError) else "INVALID_SCORES")
                    )
                    # Only allow known, safe codes into public metadata.
                    allowed = {
                        "MODEL_NOT_CONFIGURED",
                        "MODEL_NOT_PROVISIONED",
                        "MODEL_LOAD_FAILED",
                        "MODEL_INCOMPATIBLE",
                        "MODEL_BUSY",
                        "QUERY_TOO_LONG",
                        "TOKENIZATION_FAILED",
                        "INFERENCE_FAILED",
                        "INVALID_SCORES",
                        "RERANK_TIMEOUT",
                    }
                    code = code if code in allowed else "INFERENCE_FAILED"
                    diagnostics = None
                    selected = select_candidates(candidates, None, request.top_k)
            # Extend existing index observations over model inference, including fallback.
            for branch, reader in zip(response.fusion.branches, (sparse_indexes, dense_indexes)):
                if reader is None or branch.index is None:
                    raise ValueError("Missing successful Hybrid index observation")
                await _check_closing_index(reader, branch.index)
            final_ids = {e.retrieval_chunk_id for e in selected}
            warnings = [
                w for w in response.warnings if w.retrieval_chunk_id is None or w.retrieval_chunk_id in final_ids
            ]
            if code:
                warnings.append(
                    RetrievalWarning(
                        code="RERANKING_FALLBACK", message="Cross-Encoder unavailable; RRF order retained."
                    )
                )
            if diagnostics and any(diagnostics.truncated):
                warnings.append(
                    RetrievalWarning(
                        code="RERANKING_TRUNCATED",
                        message="Some model inputs were truncated; stored evidence is unchanged.",
                    )
                )
            final_ranks = {e.retrieval_chunk_id: e.rank for e in selected}
            ranking = {row.retrieval_chunk_id: row for row in response.fusion.ranking}
            payload = {
                **response.model_dump(),
                **request.model_dump(),
                "evidence": selected,
                "warnings": tuple(warnings),
                "retrieved_at": utc_now(),
                "fusion": {
                    **response.fusion.model_dump(),
                    "ranking": tuple(ranking[e.retrieval_chunk_id] for e in selected),
                },
                "reranking": RerankingMetadata(
                    status="SKIPPED_EMPTY" if not candidates else "FALLBACK" if code else "APPLIED",
                    config=config,
                    requested_candidates=pool,
                    diagnostics=diagnostics,
                    failure_code=code,
                    candidates=tuple(
                        CandidateScore(
                            retrieval_chunk_id=c.retrieval_chunk_id,
                            original_rank=c.rank,
                            rrf_score=c.raw_score,
                            cross_encoder_score=scores[i] if scores is not None else None,
                            final_rank=final_ranks.get(c.retrieval_chunk_id),
                        )
                        for i, c in enumerate(candidates)
                    ),
                ),
            }
    except (RetrievalServiceError, DatabaseRepositoryError, TimeoutError, ValidationError) as failure:
        detail = (
            failure.detail
            if isinstance(failure, RetrievalServiceError)
            else RetrievalErrorDetail(
                category=ErrorCategory.TIMEOUT
                if isinstance(failure, TimeoutError)
                else (
                    ErrorCategory.DATABASE_FAILURE
                    if isinstance(failure, DatabaseRepositoryError)
                    else ErrorCategory.INCONSISTENT_EVIDENCE
                ),
                code="RERANK_PIPELINE_TIMEOUT" if isinstance(failure, TimeoutError) else "RERANK_VERIFICATION_FAILED",
                stage="reranking",
                message="Reranked retrieval could not complete its consistency checks.",
                retryable=isinstance(failure, TimeoutError),
            )
        )
        payload = {
            **request.model_dump(),
            "request_id": response.request_id if response else new_id(),
            "query_used": request.query.strip(),
            "selected_index_name": "hybrid",
            "index": None,
            "status": "FAILED",
            "error": detail,
            "retrieved_at": utc_now(),
            "fusion": FusionMetadata(config=hybrid_config, branches=response.fusion.branches if response else ()),
            "reranking": RerankingMetadata(
                status="FAILED", config=config, requested_candidates=pool, failure_code=detail.code
            ),
        }
    return RerankedHybridRetrievalResponse.model_validate(payload)
