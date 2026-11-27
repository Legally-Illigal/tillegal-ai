"""Opt-in foundation tests; no hosted provider, database, or persistent registry."""

import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from src.applications.tillegal.agents.contract_v2 import (
    CitationTarget,
    ClaimReference,
    ClarificationAnswer,
    IdentityRegistry,
    QueryContextV2,
    QueryEntry,
    QueryEnvelopeV2,
    SearchEnvelopeV2,
)
from src.applications.tillegal.agents.pipeline_v2 import (
    V2CapabilityUnavailableError,
    envelope_from_plan,
    evidence_view,
    plan_query_v2,
    run_query_search_v2,
    search_v2,
)
from src.applications.tillegal.agents.query.agent import understand
from src.applications.tillegal.agents.search.agent import search
from src.applications.tillegal.retrieval.reranking_models import RerankedHybridRetrievalResponse
from src.core.config import SupabaseSettings
from src.query_search_bootstrap import QuerySearch, create_query_search
from tests.unit.applications.tillegal.retrieval.test_hybrid_service import hybrid_service
from tests.unit.applications.tillegal.retrieval.test_reranking import configured
from tests.unit.applications.tillegal.retrieval.test_service import hydrated_service
from tests.unit.applications.tillegal.test_gemini_query import FAKE_KEY, TARGET, reply
from tests.unit.applications.tillegal.test_query_search import options
from tests.unit.applications.tillegal.test_query_search_multimode import options as mode_options
from tests.unit.applications.tillegal.test_query_search_semantic import QUESTION


def registry(opts=None, **kwargs):
    return IdentityRegistry(QueryContextV2(request_id="req-fixture", options=opts or options(), **kwargs))


def pipeline():
    service, *_ = hydrated_service()
    return QuerySearch(service, options())


