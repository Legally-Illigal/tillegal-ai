# Compatibility

No existing V1 source model, function signature, prompt, LLM config, graph or handoff changed. create_query_search(...semantic_mode="gemini") and await runner.search(question) remain identical. V2 is separate explicit entrypoints, never a silent wrapper returned by V1.

plan_query_v2 validates options before model I/O, reserves original question before awaiting provider, calls the same existing planner, then adds IDs. It performs additional deterministic input prevalidation to reserve context safely, without changing model messages/schema/count. Claims/citation sidecars remain empty in automatic QA; V1 original/citations/time/facts/issues are retained in legacy_plan.

V2 refuses clarification-aware planning with CLARIFICATION_PLANNING_UNAVAILABLE rather than append answers into original. Typed answer spans can be represented in controlled envelopes but are not new QA model context. Verify planning raises VERIFY_EXTRACTION_UNAVAILABLE. This is explicit capability behavior, not a fallback.

search_v2 validates envelope/registry and every SearchOptions field before backend I/O. It invokes the existing search once, preserving requests, cache, rank, score, errors and partial outcomes. A subquery having only resolve_citation metadata cannot run BM25 as an exact resolver: the whole execution returns unavailable to avoid silently changing native index/skipped semantics. If that SAME subquery also has an explicit find_support entry in QA, native retrieval can run for support only; exact outcome stays unavailable and receives no support evidence link.

Tests compare mocked Gemini provider arguments and one-call count against direct V1, legacy plan/state field sets, native payloads/requests and deterministic behavior. Independently executed native responses have different generated request IDs/times; parity does not incorrectly require those runtime IDs to be identical across separate searches. Provider/partial/version/graph regressions remain covered by unchanged tests.

Graph QuerySearchNodes.query still calls deterministic understand directly. Future opt-in semantic delegation is a separate graph-owned change. JudgeHandoff v1 remains strict and unchanged; SearchEnvelopeV2 is a separate carrier and is not automatically delivered to Judge.

## Conservative lookup mapping

For `Trích dẫn: thuế`, V1 retains intent `quote_lookup` and subquery purpose `lookup`. The V2 projection deliberately labels ordinary corpus retrieval `find_support`; it does not claim exact citation resolution. There is no structured citation target in that input, so automatic QA sidecars stay empty. The original V1 plan is preserved. Evidence is only `support_suggestion`, with resolution `unresolved` and legal validity `unknown`. Explicit `resolve_citation` targets are separate and return `EXACT_RESOLVER_UNAVAILABLE`; support evidence never overwrites the cited original. A claim with no citation IDs is distinct from a retrieval `no_match` outcome and does not imply a Verification verdict.
