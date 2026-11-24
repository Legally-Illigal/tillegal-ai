# Public contracts

## QueryPlan

`query/agent.py:QueryPlan` requires `original`, `intent`, `domain`, `temporal_scope`, `subqueries`, `clarification`. Nullable clarification still requires its key. Intent is quote_lookup/legal_question; domain currently labour/unknown. At most four subqueries, each with text and purpose lookup/question_part/topic.

Backward-compatible defaults: analysis_method=deterministic, analysis_model=null; facts/issues/missing_information/citations/temporal_context/search_objectives/planning_warnings default empty lists. Original preserves caller text; offsets refer to NFC/trimmed analysis text. QueryPlan is an ordinary BaseModel (extra fields ignored), not a complete trust boundary for manually supplied plans.

|Field/type|Origin and meaning|
|---|---|
|facts: StatedFact(text,source_quote)|User statements/allegations; exact extraction, not verified truth. Semantic planner checks literal containment.|
|issues: list[str]|Information needs, not legal conclusions.|
|missing_information|Bounded questions for unknown context; narrower deterministic reconciliation, not complete legal prerequisites.|
|citations: LegalReference(kind,text,start,end,source)|Deterministic spans; source defaults user_supplied_unverified, no source-authority guarantee.|
|temporal_context: TemporalContext|text/start/end/role required; iso_date defaults null, negated false. Calendar-valid dates and heuristic roles are not applicability verification.|
|search_objectives: SearchObjective|Zero-based query_index → nonempty issue_indices; plan checks mapping bounds.|
|planning_warnings|Grounding/reclassification/consistency diagnostics, distinct from Search warnings.|

Provider SemanticAnalysis is extra-forbid and strictly typed where declared. Facts require text==source_quote. Unsupported model facts, temporal mentions, citation-like references and numbers are rejected by semantic guards. Direct QueryPlan deserialization does not rerun all these guards.

## SearchOptions: trusted caller only

All four fields required: mode=bm25/dense/hybrid, top_k strict integer1–50, as_of_date calendar date, allowed_usage_policies nonempty nonblank tuple. Extra fields forbidden. Policies normalized/deduplicated. Model output does not choose date or permissions. Reranking is configured on Hybrid, not a mode named rerank.

## SearchState

Plain TypedDict containing Pydantic objects/tuples, not a BaseModel. Required keys:

|Key|Meaning|
|---|---|
|plan|Executed QueryPlan dict|
|requests/responses|Native request/response models, including Hybrid/rerank subtypes|
|status|CLARIFICATION_REQUIRED, COMPLETED or FAILED|
|completeness|NOT_STARTED, COMPLETE, PARTIAL or FAILED; execution only|
|evidence|AggregatedEvidence(evidence,nonempty occurrences)|
|warnings/errors|Deduplicated code strings / typed RetrievalErrorDetail|
|skipped_subqueries|Zero-based unexecuted query indices after fail-fast|
|executed_searches|Actual backend invocations, not cache hits or HTTP count|

NO_MATCH can coexist with COMPLETE. PARTIAL may have only a previous NO_MATCH and a failure, so inspect evidence rather than assuming nonempty. Unexpected exceptions/cancellation propagate. QueryInputError/QueryAnalysisError are raised before Search; classified retrieval errors are returned in SearchState.

Each EvidenceOccurrence records subquery_index,response_index,query,request_id,rank,raw_score,score_kind and issue_indices(default empty tuple). Empty legacy issue associations mean unknown, not support for every issue. Native rank is local to its response. Aggregate representative score/rank comes from first occurrence, not a global ranking.

UnifiedEvidence retains source/structure/snapshot/chunk IDs, stored content/hash, locators, source metadata and dates. Many nullable fields still require keys. Grouping excludes query-local rank/score/method but retains version/date/content/metadata distinctions. Conflicting same-ID payloads remain separate and warn. Stored hash match is traceability, not legal verification.

## JSON without losing native extensions

```python
from pydantic import TypeAdapter
from src.applications.tillegal.agents.search.agent import SearchState
payload = TypeAdapter(SearchState).dump_python(state, mode="json", serialize_as_any=True)
```

serialize_as_any=True preserves fusion/reranking fields. Default base-type serialization can omit them. For trusted native JSON, restore response subtypes before state validation:

```python
from pydantic import TypeAdapter
from src.applications.tillegal.agents.search.agent import SearchState
from src.applications.tillegal.retrieval.contracts import RetrievalResponse
from src.applications.tillegal.retrieval.hybrid_models import HybridRetrievalResponse
from src.applications.tillegal.retrieval.reranking_models import RerankedHybridRetrievalResponse

def restore_state(payload):
    responses = []
    for raw in payload["responses"]:
        model = (RerankedHybridRetrievalResponse if "reranking" in raw
                 else HybridRetrievalResponse if "fusion" in raw else RetrievalResponse)
        responses.append(model.model_validate(raw))
    return TypeAdapter(SearchState).validate_python({**payload, "responses": tuple(responses)})
```

This is not grounding or a security boundary for untrusted external plans. Source authority, topical support and temporal applicability remain unverified.
