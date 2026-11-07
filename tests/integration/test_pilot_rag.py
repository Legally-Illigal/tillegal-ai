"""Offline checks against the real pinned artifacts. Generation is a test double."""
import asyncio
import os
import socket
import threading
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

pytest.importorskip("ai_core", reason="Pilot tests require the sibling BasicRAG source checkout")

from ai_core.basic_rag import BasicRAG
from ai_core.bm25_retrieval import load_index
from ai_core.rag_generation import MockProvider
from ai_core.retrieval_runtime import ROOT, make_retriever
from src.bootstrap import create_app
from src.core.config import AppSettings
from src.framework.llm.gateway import LocalChatProvider, answer_provider

MANIFEST = ROOT / "data/indexes/labor-pilot-3-t4-bm25/manifest.json"
pytestmark = pytest.mark.skipif(not MANIFEST.is_file(), reason="Pinned pilot index is not installed")


@pytest.mark.parametrize("mode,rerank", [
    ("bm25", False), ("dense", False), ("hybrid", False), ("hybrid", True)
])
@pytest.mark.pilot_artifacts
def test_real_index_http_parity(monkeypatch, mode, rerank):
    if mode != "bm25" and os.getenv("TILLEGAL_TEST_ML") != "1":
        pytest.skip("Set TILLEGAL_TEST_ML=1 with pinned models installed")
    monkeypatch.setenv("TILLEGAL_RAG_PILOT", "1")
    monkeypatch.setenv("TILLEGAL_RETRIEVAL_MODE", mode)
    monkeypatch.setenv("TILLEGAL_RERANK", str(rerank).lower())
    monkeypatch.delenv("TILLEGAL_ANSWER_PROVIDER", raising=False)
    index = load_index(MANIFEST)
    baseline = BasicRAG(index, MockProvider(), retriever=make_retriever(index, mode, rerank))
    questions = ["Đối thoại định kỳ", "Thời giờ làm việc", "qzzzxxyy"]
    references = [baseline.answer(q, request_id=f"user-{i}", top_k=3) for i, q in enumerate(questions)]
    del baseline
    with TestClient(create_app(AppSettings())) as client, patch.object(
        socket.socket, "connect", side_effect=AssertionError("unexpected network")
    ):
        for idx, question in enumerate(questions):
            rid = f"user-{idx}"
            expected = references[idx]
            response = client.post("/pilot/legal-qa", json={"question": question, "top_k": 3},
                                   headers={"X-Request-ID": rid})
            assert response.status_code == 200, response.text
            actual = response.json()
            for key in ("request_id", "evidence_bundle", "candidate_citations", "status", "verification_status"):
                assert actual[key] == expected[key]
            if idx == 0:
                response = client.post("/pilot/legal-qa", json={"workflow": "multi_agent",
                    "question": "Trích dẫn: " + question, "top_k": 3}, headers={"X-Request-ID": rid})
                assert response.status_code == 200
                assert response.json()["evidence_bundles"][0] == expected["evidence_bundle"]


def test_provider_configuration():
    assert isinstance(answer_provider({}), MockProvider)
    assert isinstance(answer_provider({"TILLEGAL_ANSWER_PROVIDER": "local",
                                      "TILLEGAL_ANSWER_MODEL": "fixture"}), LocalChatProvider)
    with pytest.raises(ValueError):
        answer_provider({"TILLEGAL_ANSWER_PROVIDER": "paid"})
    with pytest.raises(ValueError):
        answer_provider({"TILLEGAL_ANSWER_PROVIDER": "local"})


