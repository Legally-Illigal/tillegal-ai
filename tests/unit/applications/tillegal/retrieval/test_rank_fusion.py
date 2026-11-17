import hashlib
from uuid import UUID

import pytest
from pydantic import ValidationError

from src.applications.tillegal.retrieval.errors import RetrievalServiceError
from src.applications.tillegal.retrieval.hybrid_models import HybridConfig
from src.applications.tillegal.retrieval.rank_fusion import reciprocal_rank_fusion
from tests.unit.applications.tillegal.retrieval.test_contracts import evidence


def candidate(cid, rank, backend="bm25", score=1.0, **changes):
    content = changes.pop("content", f"Demo chunk {cid}")
    return evidence(
        retrieval_chunk_id=UUID(int=cid),
        rank=rank,
        retrieval_method=backend,
        score_kind="BM25" if backend == "bm25" else "COSINE_SIMILARITY",
        raw_score=score,
        content=content,
        content_sha256=hashlib.sha256(content.encode()).hexdigest(),
        **changes,
    )


def test_hand_calculated_rrf_and_original_scores():
    bm25 = (candidate(1, 1, score=100), candidate(2, 2, score=3))
    dense = (candidate(2, 1, "dense", 0.85), candidate(3, 2, "dense", 0.8))
    result = reciprocal_rank_fusion(bm25, dense)
    assert [item.retrieval_chunk_id.int for item in result.evidence] == [2, 1, 3]
    assert [item.rank for item in result.evidence] == [1, 2, 3]
    assert [item.raw_score for item in result.evidence] == pytest.approx([1 / 62 + 1 / 61, 1 / 61, 1 / 62])
    assert all(e.score_kind == "RRF" and e.retrieval_method == "hybrid" for e in result.evidence)
    contributions = result.ranking[0].contributions
    assert [(c.backend, c.rank, c.raw_score, c.score_kind) for c in contributions] == [
        ("bm25", 2, 3, "BM25"),
        ("dense", 1, 0.85, "COSINE_SIMILARITY"),
    ]
    assert result.evidence[0].chunk_metadata == bm25[1].chunk_metadata
    assert result.evidence[0].source_metadata == bm25[1].source_metadata


def test_tie_breaking_uuid_not_input_order_or_raw_score():
    result = reciprocal_rank_fusion((candidate(9, 1, score=100),), (candidate(1, 1, "dense", -0.5),))
    assert [e.retrieval_chunk_id.int for e in result.evidence] == [1, 9]
    assert (
        reciprocal_rank_fusion((candidate(9, 1),), (candidate(1, 1, "dense"),), top_k=1)
        .evidence[0]
        .retrieval_chunk_id.int
        == 1
    )


def test_different_ids_same_text_are_not_merged():
    result = reciprocal_rank_fusion((candidate(1, 1, content="same"),), (candidate(2, 1, "dense", content="same"),))
    assert len(result.evidence) == 2


@pytest.mark.parametrize("backend", ["bm25", "dense"])
def test_one_branch_empty_is_valid(backend):
    one = (candidate(1, 1, backend, score=-0.1),)
    result = reciprocal_rank_fusion(one if backend == "bm25" else (), one if backend == "dense" else ())
    assert result.evidence[0].raw_score == pytest.approx(1 / 61)
    assert result.ranking[0].contributions[0].raw_score == -0.1


def test_both_empty():
    assert reciprocal_rank_fusion((), ()).evidence == ()


@pytest.mark.parametrize("kind", ["duplicate", "zero_rank", "gap", "nan", "payload_only", "bad_hash"])
def test_invalid_branch_candidates_fail(kind):
    item = candidate(1, 1)
    candidates = (item,)
    if kind == "duplicate":
        candidates = (item, item.model_copy(update={"rank": 2}))
    elif kind == "zero_rank":
        candidates = (item.model_copy(update={"rank": 0}),)
    elif kind == "gap":
        candidates = (item.model_copy(update={"rank": 2}),)
    elif kind == "nan":
        candidates = (item.model_copy(update={"raw_score": float("nan")}),)
    elif kind == "payload_only":
        candidates = (item.model_copy(update={"hash_check": "PAYLOAD_ONLY"}),)
    elif kind == "bad_hash":
        candidates = (item.model_copy(update={"content_sha256": "0" * 64}),)
    with pytest.raises(RetrievalServiceError):
        reciprocal_rank_fusion(candidates, ())


@pytest.mark.parametrize(
    "changes",
    [
        {"content": "changed"},
        {"title": "changed"},
        {"source_document_id": UUID(int=99)},
        {"chunk_metadata": {"other": True}},
        {"effective_from": "2026-11-11"},
    ],
)
def test_same_uuid_cross_backend_conflicts_fail(changes):
    with pytest.raises(RetrievalServiceError) as exc:
        reciprocal_rank_fusion((candidate(1, 1),), (candidate(1, 1, "dense", **changes),))
    assert exc.value.detail.code == "CROSS_BACKEND_EVIDENCE_CONFLICT"


@pytest.mark.parametrize(
    "changes",
    [{"rrf_k": 0}, {"rrf_k": True}, {"bm25_candidates": 51}, {"dense_candidates": 0}, {"allow_fallback": True}],
)
def test_config_validation(changes):
    with pytest.raises(ValidationError):
        HybridConfig(**changes)


@pytest.mark.parametrize("changes", [{"k": 0}, {"k": True}, {"top_k": 0}, {"top_k": 51}])
def test_pure_function_validates_limits(changes):
    with pytest.raises(ValueError):
        reciprocal_rank_fusion((), (), **changes)
