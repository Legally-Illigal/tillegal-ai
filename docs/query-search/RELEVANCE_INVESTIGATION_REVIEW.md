# Relevance investigation final inventory

Project: D:/DOWNLOAD/tillegal-ai/tillegal-ai-main. Investigation2026-11-23.

## Scope verification

- 419 original files under src/scripts/tests/configs/docs/evaluation retain baseline SHA-256. No deletions or modifications to original files.
- No production Query/Search/prompt/provider/graph/retrieval/configuration changes. No corpus/schema/index writes or model downloads.
- New evaluation script plus10 new regression tests; final578 focused /667 full tests PASS; scoped Ruff lint/format PASS.
- 28 actual Search invocations,2 literal aliases,4 modes on3 matched queries,0 new Gemini calls. No expert ranking metrics.
- Complete observed58-row source metadata enumeration,2609 visible chunks; read-only source/literal probes retained. Scope limited to current credential visibility, no transaction snapshot.
- 57 reused human review rows +280 separate experiment rows; all labels null. Prior assistant-provisional labels stay separate and unchanged.
- Annotated JSON reviews are protected from offline reanalysis overwrites; raw outputs cannot be overwritten by a new live run.
- Superseded human_review.initial_join.json retained; use human_review.json/HUMAN_REVIEW_QUEUE.md. First draft join ambiguity was evaluator-only and regression-tested.
- Markdown links and exact credential-value scan PASS.
- Target has no Git repository metadata; branch/HEAD unavailable. No commit, push, merge or PR.

## Added files

- `docs/query-search/17_RELEVANCE_ROOT_CAUSE_AUDIT.md`
- `docs/query-search/18_QUERY_FORMULATION_EXPERIMENTS.md`
- `docs/query-search/19_CORPUS_COVERAGE_CHECK.md`
- `docs/query-search/20_SEARCH_BEHAVIOR_REVIEW.md`
- `docs/query-search/21_IMPLEMENTATION_AND_REGRESSION.md`
- `docs/query-search/22_HANDOFF_READINESS.md`
- `docs/query-search/23_STUDENT_TECHNICAL_GUIDE_VI.md`
- `docs/query-search/RELEVANCE_INVESTIGATION_REVIEW.md`
- `evaluation/query_search/relevance_investigation/HUMAN_REVIEW_QUEUE.md`
- `evaluation/query_search/relevance_investigation/case_audit.json`
- `evaluation/query_search/relevance_investigation/checks.json`
- `evaluation/query_search/relevance_investigation/checks_initial.json`
- `evaluation/query_search/relevance_investigation/coverage.json`
- `evaluation/query_search/relevance_investigation/coverage_after.json`
- `evaluation/query_search/relevance_investigation/coverage_probes.json`
- `evaluation/query_search/relevance_investigation/current_search_replay.json`
- `evaluation/query_search/relevance_investigation/experiment_summary.json`
- `evaluation/query_search/relevance_investigation/experimental_review.json`
- `evaluation/query_search/relevance_investigation/experiments.json`
- `evaluation/query_search/relevance_investigation/human_review.initial_join.json`
- `evaluation/query_search/relevance_investigation/human_review.json`
- `evaluation/query_search/relevance_investigation/saved_search_audit.json`
- `evaluation/query_search/relevance_investigation_baseline.json`
- `scripts/investigate_query_relevance.py`
- `tests/unit/applications/tillegal/test_relevance_investigation.py`
