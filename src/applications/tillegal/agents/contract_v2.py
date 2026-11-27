"""Opt-in workflow metadata. V1 models/provider schemas remain unchanged."""

import hashlib
import json
import re
import unicodedata
from typing import Literal, Self
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, field_validator, model_validator

from src.applications.tillegal.agents.query.agent import QueryPlan
from src.applications.tillegal.agents.search.agent import SearchOptions, SearchState
from src.applications.tillegal.retrieval.contracts import RetrievalResponse
from src.applications.tillegal.retrieval.hybrid_models import HybridRetrievalResponse
from src.applications.tillegal.retrieval.reranking_models import RerankedHybridRetrievalResponse


class V2Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ClarificationAnswer(V2Model):
    answer_id: StrictStr = Field(min_length=1)
    text: StrictStr = Field(min_length=1, max_length=10000)
    source: Literal["user"] = "user"


class QueryContextV2(V2Model):
    request_id: StrictStr = Field(min_length=1)
    revision: StrictStr = Field(default="1", min_length=1)
    workflow_mode: Literal["qa", "verify"] = "qa"
    options: SearchOptions
    jurisdiction: Literal["VN", "unknown"] = "VN"
    clarification_answers: tuple[ClarificationAnswer, ...] = ()

    @model_validator(mode="after")
    def valid_context(self) -> Self:
        if not self.request_id.strip() or not self.revision.strip():
            raise ValueError("V2_CONTEXT_BLANK")
        ids = [a.answer_id for a in self.clarification_answers]
        if len(ids) != len(set(ids)) or "original" in ids:
            raise ValueError("V2_ANSWER_ID_INVALID")
        return self


class IssueReference(V2Model):
    issue_id: StrictStr
    issue_index: StrictInt = Field(ge=0)


class ClaimReference(V2Model):
    claim_id: StrictStr
    text: StrictStr = Field(min_length=1)
    source_id: StrictStr = "original"
    start: StrictInt = Field(ge=0)
    end: StrictInt = Field(gt=0)
    citation_ids: tuple[StrictStr, ...] = ()


class CitationTarget(V2Model):
    citation_id: StrictStr
    raw_text: StrictStr = Field(min_length=1)
    source_id: StrictStr = "original"
    start: StrictInt = Field(ge=0)
    end: StrictInt = Field(gt=0)
    unresolved_fields: tuple[StrictStr, ...] = ()
    resolution_status: Literal["unresolved"] = "unresolved"


class QueryEntry(V2Model):
    query_id: StrictStr
    subquery_index: StrictInt = Field(ge=0)
    purpose: Literal["find_support", "resolve_citation"]
    issue_ids: tuple[StrictStr, ...] = ()
    claim_ids: tuple[StrictStr, ...] = ()
    citation_ids: tuple[StrictStr, ...] = ()

    @model_validator(mode="after")
    def resolution_needs_target(self) -> Self:
        if self.purpose == "resolve_citation" and not self.citation_ids:
            raise ValueError("V2_RESOLUTION_TARGET_REQUIRED")
        return self


def _unique(values):
    if len(values) != len(set(values)):
        raise ValueError("V2_DUPLICATE_REFERENCE")


def check_id(value: str, scope: str, kind: str):
    if not re.fullmatch(re.escape(scope) + ":" + kind + r":[0-9a-f]{32}", value):
        raise ValueError("V2_CROSS_SCOPE_OR_INVALID_ID")


