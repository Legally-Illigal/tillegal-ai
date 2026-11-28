"""Native Summary contract tests; fixtures replay, no semantic or live evaluation."""

import json
from copy import deepcopy
from unittest.mock import Mock

import pytest

from src.applications.tillegal.agents.judge.adapter import NativeJudgeResult, adapt_search
from src.applications.tillegal.agents.judge.schemas import error_result
from src.applications.tillegal.agents.response.adapter import adapt_judge
from src.applications.tillegal.agents.response.agent import FixtureSummaryProvider, SummaryAgent
from src.applications.tillegal.agents.response.schemas import LLM_OUTPUT_SCHEMA
from tests.unit.applications.tillegal.test_judge_native import args, response, state


def value(status="SUFFICIENT"):
    a = adapt_search(state(), **args())
    r = error_result("FIXTURE_ERROR") if status == "ERROR" else response(a, status)
    return adapt_judge(NativeJudgeResult(a, r, {}))


def output(v, **changes):
    r = {
        "units": [
            {
                "text": "Nội dung minh họa, không phải quy định pháp luật.",
                "issue_ids": [v["query_plan"]["issues"][0]["issue_id"]],
                "evidence_ids": [v["judge_result"]["usable_evidence_ids"][0]],
                "statement_type": "source_statement",
            }
        ],
        "limitations": [],
        "abstain": False,
    }
    r.update(changes)
    return r


def test_native_success_immutable_ids_and_metadata():
    v = value()
    before = deepcopy(v)
    r = SummaryAgent(FixtureSummaryProvider(output(v))).summarize(v)
    assert r["status"] == "DRAFT_UNVERIFIED" and v == before and r["draft_version"] == 1
    e = r["citations"][0]
    assert e["evidence_id"] in v["carrier"]["adapted"]["evidence_map"]
    assert e["document_version_id"] is None and e["exact_citation_verified"] is None
    assert e["content_representation"] == "retrieval_chunk_content"
    assert "DRAFT_NOT_VERIFIED" in r["limitations"]


def test_only_usable_content_in_model_payload():
    v = value("INSUFFICIENT")
    keep = v["judge_result"]["usable_evidence_ids"][:1]
    v["judge_result"]["usable_evidence_ids"] = keep
    v["carrier"]["judge_result"] = deepcopy(v["judge_result"])
    provider = Mock(structured_output=False)
    provider.generate.return_value = json.dumps(output(v))
    r = SummaryAgent(provider).summarize(v)
    assert r["status"] == "DRAFT_UNVERIFIED"
    payload = json.loads(provider.generate.call_args.args[0][1]["content"])
    assert [e["evidence_id"] for e in payload["evidence"]] == keep
    assert "carrier" not in payload and "native_context" not in payload
    assert "JUDGE_INSUFFICIENT" in r["limitations"]


@pytest.mark.parametrize("status", ["ERROR", "INSUFFICIENT"])
def test_no_provider_on_error_or_no_usable(status):
    v = value(status)
    if status == "INSUFFICIENT":
        v["judge_result"]["usable_evidence_ids"] = []
        v["carrier"]["judge_result"] = deepcopy(v["judge_result"])
    provider = Mock()
    r = SummaryAgent(provider).summarize(v)
    provider.generate.assert_not_called()
    assert r["status"] == ("ERROR" if status == "ERROR" else "ABSTAINED_UNVERIFIED")


@pytest.mark.parametrize("kind", ["foreign", "url", "marker", "mapping", "application"])
def test_invalid_model_content(kind):
    v = value("INSUFFICIENT")
    o = output(v)
    if kind == "foreign":
        o["units"][0]["evidence_ids"] = ["foreign"]
    if kind == "url":
        o["units"][0]["text"] = "See https://example.org"
    if kind == "marker":
        o["units"][0]["text"] = "Citation [R1]"
    if kind == "mapping":
        o["units"][0]["issue_ids"] = ["foreign"]
    if kind == "application":
        o["units"][0]["statement_type"] = "application"
    assert SummaryAgent(FixtureSummaryProvider(o)).summarize(v)["status"] == "ERROR"


