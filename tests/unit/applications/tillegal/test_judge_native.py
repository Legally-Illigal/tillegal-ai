"""Native boundary and mock replay tests, no semantic/legal or live validation."""

import asyncio
from copy import deepcopy
from unittest.mock import Mock

import pytest

from src.applications.tillegal.agents.judge.adapter import JudgeAdapterError, adapt_search, evaluate_search
from src.applications.tillegal.agents.judge.agent import FixtureJudgeProvider, JudgeAgent, JudgeLimits
from src.applications.tillegal.agents.judge.schemas import error_result
from src.applications.tillegal.agents.query.agent import understand
from src.applications.tillegal.agents.search.agent import _finish, search
from tests.unit.applications.tillegal.retrieval.test_service import hydrated_service, service
from tests.unit.applications.tillegal.test_query_search import options


def state(empty=False):
    svc = service() if empty else hydrated_service()[0]
    return asyncio.run(
        search(
            understand(
                "Tôi ký hợp đồng lao động 2 năm, mới làm được 6 tháng nhưng muốn nghỉ việc. "
                "Tôi có phải báo trước không và có phải bồi thường không?"
            ),
            svc,
            options(),
        )
    )


def args():
    return dict(
        request_id="request-test",
        options=options(),
        search_rounds_completed=1,
        query_history=["Q1"],
        query_text_history=["previous search"],
    )


def response(a, status="SUFFICIENT"):
    eids = list(a.evidence_map)
    return dict(
        status=status,
        issue_checks=[
            dict(issue_id=i, evidence_ids=eids, coverage="full" if status == "SUFFICIENT" else "partial")
            for i in a.issue_map
        ],
        missing_items=[] if status == "SUFFICIENT" else ["Missing condition"],
        next_queries=[],
        usable_evidence_ids=eids,
        explanation="Fixture only; no legal evaluation.",
        error_code=None,
    )


def test_native_roundtrip_stable_mapping_and_no_mutation():
    s = state()
    before = deepcopy(s)
    a = adapt_search(s, **args())
    b = adapt_search(s, **args())
    assert a == b and s == before
    assert a.judge_input["question"] == s["plan"]["original"]
    assert a.judge_input["as_of_date"] == options().as_of_date.isoformat()
    assert all(v["occurrences"] for v in a.evidence_map.values())
    assert any(len(v["occurrences"]) > 1 for v in a.evidence_map.values())
    assert all(
        e["document_version_id"] is None
        and e["exact_citation_verified"] is None
        and e["quote_representation"] == "retrieval_chunk_content"
        for e in a.judge_input["evidence"]
    )
    result = evaluate_search(s, judge=JudgeAgent(FixtureJudgeProvider(response(a))), **args())
    assert result.judge_result == response(a) and result.adapted == a


@pytest.mark.parametrize("status", ["SUFFICIENT", "INSUFFICIENT", "ERROR"])
def test_statuses(status):
    a = adapt_search(state(), **args())
    r = error_result("FIXTURE_ERROR") if status == "ERROR" else response(a, status)
    assert JudgeAgent(FixtureJudgeProvider(r)).evaluate(a.judge_input) == r


@pytest.mark.parametrize(
    "change,code",
    [
        ({"usable_evidence_ids": ["foreign"]}, "INVALID_OUTPUT_REFERENCE"),
        ({"missing_items": ["gap"]}, "INVALID_OUTPUT_CONSISTENCY"),
        ({"error_code": "bad"}, "INVALID_OUTPUT_CONSISTENCY"),
    ],
)
def test_bad_output(change, code):
    a = adapt_search(state(), **args())
    r = response(a)
    r.update(change)
    assert JudgeAgent(FixtureJudgeProvider(r)).evaluate(a.judge_input)["error_code"] == code


def test_empty_no_model():
    s = state(True)
    a = adapt_search(s, **args())
    provider = Mock()
    r = JudgeAgent(provider).evaluate(a.judge_input)
    assert r["status"] == "INSUFFICIENT" and all(c["coverage"] == "none" for c in r["issue_checks"])
    provider.generate.assert_not_called()


