"""Strict semantic analysis contract; model claims are never retrieved evidence."""

from datetime import date
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, field_validator, model_validator


class SemanticModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class StatedFact(SemanticModel):
    text: StrictStr = Field(min_length=1, max_length=1000)
    source_quote: StrictStr = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def extractive_only(self) -> Self:
        if self.text != self.source_quote:
            raise ValueError("Facts must be exact source spans, not inferred paraphrases")
        return self


class LegalIssue(SemanticModel):
    issue: StrictStr = Field(
        min_length=1,
        max_length=1000,
        description="One independently searchable information need; related needs may share evidence.",
    )
    search_query: StrictStr = Field(min_length=1, max_length=10000)

    @field_validator("issue", "search_query")
    @classmethod
    def nonblank_objective(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Issue and search objective must not be blank")
        return value


class SemanticAnalysis(SemanticModel):
    intent: Literal["quote_lookup", "legal_question"]
    domain: Literal["labour", "unknown"]
    facts: list[StatedFact] = Field(max_length=12)
    issues: list[LegalIssue] = Field(min_length=1, max_length=4)
    missing_information: list[StrictStr] = Field(max_length=8)
    temporal_mentions: list[StrictStr] = Field(max_length=12)
    clarification: StrictStr | None = Field(max_length=1000)

    @field_validator("missing_information", "temporal_mentions")
    @classmethod
    def nonblank_items(cls, values: list[str]) -> list[str]:
        if any(not value.strip() or len(value) > 1000 for value in values):
            raise ValueError("Items must be bounded and nonblank")
        return values


class LegalReference(SemanticModel):
    kind: Literal["document", "article", "clause", "point", "statute_reference"]
    text: StrictStr
    start: StrictInt = Field(ge=0)
    end: StrictInt = Field(gt=0)
    source: Literal["user_supplied_unverified"] = "user_supplied_unverified"


class TemporalContext(SemanticModel):
    text: StrictStr
    start: StrictInt = Field(ge=0)
    end: StrictInt = Field(gt=0)
    role: Literal[
        "event_date",
        "applicability_date",
        "publication_date",
        "effective_date",
        "historical_reference",
        "relative_reference",
        "duration",
        "current_reference",
        "unspecified",
    ]
    iso_date: StrictStr | None = None

    @field_validator("iso_date")
    @classmethod
    def valid_iso_date(cls, value: str | None) -> str | None:
        if value is not None:
            date.fromisoformat(value)
        return value

    negated: bool = False


class SearchObjective(SemanticModel):
    query_index: StrictInt = Field(ge=0, le=3)
    issue_indices: list[StrictInt] = Field(min_length=1, max_length=4)
