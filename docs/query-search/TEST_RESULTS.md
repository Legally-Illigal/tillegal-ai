# Test results — 2026-11-23

Working directory: `D:/DOWNLOAD/tillegal-ai/tillegal-ai-main`. Python 3.12.16 from the existing project .venv; pytest 8.4.2. Final commands run with `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`, outside the obsolete workspace sandbox. No real provider, database, dense model or reranker inference was requested.

## PASS

```powershell
.\.venv\Scripts\python.exe -m ruff check src/applications/tillegal/agents/query src/applications/tillegal/agents/search src/query_search_bootstrap.py tests/unit/applications/tillegal/test_query_hardening.py tests/unit/applications/tillegal/test_query_search_semantic.py
```

Exit code: 0. Test count: N/A (static check).

```text
All checks passed!
```

## PASS

```powershell
.\.venv\Scripts\python.exe -m ruff format --check src/applications/tillegal/agents/query src/applications/tillegal/agents/search src/query_search_bootstrap.py tests/unit/applications/tillegal/test_query_hardening.py tests/unit/applications/tillegal/test_query_search_semantic.py
```

Exit code: 0. Test count: N/A (static check).

```text
12 files already formatted
```

## PASS

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/applications/tillegal/test_query_search_semantic.py tests/unit/applications/tillegal/test_query_hardening.py tests/unit/applications/tillegal/test_query_search.py tests/unit/applications/tillegal/test_query_search_multimode.py tests/graph/test_query_search_workflow.py -q -p no:cacheprovider -o faulthandler_timeout=30
```

Exit code: 0. Tests: see exact pytest count below.

```text
........................................................................ [ 41%]
........................................................................ [ 83%]
............................                                             [100%]
172 passed in 2.70s
```

## PASS

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider -o faulthandler_timeout=30
```

Exit code: 0. Tests: see exact pytest count below.

```text
........................................................................ [ 12%]
........................................................................ [ 25%]
........................................................................ [ 37%]
........................................................................ [ 50%]
........................................................................ [ 62%]
........................................................................ [ 75%]
........................................................................ [ 87%]
.......................................................................  [100%]
575 passed in 7.01s
```

## Earlier checks and corrected failures

- BLOCKED/INTERRUPTED: initial sandbox baseline command `.\.venv\Scripts\python.exe -m pytest tests/unit/applications/tillegal/test_query_hardening.py tests/unit/applications/tillegal/test_query_search.py tests/unit/applications/tillegal/test_query_search_multimode.py tests/graph/test_query_search_workflow.py -q -p no:cacheprovider` printed 37 dots then hung; interrupted with Ctrl-C. It did not produce a completed baseline total. The chained `python -m ruff --version` was not reached.
- PASS: `.\.venv\Scripts\python.exe -m pytest tests/unit/applications/tillegal/test_query_search.py -x -vv -p no:cacheprovider -o faulthandler_timeout=20` outside sandbox: 12 passed in 1.33s, using real RetrievalService/fake read ports.
- FAIL, then corrected: `.\.venv\Scripts\python.exe -m pytest tests/unit/applications/tillegal/test_query_hardening.py -q -p no:cacheprovider`: 36 passed, 1 failed because the exact-key assertion described only the previous six-field plan. Explicitly extended that assertion to require all five new analysis fields and their deterministic defaults; retained all old assertions.
- FAIL, then corrected: initial scoped Ruff check reported import ordering; the next check found a 121-character test line. Scoped Ruff --fix/format resolved both. No unrelated files were formatted.
- PASS before final semantic hardening: focused Query/Search + graph command (same final focused list before seven added hardening cases and four review cases): 161 passed in 2.96s; full suite: 564 passed in 7.81s.
- PASS after semantic hardening: `.\.venv\Scripts\python.exe -m pytest tests/unit/applications/tillegal/test_query_search_semantic.py -q -p no:cacheprovider`: 48 passed in 1.28s.

## Execution scope

Model responses are mocked at StructuredCompletion. Fake ports provide controlled database rows/hits, query embeddings and reranker scores. Existing multimode tests exercise the real RetrievalService including hybrid/rerank code paths; no models are downloaded. Existing graph/runtime tests exercise cancellation, handoff validation and error propagation. Some repository test files (including the LiteLLM integration file) are docstring placeholders and contain no executable tests; a green full suite is not proof those integrations work.

NOT RUN: live model/provider quality evaluation (no working shared provider integration), live Supabase/database integration, retrieval relevance/recall on a legal corpus, legal-answer/citation accuracy, and graph semantic-LLM integration (outside scope). No measured legal accuracy is claimed.

Final diff review added four regression cases for employer termination, negated employee intent, dismissal and preserving other question parts. The final 172/575 PASS results above include these cases. Documentation-only corrections after that run update original line references and review artifacts; no executable code changed afterward.
