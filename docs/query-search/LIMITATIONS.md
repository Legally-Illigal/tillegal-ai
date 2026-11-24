# Operational and quality limitations

Query/Search is a technical interface for planning/retrieval, not a completed legal-answer system.

|Boundary|Known limitation|Owner/interpretation|
|---|---|---|
|Query semantics|Exact grounding can reject punctuation/paraphrase variants; historical Q007 primary failure remains.|Query owner; no silent fallback and no claim of universal reliability.|
|Issue/missing info|Domain labour/unknown only; narrow deterministic slots/cues, bounded issue count.|Query owner; no general legal ontology/completeness guarantee.|
|Manual external plan|QueryPlan extra-ignore and selected invariant checks do not rerun semantic grounding; an oversized end offset can pass suffix slice matching.|Caller/Query trust boundary. Prefer actual planner output, not arbitrary external plans.|
|Citation identity|Exact lookup title warning is literal, quote_lookup-only, not authoritative source/article verification.|Future consumer must distinguish principal source from cross-reference; Q025 may not receive warning.|
|Temporal context|Event/publication/effectivity roles are heuristic; execution date is caller supplied, not inferred from document year.|Query/caller. Dates in source metadata may be incomplete.|
|Corpus|Earlier visible inventory lacked stored45/2019/QH14 identity; missing effectivity dates and coverage signals remain.|Corpus owner. Scope/time-limited evidence, not global absence or a demonstrated Search defect.|
|Ranking|All modes can rank templates/cross-references too highly for the requested need; no expert relevance labels.|Retrieval/evaluation owner. Technical success does not certify legal support.|
|Execution|COMPLETE may be empty; PARTIAL may contain no evidence. Search fails fast, unexpected errors/cancellation propagate.|Future integrator must inspect response status/errors/skips.|
|Provenance|Grouping preserves source/version payload; scores are query/backend-local, not probabilities.|Consumer must use occurrences, not a global representative-score sort.|
|Serialization|Default base-type JSON serialization can omit Hybrid/rerank fields; base validation rejects subtype extras.|Use serialize_as_any=True and explicit subtype restoration.|
|Operations|Existing local E5/CE paths, ready indexes, read permissions and cold-load budgets required.|Retrieval/operations; no model install/download in this integration.|

No claim that Gemini is globally better than deterministic Query. No expert P@K/NDCG or verified legal applicability is supplied. Historical raw evidence and academic reports remain on the preserved source branch, excluded from main to avoid maintenance bloat. New tests run without historical datasets; application behavior is unchanged from the source implementation.
