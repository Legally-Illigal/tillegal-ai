"""Cross-mode Query/Search verification with fakes, then real service with fake read ports."""

import asyncio
import inspect
from copy import deepcopy
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from src.applications.tillegal.agents.query.agent import understand
from src.applications.tillegal.agents.search.agent import SearchOptions, search
from src.applications.tillegal.retrieval.contracts import RetrievalResponse
from src.applications.tillegal.retrieval.hybrid_models import HybridConfig, HybridRetrievalResponse
from src.applications.tillegal.retrieval.reranking_models import RerankConfig, RerankedHybridRetrievalResponse
from src.core.config import SupabaseSettings
from src.integrations.database.repositories.rpc import DatabaseRepositoryError
from src.integrations.embeddings.cross_encoder_reranker import LocalCrossEncoder
from src.integrations.embeddings.e5_query_encoder import E5QueryEncoder
from src.query_search_bootstrap import QuerySearch, create_query_search
from tests.unit.applications.tillegal.retrieval.test_contracts import request
from tests.unit.applications.tillegal.retrieval.test_dense_service import FakeEncoder
from tests.unit.applications.tillegal.retrieval.test_hybrid_service import hybrid_service
from tests.unit.applications.tillegal.retrieval.test_reranking import configured

MODES = ("bm25", "dense", "hybrid", "rerank")


def options(mode):
    return SearchOptions(
        mode="hybrid" if mode == "rerank" else mode,
        top_k=2,
        as_of_date=date(2026, 11, 10),
        allowed_usage_policies=("EXPERIMENTAL_ONLY",),
    )


class RecordingService:
    """Record only outer application calls; recursive Hybrid branch calls remain real."""

    def __init__(self, service):
        self.service = service
        self.requests = []
        self.responses = []

    async def search(self, req):
        self.requests.append(req)
        response = await self.service.search(req)
        self.responses.append(response)
        return response


@pytest.mark.parametrize("mode", MODES)
def test_unit_request_mapping_and_no_match_identity(mode):
    opts = options(mode)
    req = request(query="nghỉ phép", **opts.model_dump())
    # A controlled service fake validates Search transport only, not backend execution.
    response = RetrievalResponse(
        **req.model_dump(),
        request_id="00000000-0000-0000-0000-000000000001",
        query_used=req.query,
        selected_index_name="fixture",
        index=None,
        status="NO_MATCH",
        retrieved_at="2026-11-10T00:00:00Z",
    )
    service = AsyncMock()
    service.search.return_value = response
    plan = understand("Trích dẫn: nghỉ phép")
    result = asyncio.run(search(plan, service, opts))
    assert result["requests"] == (req,)
    assert result["responses"][0] is response
    assert result["plan"] is plan and result["status"] == "COMPLETED"
    service.search.assert_awaited_once_with(req)


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("question", ["Có được không?", "31/02/2024"])
def test_clarification_all_modes(mode, question):
    service = AsyncMock()
    result = asyncio.run(QuerySearch(service, options(mode)).search(question))
    assert result["status"] == "CLARIFICATION_REQUIRED"
    assert result["requests"] == result["responses"] == ()
    service.search.assert_not_called()


@pytest.mark.parametrize(
    "changes",
    [
        {"mode": "rerank"},
        {"top_k": 0},
        {"top_k": 51},
        {"top_k": True},
        {"as_of_date": None},
        {"allowed_usage_policies": ()},
    ],
)
def test_unit_invalid_options(changes):
    with pytest.raises(ValidationError):
        SearchOptions.model_validate({**options("bm25").model_dump(), **changes})


@pytest.mark.parametrize(
    "change", [{"subqueries": []}, {"subqueries": [{"text": "", "purpose": "lookup"}]}, {"intent": "invented"}]
)
def test_invalid_plan_no_calls(change):
    service = AsyncMock()
    with pytest.raises(ValidationError):
        asyncio.run(search({**understand("Trích dẫn: thuế"), **change}, service, options("bm25")))
    service.search.assert_not_called()


@pytest.mark.parametrize("mode", MODES)
def test_unit_bootstrap_preserves_backend_configuration(mode):
    dense = Path("provisioned-e5") if mode != "bm25" else None
    hybrid = HybridConfig(rrf_k=41, bm25_candidates=3, dense_candidates=4)
    rerank = RerankConfig(enabled=mode == "rerank", model_path=Path("provisioned-cross-encoder"))
    with patch("src.query_search_bootstrap.create_retrieval_service", return_value=object()) as factory:
        pipeline = create_query_search(
            SupabaseSettings(),
            options(mode),
            dense_model_path=dense,
            hybrid_config=hybrid,
            rerank_config=rerank,
            timeout_seconds=30,
        )
    assert pipeline.options == options(mode)
    assert factory.call_args.kwargs == {
        "dense_model_path": dense,
        "hybrid_config": hybrid,
        "rerank_config": rerank,
        "timeout_seconds": 30,
    }


