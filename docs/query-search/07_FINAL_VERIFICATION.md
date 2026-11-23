# Final verification — local changes only

### PASS

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/applications/tillegal/test_query_quality.py tests/unit/applications/tillegal/test_gemini_query.py tests/unit/applications/tillegal/test_query_search_semantic.py tests/unit/applications/tillegal/test_query_search.py tests/unit/applications/tillegal/test_query_hardening.py tests/unit/applications/tillegal/test_query_search_multimode.py tests/graph/test_query_search_workflow.py -q -p no:cacheprovider -o faulthandler_timeout=30
```

```text
........................................................................ [ 32%]
........................................................................ [ 65%]
........................................................................ [ 98%]
...                                                                      [100%]
219 passed in 2.60s
```

### PASS

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider -o faulthandler_timeout=30
```

```text
........................................................................ [ 11%]
........................................................................ [ 23%]
........................................................................ [ 34%]
........................................................................ [ 46%]
........................................................................ [ 57%]
........................................................................ [ 69%]
........................................................................ [ 81%]
........................................................................ [ 92%]
..............................................                           [100%]
622 passed in 6.53s
```

### PASS

```powershell
.\.venv\Scripts\python.exe -m ruff check --no-cache scripts/evaluate_query_search.py scripts/evaluate_query_search_retrieval.py src/applications/tillegal/agents/query/semantic.py tests/unit/applications/tillegal/test_query_quality.py
```

```text
All checks passed!
```

### PASS

```powershell
.\.venv\Scripts\python.exe -m ruff format --check scripts/evaluate_query_search.py scripts/evaluate_query_search_retrieval.py src/applications/tillegal/agents/query/semantic.py tests/unit/applications/tillegal/test_query_quality.py
```

```text
4 files already formatted
```

All unit/regression runs use mocked providers and controlled ports; no Gemini/database calls in pytest. Live Gemini and real read-only retrieval executions are separate artifacts documented in 02/03/06. Initial scoped lint reported import/line-length findings, corrected by Ruff formatting. A read-only sandbox Ruff invocation also failed creating .ruff_cache; the final authorized invocation uses --no-cache and passes. An inspection command initially hit Windows cp1252 stdout; rerun with PYTHONUTF8=1 succeeded. Neither issue was a model accuracy failure.

Target has no .git: branch/HEAD and git diff are unavailable. Compare against `evaluation/query_search/baseline_manifest.json` and saved source snapshot; generated `QUALITY_REVIEW.md` lists every file and checks protected source hashes. Existing provider credentials/configuration, retrieval algorithms, other agents, graph, migrations and corpus remain unchanged. No commit/push/merge/PR.

Artifacts preserve failed API cases, omitted cases due 429, cold-start failures and non-promoted prompt. Cost/accuracy values are not fabricated. All semantic proxy results remain human-review-required. No actual legal answers are generated.

## Additional report-tool verification

The temporary prose-heavy report generator produced long-string lint findings and was replaced by a small saved-run summary utility; the prose reports are standalone Markdown artifacts. The shipped utility passed:

```powershell
.\.venv\Scripts\python.exe -m ruff check --no-cache scripts/summarize_query_search_evaluation.py
.\.venv\Scripts\python.exe -m ruff format --check scripts/summarize_query_search_evaluation.py
.\.venv\Scripts\python.exe -m scripts.summarize_query_search_evaluation
```

PASS: static lint, one file already formatted, summary recomputed without API calls. No runtime agent change occurred after the 622-test run. Exact evaluation/retrieval commands and nonsecret flags are in `evaluation/query_search/runs/commands.json`.

Credential-value scan of authored source/JSON/Markdown artifacts: PASS. Every original source/test/script/config/doc outside semantic.py retains its baseline SHA-256. No deletions. Full change list: [QUALITY_REVIEW.md](QUALITY_REVIEW.md); source/test/dataset diff: [QUALITY_CHANGES.patch](QUALITY_CHANGES.patch).
