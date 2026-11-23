# Actual commands, results and limits

Working directory: D:/DOWNLOAD/tillegal-ai/tillegal-ai-main. Python3.12.16. Unit/regression uses mocked model/data ports. Starting full suite actually reran:622 PASS. Final checks below were executed, not inferred from historical reports.

### PASS

```powershell
.\.venv\Scripts\python.exe -m ruff check --fix --no-cache src/applications/tillegal/agents/query src/applications/tillegal/agents/search scripts/validate_query_semantics.py scripts/evaluate_query_relevance.py tests/unit/applications/tillegal/test_semantic_correctness.py tests/unit/applications/tillegal/test_relevance_labels.py tests/unit/applications/tillegal/test_query_hardening.py tests/unit/applications/tillegal/test_query_search_semantic.py
```

```text
All checks passed!
```

### PASS

```powershell
.\.venv\Scripts\python.exe -m ruff format src/applications/tillegal/agents/query src/applications/tillegal/agents/search scripts/validate_query_semantics.py scripts/evaluate_query_relevance.py tests/unit/applications/tillegal/test_semantic_correctness.py tests/unit/applications/tillegal/test_relevance_labels.py tests/unit/applications/tillegal/test_query_hardening.py tests/unit/applications/tillegal/test_query_search_semantic.py
```

```text
17 files left unchanged
```

### PASS

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/applications/tillegal tests/graph/test_query_search_workflow.py -q -p no:cacheprovider -o faulthandler_timeout=30
```

```text
........................................................................ [ 12%]
........................................................................ [ 25%]
........................................................................ [ 38%]
........................................................................ [ 50%]
........................................................................ [ 63%]
........................................................................ [ 76%]
........................................................................ [ 88%]
................................................................         [100%]
568 passed in 11.94s
```

### PASS

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider -o faulthandler_timeout=30
```

```text
........................................................................ [ 10%]
........................................................................ [ 21%]
........................................................................ [ 32%]
........................................................................ [ 43%]
........................................................................ [ 54%]
........................................................................ [ 65%]
........................................................................ [ 76%]
........................................................................ [ 87%]
........................................................................ [ 98%]
.........                                                                [100%]
657 passed in 14.25s
```

### PASS

```powershell
.\.venv\Scripts\python.exe -m ruff check --no-cache src/applications/tillegal/agents/query src/applications/tillegal/agents/search scripts/validate_query_semantics.py scripts/evaluate_query_relevance.py tests/unit/applications/tillegal/test_semantic_correctness.py tests/unit/applications/tillegal/test_relevance_labels.py tests/unit/applications/tillegal/test_query_hardening.py tests/unit/applications/tillegal/test_query_search_semantic.py
```

```text
All checks passed!
```

### PASS

```powershell
.\.venv\Scripts\python.exe -m ruff format --check src/applications/tillegal/agents/query src/applications/tillegal/agents/search scripts/validate_query_semantics.py scripts/evaluate_query_relevance.py tests/unit/applications/tillegal/test_semantic_correctness.py tests/unit/applications/tillegal/test_relevance_labels.py tests/unit/applications/tillegal/test_query_hardening.py tests/unit/applications/tillegal/test_query_search_semantic.py
```

```text
17 files already formatted
```

## Live Gemini and read-only retrieval

```powershell
$env:PYTHONUTF8='1'
$env:LITELLM_LOCAL_MODEL_COST_MAP='True'
.\.venv\Scripts\python.exe -m scripts.validate_query_semantics --mode gemini --max-requests 20 --output evaluation/query_search/semantic_v2/gemini.json
.\.venv\Scripts\python.exe -m scripts.validate_query_semantics --mode gemini --label bounded-resume --max-requests 5 --ids Q037,Q040,Q042,Q043,Q044 --output evaluation/query_search/semantic_v2/gemini-resume.json
.\.venv\Scripts\python.exe -m scripts.validate_query_semantics --mode gemini --label variability --max-requests 2 --ids Q007,Q025 --output evaluation/query_search/semantic_v2/variability.json
.\.venv\Scripts\python.exe -m scripts.evaluate_query_relevance --gemini evaluation/query_search/semantic_v2/matched.json
.\.venv\Scripts\python.exe -m scripts.evaluate_query_search_retrieval --plans evaluation/query_search/semantic_v2/matched.json --output evaluation/query_search/semantic_v2/source_identity_real.json --as-of-date 2026-11-23 --bm25-only --case-ids Q022
```

Raw files are preserved; choose fresh output paths and do not bypass the task-wide25-request ledger. No API key/header is printed or persisted.

Main Gemini batch:16 rows before429,14 accepted,14 API calls. Resume:5 rows accepted,5 API calls (Q037 is documented retry). Variability:2 rows accepted,2 API calls. Primary matched15 completes after resume; Q007 still rejected. Final source/time-role processing uses saved real responses; no hidden deterministic fallback.

Relevance collection:15/16 variant/case Search runs completed, one blocked by Query;57 query/chunk rows. Same observed BM25 index signature, read-only access. Hash/provenance/dedup checks pass; irrelevant evidence is not called legally correct. The extra Q022 probe confirms the new source-identity warning on real corpus data.

Initial development failures were logged: old exact-key/citation-rejection tests needed intentional updates; the new relative-reference enum was initially missing; a date object initially broke JSON-style expectations, corrected to a calendar-validated ISO string. Those failures were not bypassed. Ruff long-line/import findings were corrected by scoped formatting/fixes.

No real Dense/Hybrid/rerank execution was repeated in this relevance phase: they remain unchanged, earlier real artifacts are historical, and relevant integration regressions passed. No model downloads, DB writes, schema migrations, graph changes, commit/push/PR. Credential scan/protected-hash review are recorded in SEMANTIC_V2_REVIEW.md.

Final test utility change: a fail-closed budget preflight is covered by a mock test. Final counts are568 focused and657 full-suite PASS. Offline `--mode summarize` was executed successfully after adding it; no provider call occurred. No production code changed after the final full-suite run.
