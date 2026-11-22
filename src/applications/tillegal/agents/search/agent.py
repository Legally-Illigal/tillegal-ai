"""Execute a QueryPlan against the application RetrievalService."""

from datetime import date
from typing import Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, field_validator

from src.application.services.retrieval_service import RetrievalService
from src.applications.tillegal.agents.query.agent import QueryPlan
from src.applications.tillegal.retrieval.contracts import RetrievalMode, RetrievalRequest, RetrievalResponse


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


async def search(plan: dict, retrieval: RetrievalService, options: SearchOptions) -> SearchState:
    """Keep native responses intact; stop on a classified retrieval failure."""
    parsed = QueryPlan.model_validate(plan)
    options = SearchOptions.model_validate(options)
    if parsed.clarification:
        return {"plan": plan, "requests": (), "responses": (), "status": "CLARIFICATION_REQUIRED"}
    requests = tuple(RetrievalRequest(query=subquery.text, **options.model_dump()) for subquery in parsed.subqueries)
    responses = []
    for request in requests:
        response = await retrieval.search(request)
        responses.append(response)
        if response.status == "FAILED":
            return {
                "plan": plan,
                "requests": requests[: len(responses)],
                "responses": tuple(responses),
                "status": "FAILED",
            }
    return {"plan": plan, "requests": requests, "responses": tuple(responses), "status": "COMPLETED"}