def test_no_issues():
    s = state()
    s["plan"]["issues"] = []
    s["plan"]["search_objectives"] = []
    s = _finish(
        s["plan"], s["requests"], s["responses"], total=len(s["plan"]["subqueries"]), calls=s["executed_searches"]
    )
    with pytest.raises(JudgeAdapterError, match="JUDGE_ISSUES_REQUIRED"):
        adapt_search(s, **args())


@pytest.mark.parametrize("partial", [False, True])
def test_failed_partial_retained(partial):
    from src.applications.tillegal.retrieval.errors import RetrievalErrorDetail

    s = state()
    responses = list(s["responses"])
    idx = 1 if partial else 0
    responses[idx] = responses[idx].model_copy(
        update={
            "status": "FAILED",
            "evidence": (),
            "error": RetrievalErrorDetail(
                code="DATABASE_READ_FAILED", message="Read failed", category="DATABASE_FAILURE", stage="read"
            ),
        }
    )
    s = _finish(
        s["plan"], s["requests"][: idx + 1], responses[: idx + 1], total=len(s["plan"]["subqueries"]), calls=idx + 1
    )
    with pytest.raises(JudgeAdapterError) as exc:
        adapt_search(s, **args())
    assert exc.value.code == "JUDGE_SEARCH_NOT_COMPLETE"
    assert exc.value.native_context["errors"] and exc.value.native_context["completeness"] == (
        "PARTIAL" if partial else "FAILED"
    )


def test_conflicting_same_chunk_keeps_distinct_ids():
    import hashlib

    s = state()
    responses = list(s["responses"])
    e = responses[1].evidence[0]
    e = e.model_copy(
        update={
            "content": e.content + " changed",
            "content_sha256": hashlib.sha256((e.content + " changed").encode()).hexdigest(),
        }
    )
    responses[1] = responses[1].model_copy(update={"evidence": (e, *responses[1].evidence[1:])})
    s = _finish(s["plan"], s["requests"], responses, total=len(s["plan"]["subqueries"]), calls=s["executed_searches"])
    a = adapt_search(s, **args())
    assert "EVIDENCE_IDENTITY_CONFLICT" in a.native_context["warnings"]
    assert len(a.evidence_map) == len(s["evidence"])


@pytest.mark.parametrize(
    "raw,code",
    [("bad", "INVALID_OUTPUT_JSON"), ('{"status":1,"status":2}', "INVALID_OUTPUT_JSON"), (42, "INVALID_OUTPUT_SCHEMA")],
)
def test_provider_output(raw, code):
    a = adapt_search(state(), **args())
    provider = Mock(structured_output=False)
    provider.generate.return_value = raw
    assert JudgeAgent(provider).evaluate(a.judge_input)["error_code"] == code


def test_provider_schema_timeout_limits():
    a = adapt_search(state(), **args())
    provider = Mock(structured_output=True, output_schema={})
    assert JudgeAgent(provider).evaluate(a.judge_input)["error_code"] == "JUDGE_PROVIDER_SCHEMA_MISMATCH"
    provider.generate.assert_not_called()
    provider = Mock(structured_output=False)
    provider.generate.side_effect = TimeoutError
    assert JudgeAgent(provider).evaluate(a.judge_input)["error_code"] == "PROVIDER_TIMEOUT"
    assert (
        JudgeAgent(provider, JudgeLimits(max_input_bytes=1024)).evaluate(a.judge_input)["error_code"]
        == "JUDGE_INPUT_LIMIT"
    )


def test_mismatched_options_and_corrupt_aggregate():
    s = state()
    kw = args()
    kw["options"] = options().model_copy(update={"top_k": 3})
    with pytest.raises(JudgeAdapterError, match="JUDGE_OPTIONS_MISMATCH"):
        adapt_search(s, **kw)
    s["evidence"] = ()
    with pytest.raises(JudgeAdapterError, match="JUDGE_SEARCH_STATE_INCONSISTENT"):
        adapt_search(s, **args())
