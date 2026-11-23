# 21 — Implementation decision and regression

## Production decision

No Query, prompt, provider, Search, graph or retrieval production files changed in this task. Formulation affects ranks, but D failed to show consistent substantive improvement across cases. Stronger evidence points to scoped source-identity/coverage and temporal metadata limits. Alternatives considered: strip all facts, rewrite prompt, add topic threshold, force article-number filter, second LLM or iterative search. Rejected for unsupported benefit, loss of context/evidence, scope creep and/or resource cost. This follows the requested instruction to avoid cosmetic production changes.

## Actual new evaluation code

- `scripts/investigate_query_relevance.py`: fixed A/B/C/D schedule;28 Search calls,2 aliases; local-only sequential model initialization; read-only metadata pagination and bounded literal probes; full raw responses; native-rank/issue association audit;57-row human queue reuse;280 separate experimental review rows; offline reanalysis. No Gemini invocation.
- `tests/unit/applications/tillegal/test_relevance_investigation.py`:10 regressions detect identical-query variant confusion, provisional-label laundering, unresolved identity, native rank/score/chunk changes, issue reassociation and blocked-plan misrepresentation.

All human labels remain null. The assistant observations in docs are provisional; earlier19 provisional scores are retained separately and not copied into human templates. Null labels never become zero relevance. Native ranks and raw scores are preserved; RRF/BM25/cosine scores are not comparable relevance probabilities.

The draft evaluator's identical-query join ambiguity was corrected before final review. Initial derived human_review.initial_join.json is preserved and superseded. Original source data and prior657-test artifacts remain unchanged. Initial lint long-line findings were resolved by formatting; no failing test was bypassed.

## Executed checks

```powershell
.\.venv\Scripts\python.exe -m ruff check --no-cache scripts/investigate_query_relevance.py tests/unit/applications/tillegal/test_relevance_investigation.py
```

Exit code: 0

```text
All checks passed!
```

```powershell
.\.venv\Scripts\python.exe -m ruff format --check scripts/investigate_query_relevance.py tests/unit/applications/tillegal/test_relevance_investigation.py
```

Exit code: 0

```text
2 files already formatted
```

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/applications/tillegal tests/graph/test_query_search_workflow.py -q -p no:cacheprovider -o faulthandler_timeout=30
```

Exit code: 0

```text
........................................................................ [ 12%]
........................................................................ [ 24%]
........................................................................ [ 37%]
........................................................................ [ 49%]
........................................................................ [ 62%]
........................................................................ [ 74%]
........................................................................ [ 87%]
........................................................................ [ 99%]
..                                                                       [100%]
578 passed in 5.98s
```

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider -o faulthandler_timeout=30
```

Exit code: 0

```text
........................................................................ [ 10%]
........................................................................ [ 21%]
........................................................................ [ 32%]
........................................................................ [ 43%]
........................................................................ [ 53%]
........................................................................ [ 64%]
........................................................................ [ 75%]
........................................................................ [ 86%]
........................................................................ [ 97%]
...................                                                      [100%]
667 passed in 7.17s
```

Offline reanalysis now refuses to overwrite either human_review.json or experimental_review.json when labels/reviewer/reason are filled; two additional regressions verify this protection.

Final:578 focused and667 full-suite PASS; scoped Ruff lint/format PASS.657→667 adds10 meaningful evaluator regressions. Full suite includes existing partial-failure/version/JSON/handoff/provider tests. No production source changed after tests. No fresh Gemini call or induced real failure was required.

## Exact resource and experiment status

28 actual Search calls succeeded,30 schedule rows include2 literal reuses.3/3 Dense,3/3 Hybrid,3/3 Hybrid+rerank completed;3 rerank APPLIED.19 actual BM25 calls.0 new Gemini calls. No model downloads; existing E5/CE checkpoints initialized separately. Preliminary metadata reads plus bounded metadata/literal probes are additional read-only database operations;28 is NOT a count of all HTTP/RPC requests.

Repro commands and fixed options are in18_QUERY_FORMULATION_EXPERIMENTS.md. Final file inventory/protected hashes are in RELEVANCE_INVESTIGATION_REVIEW.md. No Git metadata, branch or HEAD invented; no commit/push/merge/PR.
