# Semantic correctness/relevance: final review

Baseline captured before this task. Existing earlier work/documents preserved.

## Modified files

- `src/applications/tillegal/agents/query/agent.py`
- `src/applications/tillegal/agents/query/prompts.py`
- `src/applications/tillegal/agents/query/schemas.py`
- `src/applications/tillegal/agents/query/semantic.py`
- `src/applications/tillegal/agents/search/agent.py`
- `src/applications/tillegal/agents/search/schemas.py`
- `tests/unit/applications/tillegal/test_query_hardening.py`
- `tests/unit/applications/tillegal/test_query_search_semantic.py`

## New files

- `docs/query-search/09_SEMANTIC_FAILURE_ROOT_CAUSES.md`
- `docs/query-search/10_CITATION_TEMPORAL_DESIGN.md`
- `docs/query-search/11_ISSUE_DECOMPOSITION.md`
- `docs/query-search/12_RELEVANCE_EVALUATION.md`
- `docs/query-search/13_IMPLEMENTATION_CHANGES.md`
- `docs/query-search/14_FINAL_COMPARISON.md`
- `docs/query-search/15_FINAL_TEST_RESULTS.md`
- `docs/query-search/16_QUERY_SEARCH_STUDENT_GUIDE_VI.md`
- `docs/query-search/SEMANTIC_V2_CHANGES.patch`
- `docs/query-search/SEMANTIC_V2_REVIEW.md`
- `evaluation/query_search/semantic_v2/api_budget.json`
- `evaluation/query_search/semantic_v2/baseline_manifest.json`
- `evaluation/query_search/semantic_v2/checks.json`
- `evaluation/query_search/semantic_v2/deterministic.json`
- `evaluation/query_search/semantic_v2/gemini-resume.json`
- `evaluation/query_search/semantic_v2/gemini.json`
- `evaluation/query_search/semantic_v2/matched.json`
- `evaluation/query_search/semantic_v2/raw_replay.json`
- `evaluation/query_search/semantic_v2/relevance/REVIEW_QUEUE.md`
- `evaluation/query_search/semantic_v2/relevance/assistant_provisional_labels.json`
- `evaluation/query_search/semantic_v2/relevance/labels_template.json`
- `evaluation/query_search/semantic_v2/relevance/pool.json`
- `evaluation/query_search/semantic_v2/relevance/runs.json`
- `evaluation/query_search/semantic_v2/source_before.json`
- `evaluation/query_search/semantic_v2/source_identity_real.json`
- `evaluation/query_search/semantic_v2/summary.json`
- `evaluation/query_search/semantic_v2/variability.json`
- `scripts/evaluate_query_relevance.py`
- `scripts/validate_query_semantics.py`
- `src/applications/tillegal/agents/query/context.py`
- `tests/unit/applications/tillegal/test_relevance_labels.py`
- `tests/unit/applications/tillegal/test_semantic_correctness.py`

## Verified scope

- All original non-pycache files under src/scripts/tests/configs/docs/evaluation outside the8 explicit changes retain baseline SHA-256. No deletion.
- RetrievalService, BM25/Dense/RRF/Reranking, repositories, database schema/migrations, provider adapter/config/credentials, graph/handoff and unrelated agents are unchanged.
-45-case ground truth and scoring terms unchanged. Original API attempts and failures preserved; derived matched processing is explicitly replay.
-21 Gemini invocations under25 cap; one429 and bounded continuation documented; no implicit fallback or indefinite retry.
-57 review rows;0 human/expert labels;19 assistant-provisional rank-one judgments separate from unfilled human template. Expert metrics null.
-Starting622 tests PASS; final568 focused and657 full-suite tests PASS; scoped Ruff lint/format PASS. Budget preflight has a mock regression test.
-Real corpus comparison used identical BM25/options per case, same observed index identity; no database writes/model downloads. Extra real Q022 probe validates source-title identity warning.
-Credential value scan PASS. Markdown report links PASS. No Git metadata in target; no branch/HEAD invented, no commit/push/merge/PR.
-Source/test diff: SEMANTIC_V2_CHANGES.patch. All data/report artifacts listed above.
-Known limits: Q007 grounding variability, incomplete MI/issue coverage, heuristic cue/slot parsing, missing effective-date metadata and no expert relevance conclusions.
