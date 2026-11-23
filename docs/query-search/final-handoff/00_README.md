# Final Query/Search technical handoff

Acceptance date:2026-11-23. Project: `D:/DOWNLOAD/tillegal-ai/tillegal-ai-main`.

**Verdict: READY WITH LIMITATIONS for technical handoff of BOTH Query Agent and Search Agent.** This is not acceptance of complete legal-answer accuracy, expert relevance, corpus sufficiency or historical applicability.

No production change was necessary or made. Current controlled execution and rerun tests validate the existing entry point; prior real-provider/Supabase evidence is explicitly historical.0 new Gemini calls,0 new Supabase calls, no dependencies/models installed.578 focused tests and667 full tests passed; Ruff lint/format passed17 files. `tests/contract/` currently contains placeholders: real executable contract coverage is in unit/applications/tillegal/retrieval/test_contracts.py and Query/Search/graph tests.

## Reading order

1. [Architecture](01_FINAL_ARCHITECTURE.md): actual functions, ownership and execution order.
2. [Query internals](02_QUERY_AGENT_INTERNALS.md) and [Search internals](03_SEARCH_AGENT_INTERNALS.md).
3. [Public contracts](04_INPUT_OUTPUT_CONTRACTS.md): required/nullable/defaults/trust boundaries and executed JSON examples.
4. [Integration guide](05_INTEGRATION_GUIDE.md): executable fixture example, production configuration and downstream checklist.
5. [Current test evidence](06_TEST_ACCEPTANCE.md).
6. [Limitations/ownership](07_LIMITATIONS_AND_OWNERSHIP.md).
7. [Vietnamese technical defense](08_TECHNICAL_DEFENSE_VI.md).
8. [Team-lead handoff summary](09_HANDOFF_SUMMARY.md).

## Quick offline verification

From project root, with the existing Python3.12+ venv:

```powershell
$env:PYTHONUTF8='1'
.\.venv\Scripts\python.exe -m scripts.verify_query_search_handoff --output evaluation/query_search/final_acceptance/LOCAL_RECHECK.json
```

Use a fresh filename. This exercises QuerySearch with injected fixture evidence, replays one saved raw Gemini response and checks errors/JSON schemas. It neither searches Supabase nor calls Gemini. [Delivered execution artifact](../../../evaluation/query_search/final_acceptance/execution.json) already records a successful run.

## Evidence levels

- CURRENT CONTROLLED: acceptance fixture/replay, source/schema probes and rerun tests.
- HISTORICAL LIVE GEMINI: semantic_v2/gemini.json and gemini-resume.json; no fresh provider verification this phase.
- HISTORICAL LIVE SUPABASE: relevance_investigation/experiments.json contains28 Search invocations and2 aliases,4 modes on3 matched queries.
- PRELIMINARY RELEVANCE: assistant observations, not expert labels. Human review labels remain null.

Full experiment evidence is linked, not copied into this directory. [Scope/inventory](SCOPE_REVIEW.md) confirms original files unchanged; no commit/push/merge/rebase/PR. Target lacks Git metadata, branch/HEAD unknown.