def test_tampered_mapping_and_schema():
    v = value()
    eid = next(iter(v["carrier"]["adapted"]["evidence_map"]))
    v["carrier"]["adapted"]["evidence_map"][eid]["native"]["title"] = "tampered"
    provider = Mock()
    r = SummaryAgent(provider).summarize(v)
    assert r["error"]["code"] == "SUMMARY_INVALID_NATIVE_CARRIER"
    provider.generate.assert_not_called()
    from src.applications.tillegal.agents.judge.schemas import OUTPUT_SCHEMA

    provider = Mock(structured_output=True, output_schema=OUTPUT_SCHEMA)
    assert SummaryAgent(provider).summarize(value())["error"]["code"] == "SUMMARY_PROVIDER_SCHEMA_MISMATCH"
    provider.generate.assert_not_called()


def test_abstain_and_json_and_version():
    v = value()
    r = SummaryAgent(
        FixtureSummaryProvider({"units": [], "limitations": ["Không đủ căn cứ minh họa."], "abstain": True})
    ).summarize(v)
    assert r["status"] == "ABSTAINED_UNVERIFIED"
    assert SummaryAgent(FixtureSummaryProvider("bad")).summarize(v)["error"]["code"] == "SUMMARY_INVALID_OUTPUT_JSON"
    v["draft_version"] = 2
    assert SummaryAgent(FixtureSummaryProvider("bad")).summarize(v)["status"] == "ERROR"


@pytest.mark.parametrize("field", ["request_id", "question", "as_of_date"])
def test_context_tamper(field):
    v = value()
    v[field] = "changed"
    provider = Mock()
    assert SummaryAgent(provider).summarize(v)["status"] == "ERROR"
    provider.generate.assert_not_called()


def test_wire_schema_uses_summary_and_safe_errors(monkeypatch):
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "scripts"))
    import live_gemini_judge as transport
    from live_gemini_summary import LiveGeminiSummary
    from pydantic import SecretStr

    from src.applications.tillegal.agents.judge.support import GenerationError
    from src.framework.llm.providers.gemini_adapter import GeminiProviderError

    calls = []

    class Completion:
        def __init__(self, *args, **kwargs):
            pass

        async def __call__(self, **kwargs):
            calls.append(kwargs)
            return "{}"

    monkeypatch.setattr(transport, "GeminiStructuredCompletion", Completion)
    provider = LiveGeminiSummary(SecretStr("fake-test-key"), "fixture")
    provider.generate([{"content": "system"}, {"content": "user"}])
    assert calls[0]["schema"] == transport.wire_schema(LLM_OUTPUT_SCHEMA)
    assert "units" in calls[0]["schema"]["properties"]

    class Failure(Completion):
        async def __call__(self, **kwargs):
            raise GeminiProviderError("GEMINI_RATE_LIMITED", 429)

    monkeypatch.setattr(transport, "GeminiStructuredCompletion", Failure)
    with pytest.raises(GenerationError, match="GEMINI_RATE_LIMITED"):
        provider.generate([{"content": "system"}, {"content": "user"}])


def test_limits_and_timeout():
    from src.applications.tillegal.agents.response.schemas import SummaryLimits

    v = value()
    provider = Mock(structured_output=False)
    provider.generate.side_effect = TimeoutError
    assert SummaryAgent(provider).summarize(v)["error"]["code"] == "SUMMARY_PROVIDER_TIMEOUT"
    assert (
        SummaryAgent(provider, SummaryLimits(max_input_bytes=1024)).summarize(v)["error"]["code"]
        == "SUMMARY_INPUT_LIMIT"
    )


def test_actual_issue_evidence_mismatch():
    v = value("INSUFFICIENT")
    eid = v["judge_result"]["usable_evidence_ids"][0]
    v["judge_result"]["issue_checks"][0]["evidence_ids"] = [v["judge_result"]["usable_evidence_ids"][1]]
    v["carrier"]["judge_result"] = deepcopy(v["judge_result"])
    o = output(v)
    o["units"][0]["evidence_ids"] = [eid]
    r = SummaryAgent(FixtureSummaryProvider(o)).summarize(v)
    assert r["error"]["code"] == "SUMMARY_ISSUE_EVIDENCE_MAPPING_MISMATCH"
