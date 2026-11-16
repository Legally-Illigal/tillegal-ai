import asyncio
from copy import deepcopy

import pytest
from pydantic import ValidationError

from scripts.search_legal_chunks import main
from src.applications.tillegal.retrieval.reranker import RerankingOperationalError, select_candidates
from src.applications.tillegal.retrieval.reranking_models import (
    PairScores,
    RerankConfig,
    RerankedHybridRetrievalResponse,
)
from src.integrations.embeddings.cross_encoder_reranker import LocalCrossEncoder
from tests.unit.applications.tillegal.retrieval.test_contracts import request
from tests.unit.applications.tillegal.retrieval.test_hybrid_service import hybrid_service


class Scorer:
    def __init__(self, scores=None, error=None):
        self.scores = scores
        self.error = error
        self.calls = []

    async def score_pairs(self, query, passages):
        self.calls.append((query, passages))
        if self.error:
            raise self.error
        return PairScores(
            scores=self.scores if self.scores is not None else tuple(range(len(passages))),
            truncated=(False,) * len(passages),
            cold=False,
            load_seconds=0,
            inference_seconds=0,
        )


def configured(scorer=None, **kwargs):
    svc, *deps = hybrid_service(**kwargs)
    svc._rerank_config = RerankConfig(enabled=True, candidate_pool=20)
    svc._pair_scorer = scorer or Scorer()
    return svc, deps


def test_real_service_integration_expands_pool_preserves_metadata_and_rrf_scores():
    baseline, *_ = hybrid_service()
    original = asyncio.run(baseline.search(request(mode="hybrid", top_k=20)))
    scorer = Scorer()
    svc, deps = configured(scorer)
    result = asyncio.run(svc.search(request(mode="hybrid", top_k=2)))
    assert result.reranking.status == "APPLIED"
    assert result.top_k == 2 and len(result.reranking.candidates) == 3
    assert scorer.calls[0][1] == tuple(e.content for e in original.evidence)
    assert [e.retrieval_chunk_id for e in result.evidence] == [e.retrieval_chunk_id for e in original.evidence][::-1][
        :2
    ]
    originals = {e.retrieval_chunk_id: e.model_dump(exclude={"rank"}) for e in original.evidence}
    assert all(e.model_dump(exclude={"rank"}) == originals[e.retrieval_chunk_id] for e in result.evidence)
    assert len(deps[3].calls) == len(deps[4].calls) == 4
    assert RerankedHybridRetrievalResponse.model_validate_json(result.model_dump_json()) == result


@pytest.mark.parametrize("scores", [(1,), (float("nan"), 2, 3), (float("inf"), 2, 3)])
def test_invalid_scores_fallback_to_original_rrf(scores):
    svc, _ = configured(Scorer(scores))
    result = asyncio.run(svc.search(request(mode="hybrid", top_k=2)))
    assert result.reranking.status == "FALLBACK"
    assert [e.retrieval_chunk_id.int for e in result.evidence] == [2, 1]
    assert any(w.code == "RERANKING_FALLBACK" for w in result.warnings)


@pytest.mark.parametrize(
    "code", ["MODEL_NOT_PROVISIONED", "MODEL_LOAD_FAILED", "INFERENCE_FAILED", "TOKENIZATION_FAILED", "MODEL_BUSY"]
)
def test_operational_failure_visible_not_no_match(code):
    svc, _ = configured(Scorer(error=RerankingOperationalError(code)))
    result = asyncio.run(svc.search(request(mode="hybrid", top_k=5)))
    assert result.status == "OK" and result.reranking.status == "FALLBACK"
    assert result.reranking.failure_code == code and len(result.evidence) == 3


def test_empty_no_model_call_and_single_candidate_is_scored():
    scorer = Scorer()
    svc, _ = configured(scorer, sparse_hits=(), dense_hits=())
    result = asyncio.run(svc.search(request(mode="hybrid")))
    assert result.status == "NO_MATCH" and scorer.calls == []
    svc, _ = configured(scorer, dense_hits=())
    result = asyncio.run(svc.search(request(mode="hybrid", top_k=1)))
    assert len(result.evidence) == 1 and len(scorer.calls) == 1
    single = (result.evidence[0],)
    assert len(select_candidates(single, (5,), 5)) == 1


