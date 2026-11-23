# Quality validation: complete local change inventory

Comparison baseline captured before this task. The prior Query/Search and Gemini work was preserved.

## Modified existing files

- `src/applications/tillegal/agents/query/semantic.py`

## New files

- `docs/query-search/01_EVALUATION_DESIGN.md`
- `docs/query-search/02_BASELINE_RESULTS.md`
- `docs/query-search/03_REAL_RETRIEVAL_E2E.md`
- `docs/query-search/04_FAILURE_ANALYSIS.md`
- `docs/query-search/05_IMPROVEMENTS.md`
- `docs/query-search/06_BEFORE_AFTER.md`
- `docs/query-search/07_FINAL_VERIFICATION.md`
- `docs/query-search/08_STUDENT_GUIDE_VI.md`
- `docs/query-search/QUALITY_CHANGES.patch`
- `docs/query-search/QUALITY_REVIEW.md`
- `evaluation/query_search/baseline_manifest.json`
- `evaluation/query_search/cases.json`
- `evaluation/query_search/runs/checks.json`
- `evaluation/query_search/runs/commands.json`
- `evaluation/query_search/runs/deterministic-after.json`
- `evaluation/query_search/runs/deterministic-before.json`
- `evaluation/query_search/runs/gemini-after.json`
- `evaluation/query_search/runs/gemini-before.json`
- `evaluation/query_search/runs/gemini-final.json`
- `evaluation/query_search/runs/preflight.json`
- `evaluation/query_search/runs/retrieval-before-warm.json`
- `evaluation/query_search/runs/retrieval-before.json`
- `evaluation/query_search/runs/retrieval-candidate-warm.json`
- `evaluation/query_search/runs/retrieval-deterministic.json`
- `evaluation/query_search/runs/retrieval-final.json`
- `evaluation/query_search/runs/selection.json`
- `evaluation/query_search/schema.json`
- `evaluation/query_search/source_before.json`
- `evaluation/query_search/summary.json`
- `scripts/evaluate_query_search.py`
- `scripts/evaluate_query_search_retrieval.py`
- `scripts/summarize_query_search_evaluation.py`
- `tests/unit/applications/tillegal/test_query_quality.py`

## Scope checks

- Only semantic.py changes production behavior: narrow provider intent and single-objective user-reference preservation.
- Baseline prompt restored byte-for-byte; rejected candidate prompt survives in its run artifact.
- Search, Gemini provider adapter, config, RetrievalService, BM25/Dense/Hybrid/Reranking, integration repositories, schema/migrations, graph/handoff and unrelated agents retain baseline hashes.
- Database operations were existing read RPCs only. No data/index/policy/schema mutation or large model download.
- Model budget: exactly 37 attempted Gemini calls; one HTTP429 retained. Cost is not invented.
- 219 focused tests PASS; 622 full-suite tests PASS; scoped Ruff lint/format PASS. Summary utility independently linted/formatted/executed.
- No Git metadata in target; no branch/HEAD invented. No commit/push/merge/PR.
- Source/test/dataset diff is QUALITY_CHANGES.patch; every raw run/report is listed above.
- Known limits: no expert relevance labels, incomplete final-cohort model evaluation, persistent citation-as-time error, missing-info/decomposition weaknesses; no overall semantic/retrieval accuracy improvement claimed.
