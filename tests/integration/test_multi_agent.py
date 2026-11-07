"""Technical fixtures and pilot HTTP checks. No API keys or remote LLM."""
import asyncio
import threading
from dataclasses import replace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

pytest.importorskip("ai_core")
from ai_core.data_contracts import content_hash
from ai_core.rag_generation import GenerationError
from src.applications.tillegal.agents.judge.agent import judge
from src.applications.tillegal.agents.query.agent import understand
from src.applications.tillegal.agents.response.agent import respond
from src.applications.tillegal.agents.search.agent import search
from src.applications.tillegal.graphs.citation_verification import verify_claims
from src.bootstrap import create_app
from src.core.config import AppSettings
from src.framework.llm.gateway import LocalChatProvider, answer_provider
from src.framework.tools.permissions import ToolPermissionDeniedError


def row(key="one", version="v1"):
    return dict(evidence_id=key, document_id="doc", document_version_id=version, chunk_id=key,
                is_heading=False, quote="đối thoại", quote_sha256=content_hash("đối thoại"))


def bundle(key="one", version="v1"):
    return dict(request_id="r", index_id="index", evidence=[row(key, version)], bundle_id=key,
                status="ASSEMBLED", groups=[{"omitted_chunk_ids": []}])


def state(question="Trích dẫn: đối thoại"):
    return dict(question=question, request_id="r", top_k=1, plan=understand(question),
                evidence={"one": row()}, bundles=[bundle()], search_trace=[{"query": "đối thoại"}],
                iteration=1, new_count=1)


def test_query_understanding():
    plan = understand("Lương năm 2020? Nghỉ phép theo luật 45/2019/QH14?")
    assert plan["domain"] == "labour" and plan["temporal_scope"] == ["2020"]
    assert sum(q["purpose"] == "question_part" for q in plan["subqueries"]) == 2
    assert plan["original"].endswith("QH14?")
    assert understand("Có được không?")["clarification"]


def test_search_dedup_preserves_versions_and_omissions():
    first = bundle()
    first["groups"][0]["omitted_chunk_ids"] = ["exception"]
    tools = AsyncMock()
    tools.execute.side_effect = [first, first, bundle("two", "v2")]
    out = asyncio.run(search({"pending": ["a","b","c"], "request_id":"r","top_k":1}, tools, 3))
    assert list(out["evidence"]) == ["one","two"]
    assert out["bundles"][0]["groups"][0]["omitted_chunk_ids"] == ["exception"]
    assert len(out["search_trace"]) == 3


def test_judge_insufficient_exception_version_budget():
    s = state()
    assert judge(s, 4, 2)["decision"] == "SUFFICIENT"
    s["bundles"][0]["groups"][0]["omitted_chunk_ids"] = ["exception"]
    s["evidence"]["two"] = row("two", "v2")
    decision = judge(s, 4, 2)
    assert decision["decision"] == "UNCERTAIN" and decision["stop"] == "REFINE"
    assert {"COMPETING_DOCUMENT_VERSIONS", "OMITTED_CONTEXT"} <= set(decision["gaps"])
    assert judge(s, 1, 2)["stop"] == "RETRIEVAL_BUDGET"
    s.update(iteration=2, new_count=0)
    assert judge(s, 4, 3)["stop"] == "NO_NEW_EVIDENCE"


def test_response_rejects_invalid_output():
    from unittest.mock import Mock
    provider = Mock(mode="local")
    provider.generate.return_value = '{"claims":[{"text":3}]}'
    s = state()
    s["judgments"] = [judge(s, 4, 2)]
    with pytest.raises(GenerationError, match="INVALID_OUTPUT"):
        respond(s, provider, threading.Lock())


def test_verification_rejects_foreign_and_unsupported():
    proposals = [{"evidence_id": "foreign", "text":"đối thoại"}, {"evidence_id":"one","text":"được miễn"},
                 {"evidence_id":"one","text":"đối thoại"}]
    checks, claims, citations = verify_claims({"one": row()}, ["one"], proposals)
    assert [c["claim_text_check"] for c in checks] == ["REJECTED", "REJECTED", "EXACT_QUOTE"]
    assert claims == proposals[-1:] and len(citations) == 1
    assert checks[-1]["claim_support"] == "NOT_EVALUATED"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("TILLEGAL_RAG_PILOT", "1")
    monkeypatch.setenv("TILLEGAL_ANSWER_PROVIDER", "mock")
    monkeypatch.setenv("TILLEGAL_RESPONSE_PROVIDER", "mock")
    with TestClient(create_app(AppSettings())) as pilot:
        yield pilot


def ask(client, question):
    return client.post("/pilot/legal-qa", json={"workflow":"multi_agent", "question":question, "top_k":1})