def test_equal_scores_retain_original_order():
    svc, _ = configured(Scorer((1, 1, 1)))
    result = asyncio.run(svc.search(request(mode="hybrid", top_k=3)))
    assert [e.retrieval_chunk_id.int for e in result.evidence] == [2, 1, 3]


def test_disabled_and_nonhybrid_compatibility():
    scorer = Scorer()
    svc, _ = configured(scorer)
    for mode in ("bm25", "dense"):
        result = asyncio.run(svc.search(request(mode=mode)))
        assert "reranking" not in result.model_dump()
    svc._rerank_config = RerankConfig()
    result = asyncio.run(svc.search(request(mode="hybrid", top_k=1)))
    assert "reranking" not in result.model_dump() and scorer.calls == []


def test_retrieval_integrity_and_policy_failures_never_fallback():
    for kind in ("hash", "policy", "duplicate"):
        scorer = Scorer()
        svc, deps = configured(scorer)
        if kind == "hash":
            next(iter(deps[-1].rows.values()))["content_sha256"] = "0" * 64
        elif kind == "policy":
            svc._sources.row["usage_policy"] = "NOT_ALLOWED"
        else:
            svc._sparse.hits = (svc._sparse.hits[0], svc._sparse.hits[0])
        result = asyncio.run(svc.search(request(mode="hybrid")))
        assert result.status == "FAILED" and result.evidence == () and scorer.calls == []


def test_pure_selection_rejects_duplicates_missing_content_bool_and_count():
    svc, _ = configured()
    result = asyncio.run(svc.search(request(mode="hybrid", top_k=3)))
    candidates = tuple(
        sorted(
            result.evidence,
            key=lambda e: next(
                r.original_rank for r in result.reranking.candidates if r.retrieval_chunk_id == e.retrieval_chunk_id
            ),
        )
    )
    candidates = tuple(e.model_copy(update={"rank": i}) for i, e in enumerate(candidates, 1))
    for bad in ((candidates[0], candidates[0]), (candidates[0].model_copy(update={"content": ""}),)):
        with pytest.raises(Exception):
            select_candidates(bad, None, 2)
    with pytest.raises(RerankingOperationalError):
        select_candidates(candidates, (True,) * 3, 2)


def test_index_change_during_inference_fails():
    svc, deps = configured()

    class Changing(Scorer):
        async def score_pairs(self, query, passages):
            deps[3].before["updated_at"] = "2026-11-16T00:00:00Z"
            return await super().score_pairs(query, passages)

    svc._pair_scorer = Changing()
    result = asyncio.run(svc.search(request(mode="hybrid")))
    assert result.status == "FAILED" and result.evidence == ()


def test_model_timeout_fallback_and_total_timeout_failure():
    class Slow(Scorer):
        async def score_pairs(self, query, passages):
            await asyncio.sleep(1)

    svc, _ = configured(Slow())
    svc._rerank_config = RerankConfig(enabled=True, inference_timeout_seconds=0.001)
    result = asyncio.run(svc.search(request(mode="hybrid")))
    assert result.reranking.failure_code == "RERANK_TIMEOUT" and result.status == "OK"
    svc._rerank_config = RerankConfig(enabled=True, total_timeout_seconds=0.001)
    result = asyncio.run(svc.search(request(mode="hybrid")))
    assert result.status == "FAILED"


def test_response_rejects_score_order_and_rrf_tampering():
    svc, _ = configured()
    result = asyncio.run(svc.search(request(mode="hybrid")))
    for field in ("score", "order"):
        payload = deepcopy(result.model_dump())
        if field == "score":
            payload["reranking"]["candidates"][0]["rrf_score"] += 1
        else:
            payload["evidence"] = tuple(reversed(payload["evidence"]))
        with pytest.raises(ValidationError):
            RerankedHybridRetrievalResponse.model_validate(payload)


