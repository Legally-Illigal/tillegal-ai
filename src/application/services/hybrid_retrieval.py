"""Sequential orchestration of existing retrieval branches; strict failure policy."""

import asyncio
from collections.abc import Awaitable, Callable

from pydantic import ValidationError

from src.applications.tillegal.retrieval.contracts import (
    IndexIdentity,
    RetrievalMode,
    RetrievalRequest,
    RetrievalResponse,
)
from src.applications.tillegal.retrieval.errors import ErrorCategory, RetrievalErrorDetail, RetrievalServiceError
from src.applications.tillegal.retrieval.hybrid_models import (
    BranchObservation,
    FusionMetadata,
    HybridConfig,
    HybridRetrievalResponse,
)
from src.applications.tillegal.retrieval.ports import IndexReader
from src.applications.tillegal.retrieval.rank_fusion import FusionResult, reciprocal_rank_fusion
from src.core.clock import utc_now
from src.core.identifiers import new_id
from src.integrations.database.repositories.rpc import DatabaseRepositoryError


def _invalid_context() -> RetrievalServiceError:
    """Reject backend responses that belong to a different query/filter/index context."""
    return RetrievalServiceError(
        RetrievalErrorDetail(
            category=ErrorCategory.INCONSISTENT_EVIDENCE,
            code="BRANCH_CONTEXT_MISMATCH",
            stage="validation",
            message="A backend returned a different retrieval context.",
        )
    )


def _validate_context(response: RetrievalResponse, expected: RetrievalRequest, index_name: str) -> None:
    """Require exact request semantics and a READY observation for valid branch outcomes."""
    for field in RetrievalRequest.model_fields:
        if getattr(response, field) != getattr(expected, field):
            raise _invalid_context()
    if response.query_used != expected.query.strip() or response.selected_index_name != index_name:
        raise _invalid_context()
    if response.status != "FAILED" and (
        response.index is None or response.index.status != "READY" or response.index.index_name != index_name
    ):
        raise _invalid_context()


async def _check_closing_index(reader: IndexReader, observed: IndexIdentity) -> None:
    """Extend index observations across the complete Hybrid attempt, without any writes.

    Existing branches already compare complete internal index metadata. This extra
    read detects later identity/version/status/updated_at changes between branches;
    neither check creates a transaction snapshot or an immutable corpus identity.
    """
    row = await reader.get_index(observed.index_name)
    try:
        current = IndexIdentity.model_validate(
            {key: value for key, value in (row or {}).items() if key in IndexIdentity.model_fields}
        )
    except ValidationError as error:
        raise RetrievalServiceError(
            RetrievalErrorDetail(
                category=ErrorCategory.INDEX_UNAVAILABLE,
                code="INDEX_CHANGED_DURING_HYBRID",
                stage="index_postflight",
                message="An index disappeared or changed during Hybrid retrieval.",
            )
        ) from error
    if current != observed:
        raise RetrievalServiceError(
            RetrievalErrorDetail(
                category=ErrorCategory.INDEX_UNAVAILABLE,
                code="INDEX_CHANGED_DURING_HYBRID",
                stage="index_postflight",
                message="An index changed after its branch completed.",
            )
        )


async def search_hybrid(
    request: RetrievalRequest,
    *,
    run_branch: Callable[[RetrievalRequest], Awaitable[RetrievalResponse]],
    sparse_indexes: IndexReader,
    dense_indexes: IndexReader | None,
    sparse_index_name: str,
    dense_index_name: str,
    dense_configured: bool,
    config: HybridConfig,
    timeout_seconds: float,
) -> HybridRetrievalResponse:
    """Reuse full branch pipelines sequentially; errors never become empty votes or fallback."""
    if request.mode != RetrievalMode.HYBRID:
        raise ValueError("Hybrid orchestration requires a hybrid request")
    branches: list[BranchObservation] = []
    responses: list[RetrievalResponse] = []
    fused = FusionResult((), ())
    error: RetrievalErrorDetail | None = None
    stage = "configuration"
    try:
        if not dense_configured or dense_indexes is None:
            raise RetrievalServiceError(
                RetrievalErrorDetail(
                    category=ErrorCategory.CONFIGURATION_ERROR,
                    code="MODE_NOT_CONFIGURED",
                    stage=stage,
                    message="Hybrid requires both existing branches and a local Dense query encoder.",
                )
            )
        async with asyncio.timeout(timeout_seconds):
            for backend, limit, name in (
                (RetrievalMode.BM25, config.bm25_candidates, sparse_index_name),
                (RetrievalMode.DENSE, config.dense_candidates, dense_index_name),
            ):
                stage = backend.value
                branch_request = RetrievalRequest.model_validate(
                    {
                        **request.model_dump(),
                        "mode": backend,
                        "top_k": limit,
                    }
                )
                response = await run_branch(branch_request)
                _validate_context(response, branch_request, name)
                branches.append(
                    BranchObservation(
                        backend=backend.value,
                        status=response.status,
                        requested_candidates=limit,
                        returned_candidates=len(response.evidence),
                        index=response.index,
                        error=response.error,
                    )
                )
                responses.append(response)
                if response.error is not None:
                    raise RetrievalServiceError(
                        response.error.model_copy(
                            update={
                                "stage": f"{backend.value}.{response.error.stage}",
                            }
                        )
                    )
            stage = "index_postflight"
            for reader, response in ((sparse_indexes, responses[0]), (dense_indexes, responses[1])):
                if response.index is None:
                    raise _invalid_context()
                await _check_closing_index(reader, response.index)
            stage = "fusion"
            fused = reciprocal_rank_fusion(
                responses[0].evidence, responses[1].evidence, k=config.rrf_k, top_k=request.top_k
            )
    except RetrievalServiceError as failure:
        error = failure.detail
    except TimeoutError:
        error = RetrievalErrorDetail(
            category=ErrorCategory.TIMEOUT,
            code="HYBRID_TIMEOUT",
            stage=stage,
            message="Hybrid retrieval exceeded its total deadline.",
            retryable=True,
        )
    except DatabaseRepositoryError:
        error = RetrievalErrorDetail(
            category=ErrorCategory.DATABASE_FAILURE,
            code="DATABASE_READ_FAILED",
            stage=stage,
            message="Hybrid closing index verification failed.",
        )
    warnings = []
    if error is None:
        returned_ids = {item.retrieval_chunk_id for item in fused.evidence}
        for response in responses:
            for warning in response.warnings:
                if warning.retrieval_chunk_id is not None and warning.retrieval_chunk_id not in returned_ids:
                    continue
                if warning not in warnings:
                    warnings.append(warning)
    return HybridRetrievalResponse(
        **request.model_dump(),
        request_id=new_id(),
        query_used=request.query.strip(),
        selected_index_name="hybrid",
        index=None,
        status="FAILED" if error else "OK" if fused.evidence else "NO_MATCH",
        evidence=() if error else fused.evidence,
        warnings=tuple(warnings),
        error=error,
        retrieved_at=utc_now(),
        fusion=FusionMetadata(config=config, branches=tuple(branches), ranking=() if error else fused.ranking),
    )