class QueryEnvelopeV2(V2Model):
    contract_version: Literal["2"] = "2"
    scope_id: StrictStr = Field(pattern=r"^[0-9a-f]{32}$")
    context: QueryContextV2
    legacy_plan: QueryPlan
    issues: tuple[IssueReference, ...] = ()
    claims: tuple[ClaimReference, ...] = ()
    citations: tuple[CitationTarget, ...] = ()
    queries: tuple[QueryEntry, ...] = ()

    @model_validator(mode="after")
    def valid_references(self) -> Self:
        groups = [
            (self.issues, "issue_id", "I"),
            (self.claims, "claim_id", "C"),
            (self.citations, "citation_id", "R"),
            (self.queries, "query_id", "Q"),
        ]
        for items, field, kind in groups:
            values = [getattr(item, field) for item in items]
            _unique(values)
            for value in values:
                check_id(value, self.scope_id, kind)
        indices = [i.issue_index for i in self.issues]
        _unique(indices)
        if set(indices) != set(range(len(self.legacy_plan.issues))):
            raise ValueError("V2_ISSUE_MAPPING_INCOMPLETE")
        sources = {
            "original": unicodedata.normalize("NFC", self.legacy_plan.original).strip(),
            **{a.answer_id: a.text for a in self.context.clarification_answers},
        }
        for item in (*self.claims, *self.citations):
            text = item.text if isinstance(item, ClaimReference) else item.raw_text
            source = sources.get(item.source_id)
            if source is None or not 0 <= item.start < item.end <= len(source) or source[item.start : item.end] != text:
                raise ValueError("V2_UNGROUNDED_SOURCE_SPAN")
        known = {
            "issue_ids": {i.issue_id for i in self.issues},
            "claim_ids": {c.claim_id for c in self.claims},
            "citation_ids": {c.citation_id for c in self.citations},
        }
        for claim in self.claims:
            _unique(claim.citation_ids)
            if not set(claim.citation_ids) <= known["citation_ids"]:
                raise ValueError("V2_DANGLING_CITATION")
        for query in self.queries:
            if query.subquery_index >= len(self.legacy_plan.subqueries):
                raise ValueError("V2_INVALID_SUBQUERY_INDEX")
            for field, ids in known.items():
                values = getattr(query, field)
                _unique(values)
                if not set(values) <= ids:
                    raise ValueError("V2_DANGLING_TARGET")
        if {q.subquery_index for q in self.queries} != set(range(len(self.legacy_plan.subqueries))):
            raise ValueError("V2_QUERY_MAPPING_INCOMPLETE")
        return self


class EvidenceLink(V2Model):
    evidence_id: StrictStr
    query_id: StrictStr
    group_index: StrictInt = Field(ge=0)
    occurrence_index: StrictInt = Field(ge=0)
    issue_ids: tuple[StrictStr, ...] = ()
    claim_ids: tuple[StrictStr, ...] = ()
    citation_ids: tuple[StrictStr, ...] = ()
    purpose: Literal["support_suggestion"] = "support_suggestion"
    resolution_status: Literal["unresolved"] = "unresolved"
    legal_validity: Literal["unknown"] = "unknown"
    url_access: Literal["not_attempted"] = "not_attempted"


class QueryOutcome(V2Model):
    query_id: StrictStr
    status: Literal["retrieved", "no_match", "failed", "skipped", "unavailable"]
    reason: StrictStr | None = None


class SearchEnvelopeV2(V2Model):
    contract_version: Literal["2"] = "2"
    query: QueryEnvelopeV2
    legacy_state: SearchState | None
    status: Literal["completed", "failed", "clarification_required", "unavailable"]
    evidence_links: tuple[EvidenceLink, ...] = ()
    query_outcomes: tuple[QueryOutcome, ...]

    @field_validator("legacy_state", mode="before")
    @classmethod
    def restore_subtypes(cls, value):
        if value is None:
            return value
        responses = []
        for raw in value["responses"]:
            if isinstance(raw, RetrievalResponse):
                responses.append(raw)
            else:
                model = (
                    RerankedHybridRetrievalResponse
                    if "reranking" in raw
                    else HybridRetrievalResponse
                    if "fusion" in raw
                    else RetrievalResponse
                )
                responses.append(model.model_validate(raw))
        return {**value, "responses": tuple(responses)}

    @model_validator(mode="after")
    def valid_links(self) -> Self:
        entries = {q.query_id: q for q in self.query.queries}
        outcomes = [q.query_id for q in self.query_outcomes]
        _unique(outcomes)
        if set(outcomes) != set(entries):
            raise ValueError("V2_OUTCOME_MAPPING_INVALID")
        if self.legacy_state is None:
            if (
                self.status != "unavailable"
                or self.evidence_links
                or any(o.status != "unavailable" for o in self.query_outcomes)
            ):
                raise ValueError("V2_UNAVAILABLE_STATE_INVALID")
            return self
        if self.legacy_state["plan"] != self.query.legacy_plan.model_dump():
            raise ValueError("V2_STATE_PLAN_MISMATCH")
        expected_status = {
            "COMPLETED": "completed",
            "FAILED": "failed",
            "CLARIFICATION_REQUIRED": "clarification_required",
        }[self.legacy_state["status"]]
        if self.status != expected_status:
            raise ValueError("V2_STATE_STATUS_MISMATCH")
        if len(self.legacy_state["requests"]) != len(self.legacy_state["responses"]):
            raise ValueError("V2_NATIVE_RESPONSE_COUNT_MISMATCH")
        for native in (*self.legacy_state["requests"], *self.legacy_state["responses"]):
            if any(getattr(native, k) != v for k, v in self.query.context.options.model_dump().items()):
                raise ValueError("V2_STATE_OPTIONS_MISMATCH")
        expected_links = {
            (gi, oi, entry.query_id)
            for gi, group in enumerate(self.legacy_state["evidence"])
            for oi, occurrence in enumerate(group.occurrences)
            for entry in self.query.queries
            if entry.purpose == "find_support" and entry.subquery_index == occurrence.subquery_index
        }
        actual_links = [(link.group_index, link.occurrence_index, link.query_id) for link in self.evidence_links]
        _unique(actual_links)
        if set(actual_links) != expected_links:
            raise ValueError("V2_EVIDENCE_LINKS_INCOMPLETE")
        group_ids = {}
        for link in self.evidence_links:
            check_id(link.evidence_id, self.query.scope_id, "E")
            if link.group_index in group_ids and group_ids[link.group_index] != link.evidence_id:
                raise ValueError("V2_EVIDENCE_ID_INCONSISTENT")
            group_ids[link.group_index] = link.evidence_id
            entry = entries.get(link.query_id)
            if entry is None or entry.purpose != "find_support":
                raise ValueError("V2_INVALID_EVIDENCE_TARGET")
            if any(getattr(entry, f) != getattr(link, f) for f in ["issue_ids", "claim_ids", "citation_ids"]):
                raise ValueError("V2_EVIDENCE_TARGET_MISMATCH")
            groups = self.legacy_state["evidence"]
            if link.group_index >= len(groups) or link.occurrence_index >= len(groups[link.group_index].occurrences):
                raise ValueError("V2_INVALID_OCCURRENCE")
            if groups[link.group_index].occurrences[link.occurrence_index].subquery_index != entry.subquery_index:
                raise ValueError("V2_OCCURRENCE_QUERY_MISMATCH")
        _unique(list(group_ids.values()))
        for outcome in self.query_outcomes:
            entry = entries[outcome.query_id]
            if entry.purpose == "resolve_citation":
                expected = "unavailable"
            elif entry.subquery_index >= len(self.legacy_state["responses"]):
                expected = "skipped"
            else:
                expected = {"OK": "retrieved", "NO_MATCH": "no_match", "FAILED": "failed"}[
                    self.legacy_state["responses"][entry.subquery_index].status
                ]
            if outcome.status != expected:
                raise ValueError("V2_OUTCOME_STATUS_MISMATCH")
        return self

    def to_json(self) -> str:
        return self.model_dump_json(serialize_as_any=True)