@pytest.mark.parametrize("mode", MODES)
def test_offline_real_dispatch_direct_parity_and_all_metadata(mode):
    if mode == "rerank":
        service, deps = configured()
        sparse, dense, encoder = deps[:3]
    else:
        service, sparse, dense, encoder, *_ = hybrid_service()
    recorder = RecordingService(service)
    plan = understand("Trích dẫn: thuế")
    before = deepcopy(plan)
    opts = options(mode)
    state = asyncio.run(search(plan, recorder, opts))
    assert plan == before and state["status"] == "COMPLETED"
    response = state["responses"][0]
    assert response is recorder.responses[0]  # Preserves subclass, every evidence field and warning.
    assert state["requests"] == tuple(recorder.requests)
    assert response.status == "OK"
    baseline = asyncio.run(service.search(state["requests"][0]))
    assert response.model_dump(exclude={"request_id", "retrieved_at"}) == baseline.model_dump(
        exclude={"request_id", "retrieved_at"}
    )
    assert [item.rank for item in response.evidence] == [1, 2]
    for item in response.evidence:
        assert item.source_document_id.int == 30 and item.document_structure_id.int == 40
        assert item.hash_check == "MATCHED_STORED"
        assert item.source_url is None and item.source_snapshot_id is None
        assert item.content_representation == "retrieval_chunk_content"
        assert item.chunk_metadata["breadcrumb"] == "Demo > Điều 1"
    assert response.warnings  # Missing temporal/source metadata stays visible.
    if mode == "bm25":
        assert sparse.requests and dense.calls == encoder.calls == []
        assert all(item.score_kind == "BM25" for item in response.evidence)
    elif mode == "dense":
        assert dense.calls and encoder.calls and sparse.requests == []
        assert all(len(req.query_embedding) == 384 for req in dense.calls)
    else:
        assert isinstance(response, HybridRetrievalResponse)
        assert [b.backend for b in response.fusion.branches] == ["bm25", "dense"]
        assert sparse.requests[0].top_k == dense.calls[0].top_k == 20
        assert response.fusion.failure_policy == "STRICT"
        assert all(item.score_kind == "RRF" for item in response.evidence)
        if mode == "rerank":
            assert isinstance(response, RerankedHybridRetrievalResponse)
            assert response.reranking.status == "APPLIED"
            assert service._pair_scorer.calls


@pytest.mark.parametrize("mode", MODES)
def test_offline_no_match_all_modes(mode):
    service, *_ = (
        configured(sparse_hits=(), dense_hits=()) if mode == "rerank" else hybrid_service(sparse_hits=(), dense_hits=())
    )
    result = asyncio.run(QuerySearch(service, options(mode)).search("Trích dẫn: thuế"))
    assert result["responses"][0].status == "NO_MATCH"
    assert result["responses"][0].evidence == ()


@pytest.mark.parametrize("backend", ["bm25", "dense"])
def test_offline_hybrid_failure_is_not_partial_success(backend):
    from src.applications.tillegal.retrieval.retriever import RetrievalError

    service, sparse, dense, *_ = hybrid_service(
        sparse_error=DatabaseRepositoryError("private") if backend == "bm25" else None,
        dense_error=RetrievalError("private") if backend == "dense" else None,
    )
    result = asyncio.run(QuerySearch(service, options("hybrid")).search("thuế; nghỉ phép"))
    response = result["responses"][0]
    assert result["status"] == "FAILED" and len(result["responses"]) == 1
    assert response.error.category == "DATABASE_FAILURE"
    assert response.evidence == response.fusion.ranking == ()
    assert "private" not in response.model_dump_json()
    if backend == "bm25":
        assert dense.calls == []
    assert sparse.requests


def test_offline_missing_e5_no_vector_call(tmp_path):
    service, _, dense, *_ = hybrid_service(encoder=E5QueryEncoder(tmp_path / "missing"))
    result = asyncio.run(QuerySearch(service, options("dense")).search("Trích dẫn: thuế"))
    assert result["responses"][0].error.code == "MODEL_NOT_PROVISIONED"
    assert dense.calls == []


def test_offline_missing_dense_index_no_model_call():
    service, _, dense, encoder, _, indexes, _ = hybrid_service()
    indexes.before = indexes.after = None
    result = asyncio.run(QuerySearch(service, options("dense")).search("Trích dẫn: thuế"))
    assert result["responses"][0].error.code == "INDEX_NOT_FOUND"
    assert dense.calls == encoder.calls == []


def test_offline_missing_reranker_fallback_explicit(tmp_path):
    scorer = LocalCrossEncoder(RerankConfig(enabled=True, model_path=tmp_path / "missing"))
    service, _ = configured(scorer)
    result = asyncio.run(QuerySearch(service, options("rerank")).search("Trích dẫn: thuế"))
    response = result["responses"][0]
    assert result["status"] == "COMPLETED" and response.status == "OK"
    assert response.reranking.status == "FALLBACK"
    assert response.reranking.failure_code == "MODEL_NOT_PROVISIONED"
    assert "RERANKING_FALLBACK" in [w.code for w in response.warnings]
    assert all(c.cross_encoder_score is None for c in response.reranking.candidates)


@pytest.mark.parametrize("mode,code", [("dense", "RETRIEVAL_TIMEOUT"), ("hybrid", "HYBRID_TIMEOUT")])
def test_offline_total_deadline(mode, code):
    class SlowEncoder(FakeEncoder):
        async def encode_query(self, query):
            await asyncio.sleep(1)
            return self.vector

    service, *_ = hybrid_service(encoder=SlowEncoder(), timeout=0.01)
    result = asyncio.run(QuerySearch(service, options(mode)).search("Trích dẫn: thuế"))
    assert result["status"] == "FAILED"
    assert result["responses"][0].error.code == code
    assert result["responses"][0].evidence == ()


def test_no_legacy_references_in_application_path():
    import src.applications.tillegal.agents.search.agent as agent
    import src.query_search_bootstrap as bootstrap
    import src.retrieval_bootstrap as retrieval_bootstrap

    for module in [agent, bootstrap, retrieval_bootstrap]:
        assert "ai_core" not in inspect.getsource(module)
