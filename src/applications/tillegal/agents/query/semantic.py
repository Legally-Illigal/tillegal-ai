"""One bounded, injectable semantic model call; no silent deterministic fallback."""

import asyncio
import json
import re
import unicodedata
from dataclasses import dataclass
from typing import Protocol

from pydantic import ValidationError

from src.applications.tillegal.agents.query.agent import QueryPlan, Subquery, understand
from src.applications.tillegal.agents.query.context import (
    classify_model_time,
    parse_context,
    reconcile_missing,
    supplied_context,
)
from src.applications.tillegal.agents.query.prompts import SYSTEM_PROMPT
from src.applications.tillegal.agents.query.schemas import SemanticAnalysis


# An application adapter implements this boundary using its configured provider.
# Existing shared gateway/provider modules are placeholders and remain untouched.
class StructuredCompletion(Protocol):
    async def __call__(self, *, model: str, system: str, user: str, schema: dict) -> str:
        """Return a single JSON object string from the application's model gateway."""
        ...


_CITATION = re.compile(r"(?:điều|khoản)\s+\d+[\w.-]*|điểm\s+[a-zđ]\b|\b\d+/(?:19|20)\d{2}/[\wĐđ-]+", re.I)


class QueryAnalysisError(RuntimeError):
    """Content-free code suitable for the caller; never provider response text."""


@dataclass(frozen=True)
class SemanticQueryAgent:
    complete: StructuredCompletion
    model: str
    timeout_seconds: float = 15

    def __post_init__(self) -> None:
        if not self.model.strip() or not 0 < self.timeout_seconds < float("inf"):
            raise ValueError("Explicit model and finite positive timeout required")

    async def understand(self, question: str) -> dict:
        base = understand(question)  # deterministic input/date validation always runs
        if base["clarification"] or base["intent"] == "quote_lookup":
            return base
        text = unicodedata.normalize("NFC", question).strip()
        references, temporal = parse_context(text)
        # Exact lookup has already returned above. Constrain the provider to the
        # only intent this semantic call can accept, rather than asking it to guess.
        schema = SemanticAnalysis.model_json_schema()
        schema["properties"]["intent"] = {"type": "string", "enum": ["legal_question"]}
        try:
            async with asyncio.timeout(self.timeout_seconds):
                raw = await self.complete(
                    model=self.model,
                    system=SYSTEM_PROMPT,
                    user=json.dumps(
                        {
                            "question": text,
                            "user_supplied_slots": supplied_context(text),
                            "reference_spans": [item.model_dump(mode="json") for item in references],
                            "temporal_candidates": [item.model_dump(mode="json") for item in temporal],
                        },
                        ensure_ascii=False,
                    ),
                    schema=schema,
                )
        except TimeoutError:
            raise QueryAnalysisError("QUERY_ANALYSIS_TIMEOUT") from None
        except Exception:
            raise QueryAnalysisError("QUERY_ANALYSIS_PROVIDER_ERROR") from None
        try:
            if not isinstance(raw, str) or len(raw) > 32000:
                raise ValueError("Response size/type")
            analysis = SemanticAnalysis.model_validate_json(raw)
            if any(fact.source_quote not in text for fact in analysis.facts):
                raise ValueError("Unsupported fact")
            model_times = []
            planning_warnings = []
            for mention in analysis.temporal_mentions:
                role = classify_model_time(mention, text, references, temporal)
                if role == "reference":
                    planning_warnings.append("MODEL_REFERENCE_RECLASSIFIED")
                elif role == "negated_time":
                    planning_warnings.append("NEGATED_TEMPORAL_REFERENCE_IGNORED")
                else:
                    model_times.append(mention)
            if analysis.intent != "legal_question":
                raise ValueError("Model cannot promote an ordinary question to exact lookup")
            generated = " ".join(
                [item.issue + " " + item.search_query for item in analysis.issues]
                + analysis.missing_information
                + ([analysis.clarification] if analysis.clarification else [])
            )
            # Reject citation-like references not literally supplied by the user.
            # This is a conservative guard, not proof of semantic correctness.
            if any(m.group().casefold() not in text.casefold() for m in _CITATION.finditer(generated)):
                raise ValueError("Unsupported citation")
            if set(re.findall(r"\d+", generated)) - set(re.findall(r"\d+", text)):
                raise ValueError("Unsupported numeric fact or provision")
            queries = list(dict.fromkeys(item.search_query.strip() for item in analysis.issues))
            links = [
                {
                    "query_index": index,
                    "issue_indices": [
                        issue_index
                        for issue_index, item in enumerate(analysis.issues)
                        if item.search_query.strip() == query
                    ],
                }
                for index, query in enumerate(queries)
            ]
            # Shared context is copied only from verified source spans. Alleged
            # legal provisions/questions are not promoted to scenario facts.
            context = []
            for fact in analysis.facts:
                if not re.search(r"có phải|đúng không|\?", fact.text, re.I) and not parse_context(fact.text)[0]:
                    if fact.text not in context and sum(map(len, context)) + len(fact.text) <= 600:
                        context.append(fact.text)
            for supplied in supplied_context(text).values():
                if not any(supplied in item for item in context):
                    context.append(supplied)
            for index, query in enumerate(queries):
                omitted_context = [item for item in context if item.casefold() not in query.casefold()]
                if omitted_context:
                    queries[index] += "; tình huống người dùng: " + "; ".join(omitted_context)
            missing, consistency_warnings = reconcile_missing(text, analysis.missing_information)
            planning_warnings.extend(consistency_warnings)
            # One objective can safely retain all citation spans supplied in
            # this question. Multiple objectives require semantic association,
            # so never copy every citation into every unrelated search query.
            if len(queries) == 1:
                references = list(dict.fromkeys(match.group() for match in _CITATION.finditer(text)))
                omitted = [reference for reference in references if reference.casefold() not in queries[0].casefold()]
                if omitted:
                    queries[0] += " " + " ".join(omitted)
            if any(not query for query in queries):
                raise ValueError("Blank search objective")
            return QueryPlan(
                **{
                    **base,
                    "domain": analysis.domain,
                    "clarification": analysis.clarification,
                    "subqueries": [Subquery(text=query, purpose="question_part") for query in queries],
                    "analysis_method": "llm",
                    "analysis_model": self.model,
                    "facts": [fact.model_dump() for fact in analysis.facts],
                    "issues": [item.issue for item in analysis.issues],
                    "missing_information": missing,
                    "search_objectives": links,
                    "planning_warnings": list(dict.fromkeys(planning_warnings)),
                    "temporal_scope": list(dict.fromkeys(base["temporal_scope"] + model_times)),
                }
            ).model_dump()
        except (ValidationError, ValueError, TypeError):
            raise QueryAnalysisError("QUERY_ANALYSIS_INVALID_RESPONSE") from None