class IdentityRegistry:
    """In-memory request/revision registry. IDs are opaque and code-issued, not persistent."""

    def __init__(self, context: QueryContextV2):
        self.context = QueryContextV2.model_validate(context.model_dump())
        self.scope_id = uuid4().hex
        self._ids: dict[tuple[str, str], str] = {}
        self._issued: set[str] = set()
        self._original: str | None = None
        self._bindings: dict[str, str] = {}

    def issue(self, kind: Literal["I", "Q", "C", "R", "E"], key: object) -> str:
        canonical = json.dumps(key, ensure_ascii=False, sort_keys=True, default=str)
        digest = hashlib.sha256(canonical.encode()).hexdigest()
        lookup = (kind, digest)
        if lookup not in self._ids:
            self._ids[lookup] = f"{self.scope_id}:{kind}:{uuid4().hex}"
            self._issued.add(self._ids[lookup])
        return self._ids[lookup]

    def validate(self, envelope: QueryEnvelopeV2):
        if envelope.scope_id != self.scope_id or envelope.context != self.context:
            raise ValueError("V2_REGISTRY_CONTEXT_MISMATCH")
        original = envelope.legacy_plan.original
        if self._original is not None and self._original != original:
            raise ValueError("V2_ORIGINAL_IMMUTABLE")
        for items, field in [
            (envelope.issues, "issue_id"),
            (envelope.claims, "claim_id"),
            (envelope.citations, "citation_id"),
            (envelope.queries, "query_id"),
        ]:
            if any(getattr(item, field) not in self._issued for item in items):
                raise ValueError("V2_ID_NOT_ISSUED")
        pending = {}
        for items, field in [
            (envelope.issues, "issue_id"),
            (envelope.claims, "claim_id"),
            (envelope.citations, "citation_id"),
            (envelope.queries, "query_id"),
        ]:
            for item in items:
                value = item.model_dump(exclude={field})
                if isinstance(item, IssueReference):
                    value = {"text": envelope.legacy_plan.issues[item.issue_index]}
                if isinstance(item, QueryEntry):
                    value.pop("subquery_index")
                    value["text"] = envelope.legacy_plan.subqueries[item.subquery_index].text
                identity = getattr(item, field)
                fingerprint = json.dumps(value, sort_keys=True, ensure_ascii=False)
                if identity in self._bindings and self._bindings[identity] != fingerprint:
                    raise ValueError("V2_ID_CONTENT_IMMUTABLE")
                pending[identity] = fingerprint
        self._bindings.update(pending)
        self._original = original
