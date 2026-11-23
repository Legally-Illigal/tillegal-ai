# Query/Search audit — 2026-11-23, before implementation

Target: `D:/DOWNLOAD/tillegal-ai/tillegal-ai-main`, the application under the user's designated `tillegal-ai` folder. This target is an extracted tree without `.git`: all three Git inspection commands (`git status --short`, `git branch --show-current`, `git rev-parse HEAD`) fail with `not a git repository`. The sibling `query-search-publish` worktree is clean on `codex/query-search-prototype` at `254f2c97e5d2d6091ebdca9960cae37fea94bb72`; that does **not** establish the extracted target's HEAD. Do not copy changes into that sibling.

## Verified behavior (line numbers refer to original sources)

| File | Functions / lines | Observed behavior and limitation |
|---|---|---|
| `src/applications/tillegal/agents/query/agent.py` | `Subquery`, `QueryPlan`, lines 15–26; `understand`, 29–95 | Validates type, length, control characters and NFC. Preserves original input. Splits on delimiters, appends fixed topics, caps at four. No facts, missing-information or legal issue fields. Compound employment example remains a sentence rather than two context-preserving objectives. |
| same | `understand`, 46–95 | Exact lookup recognizes only three prefixes; dates are calendar checked and citation years are deliberately excluded. These existing safeguards must be preserved. No legal answer or citation is generated. |
| `src/applications/tillegal/agents/search/agent.py` | `SearchOptions`, 13–28; `SearchState`, 31–35; `search`, 38–56 | Explicit trusted mode/date/policy/top-k. Native responses preserve metadata and query order already. Clarification skips calls. First classified failure stops calls, keeping prior results. No consolidated evidence/provenance view, duplicate call cache, skipped query list or completeness field. Unexpected exceptions propagate. |
| `src/query_search_bootstrap.py` | `QuerySearch.search`, 20–21; `create_query_search`, 24–43 | Calls `understand` then Search. Reuses retrieval composition; no model integration. |
| `src/applications/tillegal/state/legal_qa_state.py` | `JudgeHandoff.validate_context`, 44–64 | Requires positional plan/request/response correspondence and first-failure termination. Continuing searches would require changing the existing handoff. Keep fail-fast in this bounded task. |
| `src/applications/tillegal/graphs/legal_qa.py` | `QuerySearchNodes.query/search`, `compile_query_search_graph` | Synchronous Query node calls `understand`; Search invokes RetrievalService and constructs handoff. Leave graph and handoff untouched. |
| `src/application/services/retrieval_service.py` | `search`, 192–305 | Dispatches BM25, dense or hybrid; rerank is configured within hybrid. Classified errors/timeouts already produce FAILED. No backend fallback. |
| same | `_search_sparse`, 319–343; `_hydrate_sparse_hits`, 345–410; `_make_evidence`, 438–468; `_map_dense_evidence`, 619 onward | Uses existing indexing tokenizer, validates IDs, hydrates chunks/sources, checks hashes/eligibility. Dense and hybrid preserve their own metadata. Search must reuse these safeguards rather than replicate retrieval. |
| `src/applications/tillegal/retrieval/contracts.py` | `RetrievalRequest`, 23–44; `UnifiedEvidence`, 65–110; `RetrievalResponse`, 113–153 | Provides IDs, source snapshot, effective dates, hashes, policy, rank/score meaning, warning/error fields. Already supports strong source provenance; absence of metadata was a hypothesis, disproven. |
| Query/Search `schemas.py`, Query `prompts.py`, shared `llm_gateway.py`, LiteLLM adapter | Entire original files | Docstring placeholders. No working model gateway/provider to reuse. |

Read existing Query hardening, Query/Search, multimode, graph and retrieval fixture tests. They assert fail-fast, subtype identity, unchanged filters, Unicode original preservation, cancellation and programming-error propagation. Preserve those contracts. The exact-key schema assertion requires an intentional update for additive analysis fields.

## Decision before edits

| Option | Benefit | Limitation | Decision |
|---|---|---|---|
| A: rules only | Offline, deterministic, easy to audit | Cannot generalize arbitrary implicit legal issues | Keep an honestly labelled offline path and narrowly improve employment-exit planning. |
| B: LLM only | Flexible language interpretation | Does not replace input, provenance or date validation; gateway is absent | Reject as sole boundary. |
| C: deterministic guards plus one structured LLM call | Supports semantic facts/issues/questions with validated output and bounded errors | Requires application-supplied model adapter and evaluation | Select an opt-in semantic boundary with no silent fallback. |

No default provider/model is selected because the repository has no implemented approved gateway. The caller supplies an explicit model identifier and async structured-completion adapter. A Vietnamese-capable model supporting structured JSON is a requirement, not a verified quality claim. No direct SDK integration, credentials, new dependencies or autonomous loops.

Scope: Query agent/schema/prompt/semantic module, Search agent/evidence schema, minimal optional injection in QuerySearch bootstrap, focused tests and Markdown docs. No shared gateway, retrieval algorithms, graph, handoff, Judge, response/Answer, Summary or Verification changes.

Search keeps fail-fast: a conservative technical policy already enforced by handoff, not a legal sufficiency judgment. Expose PARTIAL/FAILED completeness and skipped indices. Exact duplicate requests reuse one response while preserving positional entries. Group identical source payloads only, retaining every query-local score/rank and native response. Different snapshots, effective dates, hashes and metadata stay separate.

Verification: baseline and regression tests; mock structured responses, timeouts/provider errors/unsupported facts/citations; real RetrievalService with fake data/model ports in all four configured modes; Ruff lint/format; broader offline suite if feasible; complete hash manifest and saved original files for diff review without Git. Do not claim live inference or legal accuracy.
