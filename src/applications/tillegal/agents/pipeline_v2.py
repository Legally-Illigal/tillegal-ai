"""Explicit opt-in adapters over the unchanged V1 planner and Search pipeline."""

from src.applications.tillegal.agents.contract_v2 import (
    EvidenceLink,
    IdentityRegistry,
    IssueReference,
    QueryEntry,
    QueryEnvelopeV2,
    QueryOutcome,
    SearchEnvelopeV2,
)
from src.applications.tillegal.agents.query.agent import QueryPlan, understand
from src.applications.tillegal.agents.search.agent import SearchOptions, SearchState, search
from src.query_search_bootstrap import QuerySearch


class V2CapabilityUnavailableError(RuntimeError):
    pass


def _options(registry: IdentityRegistry, options: SearchOptions):
    if registry.context.options != SearchOptions.model_validate(options):
        raise ValueError("V2_TRUSTED_OPTIONS_MISMATCH")


def envelope_from_plan(plan: dict, registry: IdentityRegistry) -> QueryEnvelopeV2:
    """QA projection only: no fact-to-claim conversion or inferred citation associations."""
    parsed = QueryPlan.model_validate(plan)
    counters: dict[str, int] = {}
    issues = []
    for index, text in enumerate(parsed.issues):
        occurrence = counters.get(text, 0)
        counters[text] = occurrence + 1
        issues.append(IssueReference(issue_id=registry.issue("I", [text, occurrence]), issue_index=index))
    mapping = {i.issue_index: i.issue_id for i in issues}
    links = {x.query_index: tuple(mapping[i] for i in x.issue_indices) for x in parsed.search_objectives}
    queries = []
    counts: dict[str, int] = {}
    for index, subquery in enumerate(parsed.subqueries):
        occurrence = counts.get(subquery.text, 0)
        counts[subquery.text] = occurrence + 1
        targets = links.get(index, ())
        queries.append(
            QueryEntry(
                query_id=registry.issue("Q", [subquery.text, occurrence, targets]),
                subquery_index=index,
                purpose="find_support",
                issue_ids=targets,
            )
        )
    result = QueryEnvelopeV2(
        scope_id=registry.scope_id,
        context=registry.context,
        legacy_plan=parsed,
        issues=tuple(issues),
        queries=tuple(queries),
    )
    registry.validate(result)
    return result


async def plan_query_v2(runner: QuerySearch, question: str, registry: IdentityRegistry) -> QueryEnvelopeV2:
    _options(registry, runner.options)
    if registry.context.workflow_mode != "qa":
        raise V2CapabilityUnavailableError("VERIFY_EXTRACTION_UNAVAILABLE")
    if registry.context.clarification_answers:
        raise V2CapabilityUnavailableError("CLARIFICATION_PLANNING_UNAVAILABLE")
    if registry._original is not None and registry._original != question:
        raise ValueError("V2_ORIGINAL_IMMUTABLE")
    # Reserve immutable request input before awaiting the provider (also on failure).
    understand(question)  # Same deterministic validation, without altering provider payload.
    registry._original = question
    plan = await runner.query_agent.understand(question) if runner.query_agent else understand(question)
    return envelope_from_plan(plan, registry)


def evidence_view(query: QueryEnvelopeV2, state: SearchState, registry: IdentityRegistry) -> SearchEnvelopeV2:
    """View only. No reranking, legal validation or exact resolution is performed."""
    query = QueryEnvelopeV2.model_validate(query.model_dump())
    registry.validate(query)
    if state["plan"] != query.legacy_plan.model_dump():
        raise ValueError("V2_STATE_PLAN_MISMATCH")
    for request in state["requests"]:
        if any(getattr(request, k) != v for k, v in query.context.options.model_dump().items()):
            raise ValueError("V2_STATE_OPTIONS_MISMATCH")
    links = []
    for group_index, group in enumerate(state["evidence"]):
        key = group.evidence.model_dump(mode="json", exclude={"rank", "raw_score", "score_kind", "retrieval_method"})
        evidence_id = registry.issue("E", key)
        for occurrence_index, occurrence in enumerate(group.occurrences):
            for entry in query.queries:
                if entry.subquery_index == occurrence.subquery_index and entry.purpose == "find_support":
                    links.append(
                        EvidenceLink(
                            evidence_id=evidence_id,
                            query_id=entry.query_id,
                            group_index=group_index,
                            occurrence_index=occurrence_index,
                            issue_ids=entry.issue_ids,
                            claim_ids=entry.claim_ids,
                            citation_ids=entry.citation_ids,
                        )
                    )
    outcomes = []
    for entry in query.queries:
        if entry.purpose == "resolve_citation":
            status, reason = "unavailable", "EXACT_RESOLVER_UNAVAILABLE"
        elif entry.subquery_index >= len(state["responses"]):
            status, reason = "skipped", "SUBQUERY_NOT_EXECUTED"
        else:
            status = {"OK": "retrieved", "NO_MATCH": "no_match", "FAILED": "failed"}[
                state["responses"][entry.subquery_index].status
            ]
            reason = None
        outcomes.append(QueryOutcome(query_id=entry.query_id, status=status, reason=reason))
    status = {"COMPLETED": "completed", "FAILED": "failed", "CLARIFICATION_REQUIRED": "clarification_required"}[
        state["status"]
    ]
    return SearchEnvelopeV2(
        query=query, legacy_state=state, status=status, evidence_links=tuple(links), query_outcomes=tuple(outcomes)
    )


async def search_v2(runner: QuerySearch, query: QueryEnvelopeV2, registry: IdentityRegistry) -> SearchEnvelopeV2:
    query = QueryEnvelopeV2.model_validate(query.model_dump())  # Recheck nested mutable V1 payloads.
    registry.validate(query)
    _options(registry, runner.options)
    support = {q.subquery_index for q in query.queries if q.purpose == "find_support"}
    reason = None
    if query.context.workflow_mode == "verify":
        reason = "VERIFY_RUNTIME_UNAVAILABLE"
    elif query.context.clarification_answers:
        reason = "CLARIFICATION_PLANNING_UNAVAILABLE"
    elif any(i not in support for i in range(len(query.legacy_plan.subqueries))):
        reason = "EXACT_RESOLVER_UNAVAILABLE"
    if reason:
        return SearchEnvelopeV2(
            query=query,
            legacy_state=None,
            status="unavailable",
            query_outcomes=tuple(
                QueryOutcome(
                    query_id=q.query_id,
                    status="unavailable",
                    reason="EXACT_RESOLVER_UNAVAILABLE" if q.purpose == "resolve_citation" else reason,
                )
                for q in query.queries
            ),
        )
    state = await search(query.legacy_plan.model_dump(), runner.retrieval, runner.options)
    return evidence_view(query, state, registry)


async def run_query_search_v2(runner: QuerySearch, question: str, registry: IdentityRegistry) -> SearchEnvelopeV2:
    return await search_v2(runner, await plan_query_v2(runner, question, registry), registry)
