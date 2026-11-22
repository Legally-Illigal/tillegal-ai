"""Typed state and technical retrieval handoff for the Query/Search workflow."""

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.applications.tillegal.agents.query.agent import QueryPlan
from src.applications.tillegal.agents.search.agent import SearchOptions, SearchState
from src.applications.tillegal.retrieval.contracts import RetrievalRequest, RetrievalResponse, RetrievalWarning
from src.applications.tillegal.retrieval.errors import RetrievalErrorDetail
from src.applications.tillegal.retrieval.hybrid_models import HybridRetrievalResponse
from src.applications.tillegal.retrieval.reranking_models import RerankedHybridRetrievalResponse
from src.framework.state.base import WorkflowState

RetrievalOutcome = RerankedHybridRetrievalResponse | HybridRetrievalResponse | RetrievalResponse


class JudgeHandoff(BaseModel):
    """Versioned technical retrieval output; legal sufficiency remains unassessed."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1"] = "1"
    request_id: str | None
    run_id: str = Field(min_length=1)
    question: str = Field(min_length=1, max_length=10000)
    plan: QueryPlan
    options: SearchOptions
    requests: tuple[RetrievalRequest, ...] = Field(min_length=1)
    responses: tuple[RetrievalOutcome, ...] = Field(min_length=1)
    search_status: Literal["COMPLETED", "FAILED"]
    status: Literal["READY", "NO_MATCH", "RETRIEVAL_FAILED"]

    @property
    def warnings(self) -> tuple[RetrievalWarning, ...]:
        """Derive warnings without duplicating or discarding per-query response data."""
        return tuple(warning for response in self.responses for warning in response.warnings)

    @property
    def errors(self) -> tuple[RetrievalErrorDetail, ...]:
        return tuple(response.error for response in self.responses if response.error is not None)

    @model_validator(mode="after")
    def validate_context(self) -> Self:
        if self.question != self.plan.original or self.plan.clarification:
            raise ValueError("Handoff requires the original non-clarifying query context")
        if len(self.requests) != len(self.responses) or len(self.requests) > len(self.plan.subqueries):
            raise ValueError("Handoff request/response counts differ")
        for subquery, request, response in zip(self.plan.subqueries, self.requests, self.responses):
            if request.query != subquery.text:
                raise ValueError("Handoff query differs from its plan")
            if any(getattr(request, key) != value for key, value in self.options.model_dump().items()):
                raise ValueError("Handoff execution options differ")
            if any(getattr(response, key) != getattr(request, key) for key in RetrievalRequest.model_fields):
                raise ValueError("Handoff response context differs")
        failed = self.responses[-1].status == "FAILED"
        if any(response.status == "FAILED" for response in self.responses[:-1]):
            raise ValueError("Search must stop at its first failure")
        expected = "RETRIEVAL_FAILED" if failed else "READY" if any(r.evidence for r in self.responses) else "NO_MATCH"
        if self.status != expected or self.search_status != ("FAILED" if failed else "COMPLETED"):
            raise ValueError("Handoff status differs from retrieval outcomes")
        if not failed and len(self.requests) != len(self.plan.subqueries):
            raise ValueError("Completed handoff requires all subqueries")
        return self

    @classmethod
    def from_search(
        cls,
        *,
        question: str,
        request_id: str | None,
        run_id: str,
        options: SearchOptions,
        result: SearchState,
    ) -> Self:
        status = (
            "RETRIEVAL_FAILED"
            if result["status"] == "FAILED"
            else "READY"
            if any(response.evidence for response in result["responses"])
            else "NO_MATCH"
        )
        return cls(
            question=question,
            request_id=request_id,
            run_id=run_id,
            plan=result["plan"],
            options=options,
            requests=result["requests"],
            responses=result["responses"],
            search_status=result["status"],
            status=status,
        )


class LegalQAState(WorkflowState, total=False):
    request_id: str | None
    question: str
    plan: dict
    options: SearchOptions
    search_result: SearchState | None
    clarification: str | None
    handoff: JudgeHandoff | None