def test_missing_local_model_no_download(tmp_path):
    with pytest.raises(RerankingOperationalError, match="MODEL_NOT_PROVISIONED"):
        asyncio.run(LocalCrossEncoder(RerankConfig(model_path=tmp_path / "missing")).score_pairs("q", ("p",)))


def test_cli_rejects_reranking_nonhybrid_before_dependencies(capsys):
    args = ["--query", "q", "--as-of-date", "2026-11-16", "--allowed-policy", "EXPERIMENTAL_ONLY", "--rerank"]
    assert main(args, service_factory=lambda: pytest.fail("dependencies called")) == 2
    assert "INVALID_ARGUMENTS" in capsys.readouterr().out


def test_cli_serialization_preserves_ce_order_not_rrf_order(capsys):
    import json
    from types import SimpleNamespace

    svc, _ = configured()
    result = asyncio.run(svc.search(request(mode="hybrid", top_k=3)))

    async def search(req):
        return result

    args = [
        "--query",
        "q",
        "--as-of-date",
        "2026-11-16",
        "--allowed-policy",
        "EXPERIMENTAL_ONLY",
        "--mode",
        "hybrid",
        "--dense-model-path",
        "local-e5",
        "--rerank",
        "--rerank-model-path",
        "local-ce",
    ]
    assert main(args, service_factory=lambda: SimpleNamespace(search=search)) == 0
    payload = json.loads(capsys.readouterr().out)
    assert [e["retrieval_chunk_id"] for e in payload["evidence"]] == [
        str(e.retrieval_chunk_id) for e in result.evidence
    ]
    assert [e["raw_score"] for e in payload["evidence"]] != sorted(
        [e["raw_score"] for e in payload["evidence"]], reverse=True
    )


def test_adapter_fake_model_pair_mapping_truncation_and_no_sigmoid(monkeypatch):
    import sys
    from contextlib import nullcontext
    from types import SimpleNamespace

    calls = []

    class Tokenizer:
        def num_special_tokens_to_add(self, pair):
            return 4

        def __call__(self, query, passages=None, **kwargs):
            if passages is None:
                return {"input_ids": list(range(len(query.split())))}
            calls.append((query, passages, kwargs))
            return {"batch": passages}

    class Logits:
        def __init__(self, values):
            self.values = values
            self.shape = (len(values), 1)

        def __getitem__(self, key):
            return self

        def cpu(self):
            return self

        def tolist(self):
            return self.values

    adapter = LocalCrossEncoder(RerankConfig(batch_size=1, max_length=32))
    adapter._tokenizer = Tokenizer()
    adapter._model = lambda **inputs: SimpleNamespace(logits=Logits([float(len(p)) for p in inputs["batch"]]))
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(inference_mode=nullcontext))
    output = adapter._score("query", ("short", "long " * 40))
    assert output.scores == (5.0, 200.0) and output.truncated == (False, True)
    assert calls[0][2]["truncation"] == "only_second"
    with pytest.raises(RerankingOperationalError, match="QUERY_TOO_LONG"):
        adapter._score("q " * 40, ("p",))
    adapter._model = lambda **inputs: (_ for _ in ()).throw(RuntimeError("private"))
    with pytest.raises(RerankingOperationalError, match="INFERENCE_FAILED"):
        adapter._score("q", ("p",))


def test_adapter_busy_and_cancellation_keep_worker_lock():
    from threading import Event

    started, release = Event(), Event()
    adapter = LocalCrossEncoder(RerankConfig())

    def load():
        started.set()
        release.wait(5)
        raise RerankingOperationalError("MODEL_LOAD_FAILED")

    adapter._load = load

    async def scenario():
        task = asyncio.create_task(adapter.score_pairs("q", ("p",)))
        while not started.is_set():
            await asyncio.sleep(0.001)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        try:
            with pytest.raises(RerankingOperationalError, match="MODEL_BUSY"):
                await adapter.score_pairs("q", ("p",))
        finally:
            release.set()

    asyncio.run(scenario())
    assert not adapter._lock.locked()
