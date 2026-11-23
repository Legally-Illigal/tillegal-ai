# Search Agent internals

## Inputs and execution

search(plan, retrieval, options, timeout_seconds=45) validates QueryPlan and strict frozen SearchOptions. The facade QuerySearch.search does not expose this45-second per-query setting; create_query_search timeout_seconds configures RetrievalService (default30), not the Search outer deadline. Multiple subqueries each get their own deadline; this is not a global request SLA. Caller cancellation or an outer application deadline remains the caller's responsibility.

If plan.clarification is nonempty, no read occurs: status CLARIFICATION_REQUIRED/completeness NOT_STARTED. Otherwise build RetrievalRequest(query=subquery.text, **options.model_dump()) per subquery. Request carries trusted mode/top_k/as_of_date/policies, never model-inferred execution filters.

Identical query TEXT only is cached within one Search invocation; case/quotes/spaces are not normalized for dedup. Cached response/request_id can appear in multiple occurrences. executed_searches counts actual backend invocations, not request-list length or HTTP calls. No cache across user requests, no retries or backend fallback by Search.

## Native result and aggregation

Each response remains its original subtype: Hybrid/reranking extensions retained in responses. _finish groups full UnifiedEvidence payloads except rank/raw_score/score_kind/retrieval_method, which are query-local. Identity includes source/structure/snapshot IDs, content/hash, effective dates and metadata. Distinct versions stay separate. Same chunk ID with different payloads warns EVIDENCE_IDENTITY_CONFLICT. Group order is insertion order, not a merged global score ranking.

AggregatedEvidence contains a representative evidence plus nonempty occurrences. Every occurrence records subquery_index, response_index, request_id, query, native rank/raw_score/score_kind and issue_indices. Representative evidence rank/score is only from first occurrence; use occurrences for comparisons. Scores from BM25/cosine/RRF or separate queries are not interchangeable probabilities. Reranked evidence retains RRF raw_score, so do not resort it by raw_score.

## Issue links

Mapping comes solely from plan.search_objectives. Exact duplicate queries can map to multiple issue indices. Legacy plans without links get empty issue_indices, not guessed domain associations. An issue link expresses provenance, not semantic support or coverage. An evidence chunk may legitimately be retrieved for multiple issues; preserve all occurrences.

## Errors, no match and partials

TimeoutError or RetrievalServiceError produces a typed FAILED RetrievalResponse; fail-fast stops later subqueries. Existing earlier responses/evidence retained. status FAILED with completeness PARTIAL if an earlier response was nonfailed (including NO_MATCH), otherwise FAILED. skipped_subqueries are zero-based unexecuted plan indices. NO_MATCH yields warning NO_MATCH:<index>; COMPLETE only means execution completed, even when evidence empty. Unexpected programming exceptions and cancellation propagate; they are not masked as ordinary empty results.

Search errors expose RetrievalErrorDetail(category/code/stage/message/retryable). Response warnings retain richer message/chunk identity; aggregate SearchState.warnings is deduplicated code strings. Read responses when detail is needed. Reranker operational fallback to RRF belongs to Retrieval, with explicit reranking metadata; Search itself does not choose fallback.

## Uncertainty warnings

- EXACT_LOOKUP_SOURCE_IDENTITY_UNCONFIRMED: quote_lookup, a document number supplied, evidence nonempty, number missing from concatenated returned TITLES. Literal metadata warning only; no authoritative document/article verification and not guaranteed for Q025 legal_question.
- TEMPORAL_SCOPE_REQUIRES_CALLER_DATE_REVIEW: nonempty legacy temporal_scope. Search does not automatically change as_of_date from that list.
- TEMPORAL_METADATA_INCOMPLETE: Retrieval reports an unspecified effective_from OR effective_to. A null end date can be open-ended, so the warning is conservative, not proof of invalid applicability.
- SOURCE_URL_MISSING, EVIDENCE_IDENTITY_CONFLICT, SEARCH_INCOMPLETE, NO_MATCH:<i>: preserve and interpret with source/response context.

## Evidence

Current acceptance exercises fixture success/no-match/partial/skipped/citation/time warnings. Existing tests cover cancellation, cache, version conflicts and native subtype parity. Historical real28-call corpus experiment and57-occurrence audit found no Search orchestration defect; these are not fresh live calls this phase. No production Search change made.
