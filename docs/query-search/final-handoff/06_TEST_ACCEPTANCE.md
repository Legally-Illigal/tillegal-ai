# Current test acceptance

All PASS statements below were rerun for THIS acceptance. Historical667-test report alone was not used as current verification. No tests added or production changed, so full count remains667. No fresh Gemini/Supabase call, dependency/model installation or full benchmark regeneration.

## Executed entry point

```powershell
.\.venv\Scripts\python.exe -m scripts.verify_query_search_handoff --output evaluation/query_search/final_acceptance/execution.json
```

PASS:5 controlled states and4 safe errors. Public create_query_search composition is patched only at backend construction; actual QuerySearch.search, planners and Search run. Historical Q004 raw response is returned by an injected completion and reprocessed by current SemanticQueryAgent; exact resulting plan matches saved matched.json. Retrieval backend reuses stored evidence as a fixture, not live search. Full JSON/schema and origin/hash preserved in execution.json.

## Exact checks

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/applications/tillegal tests/graph/test_query_search_workflow.py tests/contract -q -p no:cacheprovider -o faulthandler_timeout=30
```

Exit code 0

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
578 passed in 7.23s
```

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider -o faulthandler_timeout=30
```

Exit code 0

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
667 passed in 10.34s
```

```powershell
.\.venv\Scripts\python.exe -m ruff check --no-cache src/applications/tillegal/agents/query src/applications/tillegal/agents/search src/query_search_bootstrap.py src/retrieval_bootstrap.py src/framework/llm/providers/gemini_adapter.py scripts/verify_query_search_handoff.py scripts/validate_query_semantics.py scripts/investigate_query_relevance.py
```

Exit code 0

```text
All checks passed!
```

```powershell
.\.venv\Scripts\python.exe -m ruff format --check src/applications/tillegal/agents/query src/applications/tillegal/agents/search src/query_search_bootstrap.py src/retrieval_bootstrap.py src/framework/llm/providers/gemini_adapter.py scripts/verify_query_search_handoff.py scripts/validate_query_semantics.py scripts/investigate_query_relevance.py
```

Exit code 0

```text
17 files already formatted
```

## Coverage and what it does not establish

|Requirement|Current evidence|Origin|
|---|---|---|
|Query validation/metadata|test_query_hardening.py, test_semantic_correctness.py|Unit/controlled|
|Gemini adapter/config/factory|test_gemini_query.py, including test_semantic_factory_runs_adapter_query_search_and_real_retrieval|Mock completion and real service with fake ports; NOT remote Gemini|
|Structured JSON/fact/citation/time guards|test_query_search_semantic.py and controlled invalid_json scenario|Mocked + saved raw replay|
|Provider timeout/error/no fallback|test_gemini_query.py/test_query_search_semantic.py and2 controlled error scenarios|No intentional real outage|
|NO_MATCH/partial/skips|Controlled states + test_partial_failure_retains_evidence_and_explicit_skipped_queries|Injected fixture/fake ports|
|Native ranks/cache/version/source links|Semantic/multimode and graph compatibility tests|Actual implementation with controlled dependencies|
|Contracts|unit/applications/tillegal/retrieval/test_contracts.py, QueryPlan/SearchOptions tests|Executable schema tests; tests/contract files themselves are placeholders|
|Graph compatibility|tests/graph/test_query_search_workflow.py|Existing graph tested, not changed|
|Retrieval integration|unit/applications/tillegal retrieval service/hybrid/rerank suites and test_query_search_multimode.py|Real service composition with fake repository/model ports|
|Citation/time warnings|Controlled exact fixture/current native replay and existing tests|No authoritative law validation|
|Review/raw preservation|test_relevance_investigation.py and test_relevance_labels.py, inspected evaluator guards|Annotation/budget tests rerun; no full dataset regenerated|

Full-suite PASS does not imply live provider or database availability. FixtureBackend intentionally serves stored evidence regardless of query to test orchestration; its results cannot be used for relevance evaluation.

## Historical live evidence retained, not rerun

- [Gemini primary raw](../../../evaluation/query_search/semantic_v2/gemini.json) and [bounded continuation](../../../evaluation/query_search/semantic_v2/gemini-resume.json): original API failures and429 retained. Q007 primary grounding failure remains.
- [Final-code raw replay comparison](../../../evaluation/query_search/semantic_v2/matched.json): explicitly derived via deterministic replay, not fresh provider calls per row.
- [Real Supabase experiment](../../../evaluation/query_search/relevance_investigation/experiments.json):28 actual Search calls,2 literal aliases; BM25 plus3 each Dense/Hybrid/rerank.3/3 rerank APPLIED. No fresh network in acceptance.
- [Corpus inventory](../../../evaluation/query_search/relevance_investigation/coverage.json): observed58 visible sources/2609 chunks, limited to then-current credentials/time, not a new inventory or global absence claim.
- [Source snapshot comparison](SCOPE_REVIEW.md): unchanged production files support reuse of historical implementation evidence; no assertion of current external service uptime.

## Independent schema probes

[contract_probes.json](../../../evaluation/query_search/final_acceptance/contract_probes.json): demonstrates extra-ignore in QueryPlan and oversized end offset accepted for a manually constructed suffix reference. Nonblocking standard-path limitation documented in04/07; no production fix or hidden test relaxation.

Historical counts/statuses were independently re-read and asserted in [evidence_reconciliation.json](../../../evaluation/query_search/final_acceptance/evidence_reconciliation.json); external uptime was not refreshed.
