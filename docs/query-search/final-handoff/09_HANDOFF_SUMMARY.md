# Technical handoff summary for team lead

**Query Agent: READY WITH LIMITATIONS. Search Agent: READY WITH LIMITATIONS.** Verdict is for technical integration, not complete legal-answer/relevance/applicability acceptance.

Entry point: src/query_search_bootstrap.py:create_query_search → QuerySearch.search(question). Default deterministic; semantic_mode="gemini" requires GOOGLE_API_KEY, Query profile and configured model (currently gemini-3.5-flash-lite). Dense/Hybrid need existing local E5; reranking is Hybrid plus local CE config. Caller explicitly supplies date/policies/top_k/mode.

Current verification:578 focused /667 full tests PASS; Ruff lint/format PASS17 files. Public factory and facade executed with fixture backend; original Gemini Q004 raw response replayed through current semantic validation.5 controlled states and4 error scenarios accepted.0 fresh provider/DB calls; historical28 real Search calls/4 modes and raw Gemini evidence retained and linked.

Contracts: QueryPlan, SearchOptions, SearchState, typed citation/time/objective and native evidence occurrence models. Legacy plans default empty metadata; unknown associations stay empty. COMPLETE means execution completed, not legal completeness. Facts may be allegations, issues are information needs, evidence is unverified retrieved material. Consumer must preserve warnings/partials/versions/provenance.

Remaining limits: Q007 grounding variability; narrow slot/domain rules; manual external-plan schema boundary (oversized suffix end can pass); quote-only title identity warning; incomplete effective dates; poor topical matches and no expert relevance labels. Historical visible corpus lacks stored45/2019 identity; broader absence unproven. No demonstrated Search orchestration or Retrieval algorithm defect.

No production changes, no graph/other-agent/corpus/retrieval edits, no dependency/model installation. New deliverables: final-handoff documentation, offline acceptance helper and acceptance evidence/manifest. See [README](00_README.md), [integration guide](05_INTEGRATION_GUIDE.md), [contracts](04_INPUT_OUTPUT_CONTRACTS.md), [ownership](07_LIMITATIONS_AND_OWNERSHIP.md), [scope inventory](SCOPE_REVIEW.md).

Target D:/DOWNLOAD/tillegal-ai/tillegal-ai-main has no Git metadata. Branch/HEAD unavailable. No commit/push/merge/rebase/PR; local handoff only. Nothing sent to team members automatically.
