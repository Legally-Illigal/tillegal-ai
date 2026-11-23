# Targeted changes and rejected experiment

## Kept in production

Only `src/applications/tillegal/agents/query/semantic.py` changes agent behavior:

1. After deterministic clarification/exact-lookup exits, build a fresh SemanticAnalysis JSON schema whose intent enum is only legal_question. This matches the runtime invariant already enforced. The public SemanticAnalysis schema and QueryPlan contracts still accept quote_lookup where appropriate; legacy callers remain compatible. Runtime rejection is retained if a mock/provider ignores constraints.
2. For a single unique search objective, append any omitted literal article/clause/document reference spans supplied by the user. This repairs the observed document-identity loss without inventing citations. For multiple objectives, don't append every reference to unrelated queries; semantic association remains the model's responsibility. Final QueryPlan still enforces the query-length bound. This is not citation verification.

Mocked regression tests verify both the narrowed provider schema and precise user-reference preservation, including no fabrication, no duplicate reference and no cross-assignment to multiple objectives. The latter repair is demonstrated on the recorded candidate Q025 through regression/replay; the final live Q025 was blocked earlier by its temporal error, so a successful live citation-repair claim is not made.

## Rejected

A longer prompt attempted exact copying, no redundant clarification, retaining numerical context and citation identity. It fixed the three original response failures but reduced distinct objective/missing-information proxies, omitted citations and introduced a new exact-fact failure. Full text and hash remain in gemini-after.json. **It was rolled back.** The current SYSTEM_PROMPT bytes equal the baseline prompt, not the rejected candidate. We do not hide its favorable or unfavorable outputs.

## Unchanged

No Search behavior was changed: real hash/provenance/dedup checks did not justify an aggregation patch. No BM25, dense encoder algorithm, RRF, reranker, persistence schema, migration, policy, graph or unrelated agent change. Warm-model options, redacted exports, scoring and timings belong to the evaluation scripts only. No production retry/fallback added. No answer/legal sufficiency logic added.

## Verification strength

The narrowed schema is supported by invariant/regression tests and the two formerly wrong-intent live cases now returning legal_question. The small final cohort is insufficient to prove global semantic improvement or remove stochastic regressions. The citation repair is deterministically grounded and tested, but not verified as a recall improvement on a labelled corpus.
