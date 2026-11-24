"""Execute a QueryPlan against the application RetrievalService."""

import asyncio
import unicodedata
from collections.abc import Sequence
from datetime import date
from typing import Literal, TypedDict
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, field_validator

from src.application.services.retrieval_service import RetrievalService
from src.applications.tillegal.agents.query.agent import QueryPlan
from src.applications.tillegal.agents.query.context import parse_context
from src.applications.tillegal.agents.search.schemas import AggregatedEvidence, EvidenceOccurrence
from src.applications.tillegal.retrieval.contracts import (
    RetrievalMode,
    RetrievalRequest,
    RetrievalResponse,
    UnifiedEvidence,
)
from src.applications.tillegal.retrieval.errors import RetrievalErrorDetail, RetrievalServiceError
from src.core.clock import utc_now


class SearchOptions(BaseModel):
    """Trusted execution context, explicitly supplied by the application."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    mode: RetrievalMode
    top_k: StrictInt = Field(ge=1, le=50)
    as_of_date: date
    allowed_usage_policies: tuple[StrictStr, ...] = Field(min_length=1)

    @field_validator("allowed_usage_policies")
    @classmethod
    def nonblank_policies(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(not value.strip() for value in values):
            raise ValueError("Policies must not be blank")
        return tuple(dict.fromkeys(value.strip() for value in values))


class SearchState(TypedDict):
    plan: dict
    requests: tuple[RetrievalRequest, ...]
    responses: tuple[RetrievalResponse, ...]
    status: Literal["CLARIFICATION_REQUIRED", "COMPLETED", "FAILED"]
    completeness: Literal["NOT_STARTED", "COMPLETE", "PARTIAL", "FAILED"]
    evidence: tuple[AggregatedEvidence, ...]
    warnings: tuple[str, ...]
    errors: tuple[RetrievalErrorDetail, ...]
    skipped_subqueries: tuple[int, ...]
    executed_searches: int


def _finish(
    plan: dict,
    requests: Sequence[RetrievalRequest],
    responses: Sequence[RetrievalResponse],
    *,
    total: int,
    calls: int,
    clarification: bool = False,
) -> SearchState:
    """Group only byte-equivalent source payloads, excluding query-local rank/score."""
    parsed = QueryPlan.model_validate(plan)
    objective_links = {item.query_index: tuple(item.issue_indices) for item in parsed.search_objectives}
    grouped: dict[str, tuple[UnifiedEvidence, list[EvidenceOccurrence]]] = {}
    warnings = [warning.code for response in responses for warning in response.warnings]
    identities: dict[str, set[str]] = {}
    for response_index, response in enumerate(responses):
        if response.status == "NO_MATCH":
            warnings.append(f"NO_MATCH:{response_index}")
        for item in response.evidence:
            # Includes snapshot, effective dates, source metadata and content hash.
            # Conflicting versions/payloads remain separate and get a warning.
            key = item.model_dump_json(exclude={"rank", "raw_score", "score_kind", "retrieval_method"})
            identity = str(item.retrieval_chunk_id)
            if identity in identities and key not in identities[identity]:
                warnings.append("EVIDENCE_IDENTITY_CONFLICT")
            identities.setdefault(identity, set()).add(key)
            if key not in grouped:
                grouped[key] = (item, [])
            grouped[key][1].append(
                EvidenceOccurrence(
                    subquery_index=response_index,
                    response_index=response_index,
                    query=requests[response_index].query,
                    request_id=str(response.request_id),
                    rank=item.rank,
                    raw_score=item.raw_score,
                    score_kind=item.score_kind,
                    issue_indices=objective_links.get(response_index, ()),
                )
            )
    if parsed.intent == "quote_lookup" and grouped:
        # A mention inside chunk text does not establish the source's identity.
        # This is a literal metadata warning, not a legal sufficiency judgment.
        references = parsed.citations or parse_context(unicodedata.normalize("NFC", parsed.original).strip())[0]
        required = [item.text for item in references if item.kind == "document"]
        titles = " ".join(item.title for response in responses for item in response.evidence).casefold()
        if any(reference.casefold() not in titles for reference in required):
            warnings.append("EXACT_LOOKUP_SOURCE_IDENTITY_UNCONFIRMED")
    failed = any(response.status == "FAILED" for response in responses)
    skipped = tuple(range(len(responses), total))
    if failed:
        warnings.append("SEARCH_INCOMPLETE")
    if plan.get("temporal_scope"):
        warnings.append("TEMPORAL_SCOPE_REQUIRES_CALLER_DATE_REVIEW")
    return SearchState(
        plan=plan,
        requests=tuple(requests),
        responses=tuple(responses),
        status="CLARIFICATION_REQUIRED" if clarification else "FAILED" if failed else "COMPLETED",
        completeness="NOT_STARTED"
        if clarification
        else (
            "PARTIAL" if failed and any(r.status != "FAILED" for r in responses) else "FAILED" if failed else "COMPLETE"
        ),
        evidence=tuple(
            AggregatedEvidence(evidence=item, occurrences=tuple(occurrences)) for item, occurrences in grouped.values()
        ),
        warnings=tuple(dict.fromkeys(warnings)),
        errors=tuple(response.error for response in responses if response.error is not None),
        skipped_subqueries=skipped,
        executed_searches=calls,
    )


async def search(
    plan: dict,
    retrieval: RetrievalService,
    options: SearchOptions,
    *,
    timeout_seconds: float = 45,
) -> SearchState:
    """Retain fail-fast handoff compatibility; expose all partial evidence and gaps.

    Classified errors are outcomes. Unexpected programming errors and cancellation
    propagate to the caller. There is no backend fallback or ranking change.
    """
    parsed = QueryPlan.model_validate(plan)
    options = SearchOptions.model_validate(options)
    if not 0 < timeout_seconds < float("inf"):
        raise ValueError("finite positive per-query timeout required")
    if parsed.clarification:
        return _finish(plan, (), (), total=len(parsed.subqueries), calls=0, clarification=True)
    requests: list[RetrievalRequest] = []
    responses: list[RetrievalResponse] = []
    cached: dict[str, RetrievalResponse] = {}
    calls = 0
    for subquery in parsed.subqueries:
        request = RetrievalRequest(query=subquery.text, **options.model_dump())
        requests.append(request)
        # Exact text only: do not change quoted text or case-sensitive lookup intent.
        if request.query in cached:
            response = cached[request.query]
        else:
            calls += 1
            try:
                async with asyncio.timeout(timeout_seconds):
                    response = await retrieval.search(request)
            except (TimeoutError, RetrievalServiceError) as failure:
                detail = (
                    failure.detail
                    if isinstance(failure, RetrievalServiceError)
                    else RetrievalErrorDetail(
                        category="TIMEOUT",
                        code="SEARCH_QUERY_TIMEOUT",
                        stage="search",
                        message="Search query exceeded its deadline.",
                        retryable=True,
                    )
                )
                response = RetrievalResponse(
                    **request.model_dump(),
                    request_id=uuid4(),
                    query_used=request.query.strip(),
                    selected_index_name="unavailable",
                    index=None,
                    status="FAILED",
                    error=detail,
                    retrieved_at=utc_now(),
                )
            cached[request.query] = response
        responses.append(response)
        if response.status == "FAILED":
            break
    return _finish(plan, requests, responses, total=len(parsed.subqueries), calls=calls)
