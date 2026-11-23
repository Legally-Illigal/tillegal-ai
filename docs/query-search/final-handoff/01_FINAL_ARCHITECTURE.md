# Verified final architecture

## Entry points and execution order

|Order|Actual file/function|Input|Output/role|
|---|---|---|---|
|1|src/query_search_bootstrap.py:create_query_search|SupabaseSettings, SearchOptions, optional semantic_mode/query_agent/checkpoints/configs|QuerySearch composition; default deterministic|
|2|QuerySearch.search(question)|External question string|Calls planner then Search, returns SearchState|
|3a|src/applications/tillegal/agents/query/agent.py:understand|Question|Validated deterministic QueryPlan dict|
|3b|query/semantic.py:SemanticQueryAgent.understand|Question + StructuredCompletion dependency|One bounded semantic analysis, strict grounding or QueryAnalysisError|
|4|query/gemini.py:create_gemini_query_agent|Environment + configs/models.yaml|Gemini-only Query planner; no provider call during construction|
|5|src/framework/llm/providers/gemini_adapter.py:GeminiStructuredCompletion.__call__|model/system/user/schema|JSON string via LiteLLM; no-log, no retry, bounded timeout|
|6|search/agent.py:search|Plan, RetrievalService, trusted SearchOptions|Sequential RetrievalRequests/native responses|
|7|src/retrieval_bootstrap.py:create_retrieval_service|Supabase settings and optional local checkpoints|Read adapters and existing RetrievalService; no ASGI startup/migration|
|8|src/application/services/retrieval_service.py:RetrievalService.search|RetrievalRequest|BM25/Dense or Hybrid/rerank response subtype|
|9|search/agent.py:_finish|Plan, all executed requests/responses|Aggregate identical payloads, preserve occurrences/warnings/errors/skips|

`QuerySearch` is a frozen dataclass facade. It has no LLM logic, iterative search, legal-answer generation or relevance scoring. Passing query_agent injects a SemanticQueryAgent; semantic_mode="gemini" instead constructs the configured agent. Supplying both is an explicit configuration error. Default semantic_mode="deterministic" with no injected query_agent uses pure understand().

## Retrieval boundary

RetrievalService owns index readiness, tokenization/vector encoding, existing RPC calls, hydration, hash/eligibility/index-consistency checks. BM25 uses the existing Unicode tokenizer and sparse index. Dense uses local E5 and vector RPC. Hybrid uses sequential branches and reciprocal_rank_fusion; reranking is an optional post-Hybrid stage. Search does not implement these algorithms, rescale native scores or choose alternative backends on error.

Service helper ownership: application/services/hybrid_retrieval.py:search_hybrid; applications/tillegal/retrieval/rank_fusion.py:reciprocal_rank_fusion; application/services/reranking.py:search_reranked; integrations/embeddings/e5_query_encoder.py:E5QueryEncoder; integrations/embeddings/cross_encoder_reranker.py:LocalCrossEncoder. These were inspected, not modified.

## Execution is separate from validity of legal support

Source/content hashes establish traceability to stored chunks, not authoritative correctness. Retrieved content can contain breadcrumbs/templates/cross-references. Metadata/index observations are BEST_EFFORT, not a transaction snapshot. Issue linkage means which query produced a chunk, not that the chunk answers that issue.

## Audit scope

Query/Search source, supporting bootstrap/provider/contracts/config and relevant RetrievalService behavior inspected directly. Existing tests/real artifacts corroborate behavior; earlier summaries were not treated as source. Search/prompts.py and package __init__.py are descriptive placeholders, not hidden planning logic. Shared gateway placeholders are not the Gemini runtime path. Graph and other agents remain untouched.
