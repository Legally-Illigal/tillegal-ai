# Judge native SearchState integration

Branch: feature/judge-native-search-adapter; base origin/main cba277c.
Independent synchronous Python API only. No graph/state/startup/API or Summary changes.

## API

```python
from src.applications.tillegal.agents.judge.adapter import adapt_search, evaluate_search
from src.applications.tillegal.agents.judge.agent import JudgeAgent, FixtureJudgeProvider

# search_state: existing native SearchState; options: trusted SearchOptions.
# History and round count must describe actual caller execution.
context = dict(request_id="req-001", options=options,
               search_rounds_completed=1, query_history=query_ids,
               query_text_history=executed_query_texts)
adapted = adapt_search(search_state, **context)
# Explicit fixture: replay only, no semantic evaluation. Empty evidence can be
# evaluated without calling the provider. For nonempty evidence use a recorded,
# schema-valid response referring to adapted.issue_map/evidence_map IDs.
fixture = {
    "status": "ERROR", "issue_checks": [], "missing_items": [],
    "next_queries": [], "usable_evidence_ids": [],
    "explanation": "Mock replay, no semantic evaluation.",
    "error_code": "FIXTURE_ONLY",
}
judge = JudgeAgent(FixtureJudgeProvider(fixture))
result = evaluate_search(search_state, judge=judge, **context)
assert result.adapted == adapted
# result.judge_result remains the original Judge output contract.
```

## Boundary and policy

SearchState plus explicit trusted options/request ID/history is the only native
boundary. JudgeHandoff alone omits aggregation/occurrences; V2 is not implicitly
connected to graph. No search/model/database is called by adapt_search. It checks
native aggregate consistency by reusing pure Search._finish, without searching.
Caller supplies already grounded internal plans; validation does not certify an
untrusted external plan. No automatic issue extraction or empty-issue fallback.

COMPLETE, including NO_MATCH, is accepted. FAILED/PARTIAL/clarification is rejected
with JudgeAdapterError and detached native_context (errors/warnings/skipped queries,
responses and completeness). This is not a legal insufficiency verdict. Missing
issues raises JUDGE_ISSUES_REQUIRED. No evidence on complete search takes the core
Judge empty fast path: INSUFFICIENT/coverage none and zero provider calls.

IDs use SHA-256(request scope + issue index/text or exact source payload excluding
query-local rank/score/method). Same chunk with different source/content/version
payload gets different IDs; multiple occurrences stay linked. Source/structure/
snapshot IDs, raw metadata, offsets and per-query scores remain in evidence_map and
native_context. Query-to-issue intent links also enter validated input context;
they do not prove semantic support. V2 IDs are not reused by this native-only API.
Keep the returned carrier throughout later stages rather than adapting with a new
request ID. Frozen carriers contain mutable dictionaries; callers must not mutate
them after evaluation. All payloads are detached copies.

Native content is retrieval_chunk_content, not an exact verified quote. Legal
version, temporal validity and exact citation remain null/UNKNOWN. No fabricated
article/clause/point/locator/context groups/omissions. An empty legacy groups list
means not provided, not complete context. Hash match is traceability only.

## Provider

JudgeProvider.generate(messages) -> JSON string is dependency-injected. No concrete
live transport was imported; Query Gemini is not automatically compatible. Custom
providers must use Judge prompts and OUTPUT_SCHEMA, enforce I/O timeout and return
one JSON object. structured_output providers must declare OUTPUT_SCHEMA or its
anthropic_output_schema projection. Local full validation always runs. Fixture
replays explicit data; it never judges meaning. No paid/live calls were made.
Synchronous calls cannot be forcibly cancelled; no retry/loop is implemented.
Limits: default 100000 input bytes including schema/prompt; 24000 output characters.
Input limit before empty fast path; duplicate JSON keys/nonfinite constants rejected.

## Implementation provenance

Selected original ai_core Judge core/contracts, matching the old integration port;
imports changed to local support primitives rather than pulling legacy ingestion,
retrieval/generation/providers. prompts.py extracts the original prompt and adds
native-representation cautions. schemas.py preserves output and relational checks,
adds only native input context links/diagnostics. adapter.py is new.

## Validation

python -m pytest -q: 793 passed (18.51s), including 17 new boundary tests.
Focused Query/Search, V2, graph + Judge: 176 passed (5.47s).
All offline/mock/fake-port tests, not legal quality or live validation.
No LangGraph/orchestrator/Summary/Verify/loop/startup/API change. Future orchestration
must preserve request scope, maps, native context and actual history; Summary needs
its own representation-aware input contract (not implemented here).