def test_gemini_factory_payload_and_v1_state_parity(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", FAKE_KEY)
    service, *_ = hydrated_service()
    with (
        patch("src.query_search_bootstrap.create_retrieval_service", return_value=service),
        patch(TARGET, AsyncMock(return_value=reply())) as provider,
    ):
        runner = create_query_search(SupabaseSettings(), options(), semantic_mode="gemini")
        v1 = asyncio.run(runner.search(QUESTION))
        first = provider.call_args
        assert provider.await_count == 1
        provider.reset_mock()
        v2 = asyncio.run(run_query_search_v2(runner, QUESTION, registry()))
        assert provider.await_count == 1 and provider.call_args == first
    assert v2.query.legacy_plan.model_dump() == v1["plan"]
    # Runtime IDs/timestamps are not deterministic across separate native service invocations.
    assert set(v2.legacy_state) == set(v1)
    assert v2.legacy_state["requests"] == v1["requests"]
    assert [g.evidence.model_dump() for g in v2.legacy_state["evidence"]] == [
        g.evidence.model_dump() for g in v1["evidence"]
    ]
    assert not v2.query.claims and not v2.query.citations


def test_deterministic_parity_and_original_dates_stay_separate():
    runner = pipeline()
    q = "Tôi ký năm 2010, cần tìm quy định khi đó?"
    v1 = asyncio.run(runner.search(q))
    v2 = asyncio.run(run_query_search_v2(runner, q, registry()))
    assert v2.query.legacy_plan.model_dump() == v1["plan"]
    assert "as_of_date" not in v1["plan"]
    assert v2.query.context.options.as_of_date == options().as_of_date
    assert v2.legacy_state["requests"] == v1["requests"]


@pytest.mark.parametrize(
    "changes",
    [
        {"as_of_date": "2020-01-01"},
        {"allowed_usage_policies": ["OTHER"]},
        {"top_k": 2},
        {"mode": "dense"},
    ],
)
def test_trusted_options_mismatch_before_model_or_retrieval(changes):
    runner = QuerySearch(AsyncMock(), options(), AsyncMock())
    opts = type(options()).model_validate({**options().model_dump(), **changes})
    reg = registry(opts)
    with pytest.raises(ValueError, match="OPTIONS_MISMATCH"):
        asyncio.run(plan_query_v2(runner, QUESTION, reg))
    runner.query_agent.understand.assert_not_called()
    query = envelope_from_plan(understand(QUESTION), reg)
    with pytest.raises(ValueError, match="OPTIONS_MISMATCH"):
        asyncio.run(search_v2(runner, query, reg))
    runner.retrieval.search.assert_not_called()


def test_context_frozen_and_invalid_request_answers_rejected():
    with pytest.raises(ValidationError):
        QueryContextV2(request_id=" ", options=options())
    with pytest.raises(ValidationError):
        registry().context.revision = "2"
    with pytest.raises(ValidationError):
        QueryContextV2(
            request_id="r",
            options=options(),
            clarification_answers=(ClarificationAnswer(answer_id="original", text="text"),),
        )


def test_ids_stable_scoped_reorder_and_original_immutable():
    reg = registry()
    plan = understand("Điều kiện hợp đồng?")
    plan.update(
        issues=["A", "B"],
        subqueries=[{"text": "query A", "purpose": "topic"}, {"text": "query B", "purpose": "topic"}],
        search_objectives=[{"query_index": 0, "issue_indices": [0]}, {"query_index": 1, "issue_indices": [1]}],
    )
    first = envelope_from_plan(plan, reg)
    assert first == envelope_from_plan(plan, reg)
    plan.update(issues=["B", "A"], subqueries=list(reversed(plan["subqueries"])))
    second = envelope_from_plan(plan, reg)
    assert first.issues[0].issue_id == second.issues[1].issue_id
    assert first.queries[0].query_id == second.queries[1].query_id
    assert registry().scope_id != reg.scope_id
    with pytest.raises(ValueError, match="ORIGINAL_IMMUTABLE"):
        envelope_from_plan(understand("Một câu hỏi khác?"), reg)


def controlled(mode="qa"):
    reg = registry(workflow_mode=mode)
    plan = understand("Tôi hỏi Điều 35 có đúng không?")
    base = envelope_from_plan(plan, reg)
    text = plan["original"]
    start = text.index("Điều 35")
    citation = CitationTarget(
        citation_id=reg.issue("R", "literal"),
        raw_text="Điều 35",
        start=start,
        end=start + 7,
        unresolved_fields=("document_ref", "version"),
    )
    claim = ClaimReference(
        claim_id=reg.issue("C", "original statement"),
        text=text,
        start=0,
        end=len(text),
        citation_ids=(citation.citation_id,),
    )
    support = QueryEntry(
        query_id=reg.issue("Q", "support-target"), subquery_index=0, purpose="find_support", claim_ids=(claim.claim_id,)
    )
    exact = QueryEntry(
        query_id=reg.issue("Q", "citation-target"),
        subquery_index=0,
        purpose="resolve_citation",
        claim_ids=(claim.claim_id,),
        citation_ids=(citation.citation_id,),
    )
    result = QueryEnvelopeV2(
        **{**base.model_dump(), "claims": (claim,), "citations": (citation,), "queries": (support, exact)}
    )
    return reg, result


def test_multiple_purposes_support_never_replaces_original_ambiguous_citation():
    reg, query = controlled()
    before = query.citations[0].model_dump()
    result = asyncio.run(search_v2(pipeline(), query, reg))
    assert result.evidence_links and all(link.purpose == "support_suggestion" for link in result.evidence_links)
    assert all(
        link.resolution_status == "unresolved" and link.legal_validity == "unknown" for link in result.evidence_links
    )
    assert all(link.query_id != query.queries[1].query_id for link in result.evidence_links)
    assert result.query_outcomes[1].reason == "EXACT_RESOLVER_UNAVAILABLE"
    assert query.citations[0].model_dump() == before


def test_verify_contract_has_no_executable_verify_or_extraction():
    reg, query = controlled("verify")
    runner = QuerySearch(AsyncMock(), options(), AsyncMock())
    result = asyncio.run(search_v2(runner, query, reg))
    assert result.status == "unavailable" and result.legacy_state is None
    runner.retrieval.search.assert_not_called()
    with pytest.raises(V2CapabilityUnavailableError, match="VERIFY_EXTRACTION_UNAVAILABLE"):
        asyncio.run(plan_query_v2(runner, QUESTION, reg))
    runner.query_agent.understand.assert_not_called()


def test_resolve_only_never_calls_bm25_as_exact():
    reg, query = controlled()
    query = QueryEnvelopeV2(**{**query.model_dump(), "queries": (query.queries[1],)})
    runner = QuerySearch(AsyncMock(), options())
    result = asyncio.run(search_v2(runner, query, reg))
    assert result.status == "unavailable" and result.query_outcomes[0].reason == "EXACT_RESOLVER_UNAVAILABLE"
    runner.retrieval.search.assert_not_called()


def test_clarification_has_its_own_source_and_no_qa_prompt_change():
    reg = registry(clarification_answers=(ClarificationAnswer(answer_id="a1", text="Tôi đã ký"),))
    runner = QuerySearch(AsyncMock(), options(), AsyncMock())
    with pytest.raises(V2CapabilityUnavailableError, match="CLARIFICATION_PLANNING_UNAVAILABLE"):
        asyncio.run(plan_query_v2(runner, QUESTION, reg))
    runner.query_agent.understand.assert_not_called()
    base = envelope_from_plan(understand("Câu hỏi gốc?"), reg)
    claim = ClaimReference(claim_id=reg.issue("C", "answer"), text="Tôi đã ký", source_id="a1", start=0, end=9)
    valid = QueryEnvelopeV2(**{**base.model_dump(), "claims": (claim,)})
    assert valid.legacy_plan.original == "Câu hỏi gốc?"


@pytest.mark.parametrize("kind", ["cross_request", "dangling", "bad_index", "bad_span", "unissued"])
def test_invalid_references_rejected_without_io(kind):
    reg, query = controlled()
    data = query.model_dump()
    if kind == "cross_request":
        data["queries"][0]["query_id"] = registry().issue("Q", "foreign")
    elif kind == "dangling":
        data["queries"][0]["claim_ids"] = (reg.issue("C", "not included"),)
    elif kind == "bad_index":
        data["queries"][0]["subquery_index"] = 99
    elif kind == "bad_span":
        data["claims"][0]["end"] = 99999
    else:
        data["queries"][0]["query_id"] = reg.scope_id + ":Q:" + "0" * 32
    runner = QuerySearch(AsyncMock(), options())
    with pytest.raises(ValueError):
        asyncio.run(search_v2(runner, QueryEnvelopeV2.model_validate(data), reg))
    runner.retrieval.search.assert_not_called()


def test_claim_without_citation_and_duplicate_target_validation():
    reg, q = controlled()
    data = q.model_dump()
    data["claims"][0]["citation_ids"] = ()
    assert QueryEnvelopeV2.model_validate(data).claims[0].citation_ids == ()
    data["queries"][0]["claim_ids"] *= 2
    with pytest.raises(ValidationError):
        QueryEnvelopeV2.model_validate(data)


def test_duplicate_queries_cache_once_keep_all_occurrences():
    runner = pipeline()
    native = asyncio.run(runner.search("Trích dẫn: thuế"))["responses"][0]
    retrieval = AsyncMock(return_value=native)
    backend = AsyncMock()
    backend.search = retrieval
    plan = understand("Trích dẫn: thuế")
    plan["subqueries"] *= 2
    reg = registry()
    envelope = envelope_from_plan(plan, reg)
    result = asyncio.run(search_v2(QuerySearch(backend, options()), envelope, reg))
    assert retrieval.await_count == 1 and result.legacy_state["executed_searches"] == 1
    assert {link.query_id for link in result.evidence_links} == {q.query_id for q in envelope.queries}


@pytest.mark.parametrize("mode", ["bm25", "dense", "hybrid", "rerank"])
def test_json_roundtrip_native_subtype_and_same_evidence_ids(mode):
    opts = mode_options(mode)
    service = configured()[0] if mode == "rerank" else hybrid_service()[0]
    runner = QuerySearch(service, opts)
    reg = registry(opts)
    query = asyncio.run(plan_query_v2(runner, "Trích dẫn: thuế", reg))
    result = asyncio.run(search_v2(runner, query, reg))
    restored = SearchEnvelopeV2.model_validate_json(result.to_json())
    assert type(restored.legacy_state["responses"][0]) is type(result.legacy_state["responses"][0])
    assert restored.model_dump(serialize_as_any=True) == result.model_dump(serialize_as_any=True)
    again = evidence_view(query, result.legacy_state, reg)
    assert again.evidence_links == result.evidence_links
    if mode == "rerank":
        assert isinstance(restored.legacy_state["responses"][0], RerankedHybridRetrievalResponse)


def test_multiple_issues_one_query_and_version_conflicts_partial_skips():
    runner = pipeline()
    native = asyncio.run(runner.search("Trích dẫn: thuế"))["responses"][0]
    plan = understand("thuế; nghỉ phép; đăng ký đất")
    plan.update(issues=["A", "B"], search_objectives=[{"query_index": 0, "issue_indices": [0, 1]}])
    reg = registry()
    query = envelope_from_plan(plan, reg)
    changed = native.model_copy(
        update={
            "evidence": (
                native.evidence[0].model_copy(update={"source_snapshot_id": "new-version"}),
                *native.evidence[1:],
            )
        }
    )
    backend = AsyncMock()
    backend.search.side_effect = [native, changed, native]
    state = asyncio.run(search(plan, backend, options()))
    result = evidence_view(query, state, reg)
    assert len({link.evidence_id for link in result.evidence_links}) == len(state["evidence"])
    assert len(result.evidence_links[0].issue_ids) == 2
    assert "EVIDENCE_IDENTITY_CONFLICT" in state["warnings"]
    backend.search.side_effect = [native, TimeoutError()]
    partial = asyncio.run(search_v2(QuerySearch(backend, options()), query, reg))
    assert partial.legacy_state["completeness"] == "PARTIAL"
    assert partial.legacy_state["skipped_subqueries"] == (2,)
    assert partial.query_outcomes[1].status == "failed" and partial.query_outcomes[2].status == "skipped"
    assert partial.evidence_links


def test_ids_cannot_be_reassigned_and_nested_plan_mutation_revalidated():
    reg, query = controlled()
    reg.validate(query)
    data = query.model_dump()
    data["queries"][0]["claim_ids"] = ()
    with pytest.raises(ValueError, match="CONTENT_IMMUTABLE"):
        reg.validate(QueryEnvelopeV2.model_validate(data))
    query.legacy_plan.issues.append("unmapped")
    with pytest.raises(ValidationError):
        asyncio.run(search_v2(pipeline(), query, reg))


@pytest.mark.parametrize("field", ["links", "status", "outcome", "context"])
def test_serialized_evidence_view_rejects_lost_links_or_context(field):
    result = asyncio.run(run_query_search_v2(pipeline(), "Trích dẫn: thuế", registry()))
    data = json.loads(result.to_json())
    if field == "links":
        data["evidence_links"] = []
    elif field == "status":
        data["status"] = "failed"
    elif field == "outcome":
        data["query_outcomes"][0]["status"] = "unavailable"
    else:
        data["legacy_state"]["responses"][0]["as_of_date"] = "2000-01-01"
    with pytest.raises(ValidationError):
        SearchEnvelopeV2.model_validate(data)


def test_failed_provider_still_reserves_original_request():
    runner = QuerySearch(AsyncMock(), options(), AsyncMock())
    runner.query_agent.understand.side_effect = RuntimeError("fixture")
    reg = registry()
    with pytest.raises(RuntimeError):
        asyncio.run(plan_query_v2(runner, QUESTION, reg))
    with pytest.raises(ValueError, match="ORIGINAL_IMMUTABLE"):
        asyncio.run(plan_query_v2(runner, "Một câu hỏi khác?", reg))
    assert runner.query_agent.understand.await_count == 1


def test_valid_but_unknown_legacy_issue_associations_stay_empty_and_new_revision_isolated():
    reg = registry()
    plan = understand("Điều kiện hợp đồng dân sự?")
    query = envelope_from_plan(plan, reg)
    assert not query.issues and not query.queries[0].issue_ids
    next_revision = registry(revision="2")
    with pytest.raises(ValueError, match="CONTEXT_MISMATCH"):
        next_revision.validate(query)


def test_one_query_keeps_multiple_claim_targets_without_inventing_facts():
    reg, query = controlled()
    text = query.legacy_plan.original
    start = text.index("có đúng")
    second = ClaimReference(
        claim_id=reg.issue("C", "second controlled span"), text=text[start:-1], start=start, end=len(text) - 1
    )
    entry = QueryEntry(
        query_id=reg.issue("Q", "both targets"),
        subquery_index=0,
        purpose="find_support",
        claim_ids=(query.claims[0].claim_id, second.claim_id),
    )
    query = QueryEnvelopeV2(**{**query.model_dump(), "claims": (*query.claims, second), "queries": (entry,)})
    result = asyncio.run(search_v2(pipeline(), query, reg))
    assert result.evidence_links and all(len(link.claim_ids) == 2 for link in result.evidence_links)
    assert result.query.legacy_plan.facts == query.legacy_plan.facts


@pytest.mark.parametrize(
    "question, expected", [("Điều kiện hợp đồng dân sự?", "no_match"), ("Có được không?", "skipped")]
)
def test_no_match_and_clarification_are_not_fabricated_support(question, expected):
    from tests.unit.applications.tillegal.retrieval.test_service import service

    result = asyncio.run(run_query_search_v2(QuerySearch(service(), options()), question, registry()))
    assert not result.evidence_links and result.query_outcomes[0].status == expected
    assert result.legacy_state["completeness"] == ("COMPLETE" if expected == "no_match" else "NOT_STARTED")


@pytest.mark.parametrize("outcome", ["success", "no_match", "failed", "timeout"])
def test_exact_full_v1_state_parity_with_controlled_native_results(outcome):
    from src.applications.tillegal.retrieval.errors import RetrievalErrorDetail

    native = asyncio.run(pipeline().search("Trích dẫn: thuế"))["responses"][0]
    question = "thuế; đất; bảo hiểm"
    calls = []

    async def retrieve(request):
        calls.append(request)
        current = native.model_copy(update={**request.model_dump(), "query_used": request.query})
        if outcome == "no_match":
            return current.model_copy(update={"status": "NO_MATCH", "evidence": ()})
        if len(calls) == 2 and outcome == "timeout":
            raise TimeoutError()
        if len(calls) == 2 and outcome == "failed":
            return current.model_copy(
                update={
                    "status": "FAILED",
                    "evidence": (),
                    "error": RetrievalErrorDetail(
                        category="DATABASE_FAILURE", code="FIXTURE_FAILED", stage="search", message="Fixture only"
                    ),
                }
            )
        return current

    backend = AsyncMock()
    backend.search.side_effect = retrieve
    runner = QuerySearch(backend, options())
    with (
        patch("src.applications.tillegal.agents.search.agent.uuid4", return_value=native.request_id),
        patch("src.applications.tillegal.agents.search.agent.utc_now", return_value=native.retrieved_at),
    ):
        legacy = asyncio.run(runner.search(question))
        sequence = list(calls)
        calls.clear()
        wrapped = asyncio.run(run_query_search_v2(runner, question, registry()))
    # Exact comparison includes every warning, error, score, occurrence and skipped query.
    assert wrapped.legacy_state == legacy
    assert calls == sequence
    if outcome in {"failed", "timeout"}:
        assert legacy["completeness"] == "PARTIAL" and legacy["skipped_subqueries"] == (2,)


@pytest.mark.parametrize("failure", ["timeout", "provider", "invalid_schema"])
def test_gemini_failure_parity_no_fallback_or_retrieval(monkeypatch, failure):
    from src.applications.tillegal.agents.query.semantic import QueryAnalysisError

    monkeypatch.setenv("GOOGLE_API_KEY", FAKE_KEY)
    provider = AsyncMock(return_value=reply("{}"))
    if failure != "invalid_schema":
        provider.side_effect = TimeoutError() if failure == "timeout" else RuntimeError("fixture provider failure")
    backend = AsyncMock()
    with (
        patch("src.query_search_bootstrap.create_retrieval_service", return_value=backend),
        patch(TARGET, provider),
    ):
        runner = create_query_search(SupabaseSettings(), options(), semantic_mode="gemini")
        with pytest.raises(QueryAnalysisError) as legacy:
            asyncio.run(runner.search(QUESTION))
        arguments = provider.call_args
        assert provider.await_count == 1
        provider.reset_mock()
        with pytest.raises(QueryAnalysisError) as wrapped:
            asyncio.run(run_query_search_v2(runner, QUESTION, registry()))
        assert provider.await_count == 1 and provider.call_args == arguments
    assert type(legacy.value) is type(wrapped.value) and str(legacy.value) == str(wrapped.value)
    backend.search.assert_not_called()


def test_graph_query_remains_deterministic_even_with_semantic_runner():
    from src.applications.tillegal.graphs.legal_qa import QuerySearchNodes

    agent = AsyncMock()
    runner = QuerySearch(AsyncMock(), options(), agent)
    state = QuerySearchNodes(runner).query({"question": QUESTION})
    assert state["plan"] == understand(QUESTION)
    agent.understand.assert_not_called()


def test_quote_lookup_is_conservative_support_not_exact_resolution():
    result = asyncio.run(run_query_search_v2(pipeline(), "Trích dẫn: thuế", registry()))
    assert result.query.legacy_plan.intent == "quote_lookup"
    assert result.query.legacy_plan.subqueries[0].purpose == "lookup"
    assert result.query.queries[0].purpose == "find_support"
    assert not result.query.citations
    assert result.evidence_links and all(link.resolution_status == "unresolved" for link in result.evidence_links)