@pytest.mark.pilot_artifacts
def test_overlapping_requests(monkeypatch):
    monkeypatch.setenv("TILLEGAL_RAG_PILOT", "1")
    entering, release = threading.Event(), threading.Event()
    with TestClient(create_app(AppSettings())) as client:
        provider = client.app.state.legal_qa.provider
        generate = provider.generate

        def delayed(messages):
            entering.set()
            assert release.wait(10)
            return generate(messages)

        monkeypatch.setattr(provider, "generate", delayed)
        def ask(question):
            return client.post("/pilot/legal-qa", json={"question": question})

        async def exercise():
            first = asyncio.create_task(asyncio.to_thread(ask, "đối thoại"))
            try:
                assert await asyncio.to_thread(entering.wait, 10)
                assert (await asyncio.to_thread(ask, "khác")).status_code == 429
            finally:
                release.set()
            one = (await first).json()
            two = (await asyncio.to_thread(ask, "lao động")).json()
            assert one["run_id"] != two["run_id"]
            for result, question in ((one, "đối thoại"), (two, "lao động")):
                assert result["evidence_bundle"]["query"] == question
                assert result["evidence_bundle"]["request_id"] == result["request_id"]

        asyncio.run(exercise())

def test_reference_and_quote_checks():
    from ai_core.data_contracts import content_hash
    from src.applications.tillegal.graphs.citation_verification import check_candidates

    entry = {"evidence_id": "e1", "document_id": "doc", "document_version_id": "v1", "chunk_id": "c1",
             "quote": "quote", "quote_sha256": content_hash("quote")}
    checks = check_candidates({"evidence": [entry]}, [
        entry, dict(entry, quote="altered"), dict(entry, document_version_id="v2"),
        dict(entry, evidence_id="missing")
    ])
    assert [c["bundle_identity"] for c in checks] == ["MATCH", "MATCH", "MISMATCH", "MISMATCH"]
    assert [c["normalized_quote_against_bundle"] for c in checks] == [
        "MATCH", "UNCONFIRMED", "UNCONFIRMED", "UNCONFIRMED"]
    assert all(c["claim_support"] == "NOT_EVALUATED" for c in checks)


def test_local_wire_contract(monkeypatch):
    import json
    from unittest.mock import MagicMock

    from ai_core.rag_generation import GenerationError

    connection = MagicMock()
    monkeypatch.setattr("src.framework.llm.gateway.HTTPConnection", connection)
    response = connection.return_value.getresponse.return_value
    response.status = 200
    response.read.return_value = json.dumps({"choices": [{"finish_reason": "stop", "message": {"content": "ok"}}],
                                              "usage": {"completion_tokens": 7}}).encode()
    adapter = LocalChatProvider("wire-fixture", 1234)
    raw = adapter.generate([{"role": "user", "content": "fixture"}])
    assert raw == "ok" and raw.metadata == {"completion_tokens": 7}
    connection.assert_called_once_with("127.0.0.1", 1234, timeout=25)
    _, path, payload, headers = connection.return_value.request.call_args.args
    assert path == "/v1/chat/completions"
    assert json.loads(payload)["model"] == "wire-fixture"
    assert "Authorization" not in headers
    response.status = 429
    with pytest.raises(GenerationError, match="PROVIDER_RATE_LIMIT"):
        adapter.generate([])
    assert connection.return_value.request.call_count == 2

def test_pilot_rejects_unsafe_settings(monkeypatch):
    monkeypatch.setenv("TILLEGAL_RAG_PILOT", "1")
    with pytest.raises(ValueError, match="development"):
        create_app(AppSettings(app={"env": "production"}))
    with pytest.raises(ValueError, match="database integrations disabled"):
        create_app(AppSettings(supabase={"database_url": "postgresql://localhost/test", "auto_migrate": True}))


@pytest.mark.pilot_artifacts
def test_failed_generation_returns_no_draft(monkeypatch):
    monkeypatch.setenv("TILLEGAL_RAG_PILOT", "1")
    with TestClient(create_app(AppSettings())) as client:
        monkeypatch.setattr(client.app.state.legal_qa.provider, "generate", lambda _: "broken")
        result = client.post("/pilot/legal-qa", json={"question": "đối thoại"})
        assert result.status_code == 502
        assert result.json() == {"detail": "INVALID_OUTPUT"}
        assert client.post("/pilot/legal-qa", json={"question": "   "}).status_code == 422
