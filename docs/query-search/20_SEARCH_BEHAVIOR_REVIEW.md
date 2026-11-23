# 20 — Search behavior review

## Existing call chain and ownership

`src/query_search_bootstrap.py:create_query_search` composes a planner and existing RetrievalService. `QuerySearch.search` gets a plan then calls `src/applications/tillegal/agents/search/agent.py:search`. Search validates QueryPlan/options, builds a RetrievalRequest per subquery, calls RetrievalService sequentially and caches only EXACT same query text within that request. Trusted date/policies come from SearchOptions, not model output.

Search `_finish` groups only identical full source payloads excluding query-local rank/raw_score/score_kind/retrieval_method. Content hash, source/structure/snapshot IDs, dates and metadata remain in the grouping key. Distinct versions stay distinct; conflicting same-chunk payloads warn EVIDENCE_IDENTITY_CONFLICT. No global score sorting, reranking, relevance filtering or source suppression is performed by Search. Aggregate order is insertion order, not a universal ranking across queries. Consumers use each occurrence's native rank/query/index.

## Evidence from stored real responses

15 successful saved variant/case runs,57 native evidence occurrences: every chunk/hash/rank/raw_score retained exactly in aggregate occurrences. Q004 deterministic collapses one duplicate payload across queries while preserving both occurrences. Issue associations match only explicit search_objectives; legacy absent links remain empty instead of guessed. The blocked Q007 primary Gemini plan is NOT represented as an empty successful retrieval.

`scripts/investigate_query_relevance.py:inspect_native` audits cardinality and native tuples; `build_review` joins variant+query+chunk+rank. Exact-query text alone is insufficient to disambiguate Q022's deterministic short circuit in both variants. A draft review join exposed this evaluator-only ambiguity; fixed by matching saved blind_variant_token, covered by regression. Superseded human_review.initial_join.json retained for transparency, not to be used for labels. This was not a Search production defect.

## Current Search replay

Prior stored warnings predate the exact-source warning. Offline `_finish` replay using all native responses and original plans confirms Q022 emits EXACT_LOOKUP_SOURCE_IDENTITY_UNCONFIRMED on BOTH variants. All occurrences/ranks/issue links still match. The earlier source_identity_real.json separately demonstrated the warning on a real request. Replay is explicitly SAVED_NATIVE_RESPONSES_FINAL_SEARCH_FINISH_NO_NETWORK, not new live retrieval or Gemini.

The warning is literal and scoped to quote_lookup with a document number absent from returned TITLES. It does not filter evidence, prove corpus absence, verify article identity or establish legal sufficiency. Q025 is legal_question, so a comparable warning is not guaranteed; citation-check consumers still must inspect source identity. Do not infer verified source from absence of warning. Title matching itself is a weak metadata check, not authoritative identity proof.

## Failure/completeness behavior

Classified dependency failures/timeouts become FAILED responses. Search stops after the first failed subquery, retains previous evidence, reports skipped_subqueries and SEARCH_INCOMPLETE. PARTIAL means some execution succeeded, not partial legal correctness. NO_MATCH remains visible but COMPLETE means execution completed. Cancellation/unexpected programming errors propagate. There is no backend fallback by Search. Existing optional reranker can operationally fall back to RRF with explicit metadata; current3 live responses were APPLIED, not fallback.

Real current experiments cover successful mode execution. Partial failure, cancellation, conflicting versions and no-match behavior are validated by existing mocked/contract tests, not newly induced real outages. Tests include test_partial_failure_retains_evidence_and_explicit_skipped_queries, test_conflicting_legal_versions_never_merge, graph/test_query_search_workflow.py failure/handoff/cancellation cases.

## Decision

No reproducible Search orchestration defect was established. No production Search changes. Adding a relevance threshold, topic filter, guessed article gate, or cross-query score sort would risk discarding evidence and exceed the support from unreviewed data. The review retains every native response/chunk for human evaluation.

Artifacts: [saved audit](../../evaluation/query_search/relevance_investigation/saved_search_audit.json), [current Search replay](../../evaluation/query_search/relevance_investigation/current_search_replay.json), [native experiment responses](../../evaluation/query_search/relevance_investigation/experiments.json).
