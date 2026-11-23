"""Offline regression checks for auditable review joins and native rank retention."""

import copy
import hashlib
import json

import pytest

from scripts.investigate_query_relevance import analyze, build_review, inspect_native


def fixtures():
    evidence = {
        "retrieval_chunk_id": "chunk",
        "content_sha256": "hash",
        "rank": 1,
        "raw_score": 2.0,
        "score_kind": "BM25",
        "source_metadata": {},
    }
    response = {"query": "same query", "mode": "bm25", "index": {}, "as_of_date": "2026-11-23", "evidence": [evidence]}
    occurrence = {"response_index": 0, "subquery_index": 0, "rank": 1, "raw_score": 2.0, "issue_indices": [0, 1]}
    run = {
        "id": "Q1",
        "variant": "deterministic",
        "responses": [response],
        "requests": [{"query": "same query"}],
        "plan": {"issues": ["loan", "guarantee"], "search_objectives": [{"query_index": 0, "issue_indices": [0, 1]}]},
        "evidence": [{"evidence": evidence, "occurrences": [occurrence]}],
        "checks": {},
        "warnings": [],
        "status": "COMPLETED",
    }
    other = copy.deepcopy(run)
    other["variant"] = "gemini"
    pool = {
        "rows": [
            {
                "case_id": "Q1",
                "query_index": 0,
                "rank": 1,
                "chunk_id": "chunk",
                "search_objective": "same query",
                "review_id": variant,
                "blind_variant_token": hashlib.sha256(variant.encode()).hexdigest()[:8],
            }
            for variant in ("deterministic", "gemini")
        ]
    }
    return pool, [run, other]


def test_identical_queries_preserve_each_variants_identity_and_multi_issue_links():
    pool, runs = fixtures()
    rows = build_review(pool, runs)["rows"]
    assert [row["query_source"] for row in rows] == ["deterministic", "gemini"]
    assert all(row["legal_issue"] == ["loan", "guarantee"] for row in rows)


def test_provisional_labels_cannot_become_human_review_labels():
    pool, runs = fixtures()
    pool["rows"][0].update(label=3, label_source="model_assisted_provisional", reviewer="assistant", reason="test")
    result = build_review(pool, runs)
    assert result["human_labels"] == 0 and result["expert_metrics"] is None
    assert all(row["label"] is None and row["reviewer"] is None and row["reason"] is None for row in result["rows"])


def test_unknown_variant_fails_instead_of_borrowing_another_plans_evidence():
    pool, runs = fixtures()
    pool["rows"][0]["blind_variant_token"] = "unknown"
    with pytest.raises(ValueError, match="exactly one"):
        build_review(pool, runs)


@pytest.mark.parametrize("changed", ["rank", "raw_score", "retrieval_chunk_id"])
def test_audit_detects_native_evidence_or_rank_changes(changed):
    _, runs = fixtures()
    run = runs[0]
    assert inspect_native(run)["all_native_occurrences_preserved"]
    run["evidence"][0]["evidence"] = copy.deepcopy(run["evidence"][0]["evidence"])
    if changed == "retrieval_chunk_id":
        run["evidence"][0]["evidence"][changed] = "different"
    else:
        run["evidence"][0]["occurrences"][0][changed] = 99
    assert not inspect_native(run)["all_native_occurrences_preserved"]


def test_audit_detects_issue_reassociation():
    _, runs = fixtures()
    run = runs[0]
    assert inspect_native(run)["explicit_issue_links_preserved"]
    run["evidence"][0]["occurrences"][0]["issue_indices"] = [1]
    assert not inspect_native(run)["explicit_issue_links_preserved"]


def test_failed_plan_remains_unauditable_not_successful_empty_search():
    assert inspect_native({"status": "BLOCKED_QUERY_PLAN"}) == {"status": "BLOCKED_QUERY_PLAN", "auditable": False}


@pytest.mark.parametrize("filename", ["human_review.json", "experimental_review.json"])
def test_reanalysis_preserves_reviewer_annotations(tmp_path, filename):
    path = tmp_path / filename
    content = json.dumps({"rows": [{"label": 0, "reviewer": "human", "reason": "unrelated"}]})
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError, match="Preserve annotated"):
        analyze(tmp_path)
    assert path.read_text(encoding="utf-8") == content
