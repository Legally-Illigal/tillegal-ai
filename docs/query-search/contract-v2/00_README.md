# Contract V2 foundation

Implemented2026-11-27, opt-in only. Readiness: **READY WITH LIMITATIONS**. V1 remains the default; no bootstrap, graph, provider profile, Gemini QA prompt/schema, Retrieval algorithms or other agents changed. Publication is on the feature branch only; no main merge or PR creation is part of this acceptance task.

New modules: `src/applications/tillegal/agents/contract_v2.py` and `pipeline_v2.py`. They wrap the existing QA planner and Search, rather than extending V1 required fields. Business qa/verify is separate from deterministic/gemini provider and bm25/dense/hybrid backend.

Read [approved decisions](01_APPROVED_DECISIONS.md), [schemas](02_SCHEMA_AND_VALIDATION.md), [compatibility](03_V1_V2_COMPATIBILITY.md), [targets](04_QUERY_TARGET_MAPPING.md), [evidence](05_SEARCH_EVIDENCE_MAPPING.md), [tests](06_TEST_RESULTS.md), [limits](07_LIMITATIONS_AND_NEXT_PHASE.md).

## Opt-in invocation

```python
from src.applications.tillegal.agents.contract_v2 import QueryContextV2, IdentityRegistry
from src.applications.tillegal.agents.pipeline_v2 import run_query_search_v2

# runner is the EXISTING create_query_search(...) instance with trusted SearchOptions.
context = QueryContextV2(request_id="request-from-backend", options=runner.options)
registry = IdentityRegistry(context)  # Retain this one registry for this request/revision.
result = await run_query_search_v2(runner, question, registry)
json_output = result.to_json()
```

Existing `await runner.search(question)` still returns unchanged V1 SearchState. Explicit lower entrypoints: `plan_query_v2(runner,question,registry)`, `envelope_from_plan(plan,registry)` for controlled metadata construction, `search_v2(runner,envelope,registry)`, `evidence_view(envelope,state,registry)` for an actual recorded SearchState. These helpers do not implement a Judge, Verification Agent, web/fetch or autonomous loop.

QA without new inputs uses the same Gemini structured completion and Search requests. Verify planning raises VERIFY_EXTRACTION_UNAVAILABLE before provider I/O. search_v2 with verify context returns status unavailable with no native state or retrieval I/O. A controlled verify envelope demonstrates contracts, not a working verifier.

[EXAMPLES.json](EXAMPLES.json) contains current input/output from real Python execution on in-memory read fixtures. It is not live Gemini/Supabase evidence. The illustrative claim there is an unverified user assertion, not a statement of law.
