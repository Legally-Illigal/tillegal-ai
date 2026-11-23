# Gemini scope review

This task builds on the existing redesign. Paths listed below are changes from the start of the Gemini task, not the earlier Query/Search redesign.

## Modified

- `configs/models.yaml`
- `docs/query-search/GUIDE_VI.md`
- `src/query_search_bootstrap.py`

## Added

- `docs/query-search/GEMINI.md`
- `docs/query-search/GEMINI_LIVE_RESULTS.json`
- `docs/query-search/GEMINI_TEST_RESULTS.md`
- `scripts/verify_gemini_query.py`
- `src/applications/tillegal/agents/query/gemini.py`
- `src/framework/llm/providers/gemini_adapter.py`
- `tests/unit/applications/tillegal/test_gemini_query.py`
- `docs/query-search/GEMINI_CHANGES.patch`
- `docs/query-search/GEMINI_REVIEW.md`

## Protected boundaries

All other original non-pycache files under src/tests/scripts/configs/docs match the pre-task SHA-256 manifest. In particular Query semantic.py, Query rules/schema/prompt, Search, RetrievalService, BM25/Dense/Hybrid/Reranking, graph/handoff and other agents are unchanged. No deletion, dependency or API credential change. Existing provider profile values and global OpenAI default are preserved; Query uses a dedicated Gemini profile.

Final checks: 37 Gemini unit tests PASS; 209 focused regression tests PASS; 612 full suite tests PASS; Ruff lint/format PASS. Live Gemini smoke and real Vietnamese question PASS; retrieval data in the live workflow is a declared empty fixture. Initial timeout is retained in the live results.

No Git repository metadata exists in the extracted target. No commit/push/merge/PR performed. Changes remain local.

[Integration guide](GEMINI.md), [live results](GEMINI_LIVE_RESULTS.json), [test commands/results](GEMINI_TEST_RESULTS.md), [complete diff](GEMINI_CHANGES.patch).