@pytest.mark.pilot_artifacts
def test_multi_http_decisions(client):
    lookup = ask(client, "Trích dẫn: đối thoại").json()
    assert lookup["status"] == "EXTRACTIVE_DRAFT", lookup["judgments"]
    assert lookup["citation_checks"][0]["claim_text_check"] == "EXACT_QUOTE"
    for q in ("qzzzxxyy qzzzyyyy", "đối thoại; nghỉ phép"):
        result = ask(client, q).json()
        assert result["judgments"][0]["stop"] == "REFINE"
        assert len(result["retrieval_trace"]) <= 4
        assert result["judgments"][-1]["stop"] != "REFINE"
        if q.startswith("qzzz"):
            assert result["retrieval_trace"][0]["status"] == "EMPTY"
            assert result["status"] == "ABSTAINED"
    assert not ask(client, "Có được không?").json()["retrieval_trace"]


@pytest.mark.pilot_artifacts
def test_backpressure_and_run_isolation(client):
    tool = client.app.state.legal_qa.tools
    entered, release = threading.Event(), threading.Event()
    execute = tool.execute

    async def delayed(*args, **kwargs):
        entered.set()
        await asyncio.to_thread(release.wait, 5)
        return await execute(*args, **kwargs)

    from concurrent.futures import ThreadPoolExecutor
    with patch.object(tool, "execute", delayed), ThreadPoolExecutor(1) as worker:
        task = worker.submit(ask, client, "Trích dẫn: đối thoại")
        try:
            assert entered.wait(5)
            assert ask(client, "Trích dẫn: nghỉ phép").status_code == 429
        finally:
            release.set()
        first = task.result().json()
    second = ask(client, "Trích dẫn: nghỉ phép").json()
    assert first["run_id"] != second["run_id"]
    for result in (first, second):
        assert all(b["request_id"] == result["request_id"] for b in result["evidence_bundles"])


@pytest.mark.pilot_artifacts
def test_tool_deadline_and_policy(client):
    tool = client.app.state.legal_qa.tools
    spec = tool._registry.get("legal_retrieval")
    with patch.object(tool._registry, "get", return_value=replace(spec, handler=lambda _: asyncio.sleep(1),
                                                                timeout_seconds=0.01)):
        assert ask(client, "Trích dẫn: đối thoại").status_code == 504
    with patch.object(tool, "execute", side_effect=ToolPermissionDeniedError()):
        assert ask(client, "Trích dẫn: đối thoại").status_code == 403


@pytest.mark.pilot_artifacts
def test_provider_timeout_and_gemini_gate(monkeypatch):
    with pytest.raises(ValueError, match="GEMINI_DISABLED"):
        answer_provider({"TILLEGAL_RESPONSE_PROVIDER":"gemini"}, profile="RESPONSE")
    monkeypatch.setenv("TILLEGAL_RAG_PILOT","1")
    monkeypatch.setenv("TILLEGAL_RESPONSE_PROVIDER","local")
    monkeypatch.setenv("TILLEGAL_RESPONSE_MODEL","fixture")
    with TestClient(create_app(AppSettings())) as pilot, patch.object(
        LocalChatProvider, "generate", side_effect=GenerationError("PROVIDER_TIMEOUT")
    ):
        assert ask(pilot, "Trích dẫn: đối thoại").status_code == 504


def test_temporal_and_jurisdiction_checks():
    s = state("Trích dẫn: đối thoại năm 2017")
    s["evidence"]["one"]["document"] = {"effective_from":"2021-01-01"}
    result = judge(s, 4, 2)
    assert result["outside_reported_period"] == ["one"] and not result["selected"]
    assert judge(state("Tiền lương tại Mỹ"), 4, 2)["jurisdiction"] == "OUTSIDE_VN_PILOT"


@pytest.mark.pilot_artifacts
def test_budget_is_enforced_at_tool_boundary(monkeypatch):
    monkeypatch.setenv("TILLEGAL_RAG_PILOT", "1")
    monkeypatch.setenv("TILLEGAL_SEARCH_BUDGET", "1")
    with TestClient(create_app(AppSettings())) as pilot:
        result = ask(pilot, "đối thoại; nghỉ phép").json()
        assert result["judgments"][-1]["stop"] == "RETRIEVAL_BUDGET"
        assert len(result["retrieval_trace"]) == 1


def test_gemini_offline_wire_and_local_quota():
    import json
    from unittest.mock import Mock
    from src.framework.llm.providers.gemini import GeminiProvider, gemini_payload, gemini_result

    messages = [{"role":"system","content":"s"},{"role":"user","content":"q"}]
    payload = json.loads(gemini_payload(messages))
    assert payload["generationConfig"]["maxOutputTokens"] == 1024
    raw = gemini_result(json.dumps({"candidates":[{"finishReason":"STOP","content":{"parts":[{"text":"{}"}]}}],
                                   "usageMetadata":{"promptTokenCount":42}}))
    assert raw == "{}" and raw.metadata == {"prompt_tokens":42}
    with pytest.raises(GenerationError, match="INVALID_OUTPUT"):
        gemini_result(b'{"candidates":[]}')
    policy = Mock(allowed_models=frozenset({"gemini-test"}))
    with pytest.raises(ValueError, match="allowlist"):
        GeminiProvider("gemini-other", policy)
    provider = GeminiProvider("gemini-test", policy)
    provider.reserve_local_attempt()
    with pytest.raises(GenerationError, match="PROVIDER_RATE_LIMIT"):
        provider.reserve_local_attempt()
