# Gemini test results — 2026-11-23

Working directory: `D:/DOWNLOAD/tillegal-ai/tillegal-ai-main`. Python 3.12.16, pytest 8.4.2, LiteLLM 1.106.4. All results below are observed executions, not proposed commands.

## Mocked unit and regression checks

| Exact command | Result | Count | Execution |
|---|---|---:|---|
| `.\.venv\Scripts\python.exe -m pytest tests/unit/applications/tillegal/test_gemini_query.py -q -p no:cacheprovider` | PASS | 37 | Mocked SDK responses, real adapter/planner/factory/Search interfaces |
| `.\.venv\Scripts\python.exe -m pytest tests/unit/applications/tillegal/test_gemini_query.py tests/unit/applications/tillegal/test_query_search_semantic.py tests/unit/applications/tillegal/test_query_search.py tests/unit/applications/tillegal/test_query_hardening.py tests/unit/applications/tillegal/test_query_search_multimode.py tests/graph/test_query_search_workflow.py -q -p no:cacheprovider -o faulthandler_timeout=30` | PASS in 2.90s | 209 | Mocked providers/ports; real Query/Search, RetrievalService and graph/runtime |
| `.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider -o faulthandler_timeout=30` | PASS in 7.47s | 612 | Full repository suite; no live Gemini calls |
| `.\.venv\Scripts\python.exe -m ruff check src/framework/llm/providers/gemini_adapter.py src/applications/tillegal/agents/query/gemini.py src/query_search_bootstrap.py scripts/verify_gemini_query.py tests/unit/applications/tillegal/test_gemini_query.py` | PASS | N/A | Static lint |
| `.\.venv\Scripts\python.exe -m ruff format --check src/framework/llm/providers/gemini_adapter.py src/applications/tillegal/agents/query/gemini.py src/query_search_bootstrap.py scripts/verify_gemini_query.py tests/unit/applications/tillegal/test_gemini_query.py` | PASS, 5 files formatted | N/A | Static format |

Regression environment: `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `LITELLM_LOCAL_MODEL_COST_MAP=True`. Existing placeholder test files still do not provide executable integration coverage.

Initial lint found long lines/import ordering and an intentionally SDK-named `Timeout` exception class in a test. Formatting and replacing the test class declaration with `type("Timeout", (Exception,), {})` resolved the findings without suppressions. The final lint result above is clean. No failing unit/regression tests were observed.

## Live API checks

See [GEMINI_LIVE_RESULTS.json](GEMINI_LIVE_RESULTS.json) and [GEMINI.md](GEMINI.md). These are **live Gemini**, not mocked responses. API key/headers were not printed or saved.

1. `GET https://generativelanguage.googleapis.com/v1beta/models?pageSize=1000` with the existing key: PASS, HTTP 200; selected model advertises generateContent.
2. `.\.venv\Scripts\python.exe -m scripts.verify_gemini_query --mode gemini --smoke-test` without the local cost map flag: FAIL, exit 1, `GEMINI_TIMEOUT`, 33,212.32 ms. Cold SDK startup/warnings were observed; this does not prove an API outage.
3. Same smoke command with `PYTHONUTF8=1` and `LITELLM_LOCAL_MODEL_COST_MAP=True`: PASS, exit 0, `{"ok": true}`, 6,341.89 ms.
4. `.\.venv\Scripts\python.exe -m scripts.verify_gemini_query --mode gemini --search-backend fixture` with those environment flags, after moving SDK import off the event loop/removing deprecated sampling: PASS, exit 0, 6,867.84 ms. Actual semantic response passed guards/schema; Search consumed two subqueries; real RetrievalService returned NO_MATCH twice using fake ports.

The live legal-question model output has two relevant legal issues/search objectives and exact extractive facts. Missing-information output includes a redundant contract-type question. These observations are one-case functional evidence, not a measured legal-understanding accuracy score.

NOT RUN: live Supabase/corpus retrieval, Vietnamese evaluation dataset/recall metrics, answer generation, citation verification, and Gemini integration into the untouched synchronous graph.
