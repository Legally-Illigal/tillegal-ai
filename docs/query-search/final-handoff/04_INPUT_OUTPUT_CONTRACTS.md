# Public input/output contracts

Tables generated from CURRENT Pydantic model fields. Required means the key must be supplied; nullable means null may be a value. These are independent. []/()/null/default literal values are backward-compatible defaults only where shown. Full machine JSON schemas and executed SearchState examples: [execution.json](../../../evaluation/query_search/final_acceptance/execution.json).

## Provenance and trust

- External caller provides question; trusted application provides as_of_date, allowed_usage_policies, top_k, mode and backend/checkpoint configuration.
- Provider generates SemanticAnalysis; deterministic planner validation/postprocessing owns final QueryPlan spans, links and warnings.
- Retrieval supplies stored material and source claims; Search supplies occurrence associations and execution completeness.
- No stage shown here establishes verified legal support. Facts may be allegations; issues are information needs.
- QueryPlan/Subquery use BaseModel default extra-ignore and some coercion. SemanticModel, SearchOptions and retrieval ContractModel forbid extra fields; strictness varies by field. Never describe all schemas as globally strict.

## QueryPlan

Required core fields: original,intent,domain,temporal_scope,subqueries,clarification. Optional metadata defaults preserve legacy plans; no automatic fact grounding for arbitrary deserialized plans. Origin is deterministic or validated semantic planner output.

|Field|Required|JSON shape/constraints|Default|
|---|---|---|---|
|original|yes|`{"maxLength": 10000, "minLength": 1, "type": "string"}`|`none (required)`|
|intent|yes|`{"enum": ["quote_lookup", "legal_question"], "type": "string"}`|`none (required)`|
|domain|yes|`{"enum": ["labour", "unknown"], "type": "string"}`|`none (required)`|
|temporal_scope|yes|`{"items": {"type": "string"}, "type": "array"}`|`none (required)`|
|subqueries|yes|`{"items": {"$ref": "#/$defs/Subquery"}, "maxItems": 4, "minItems": 1, "type": "array"}`|`none (required)`|
|clarification|yes|`{"anyOf": [{"type": "string"}, {"type": "null"}]}`|`none (required)`|
|analysis_method|no|`{"enum": ["deterministic", "llm"], "type": "string"}`|`"deterministic"`|
|analysis_model|no|`{"anyOf": [{"type": "string"}, {"type": "null"}]}`|`null`|
|facts|no|`{"items": {"$ref": "#/$defs/StatedFact"}, "maxItems": 12, "type": "array"}`|`[]`|
|issues|no|`{"items": {"type": "string"}, "maxItems": 4, "type": "array"}`|`[]`|
|missing_information|no|`{"items": {"type": "string"}, "maxItems": 8, "type": "array"}`|`[]`|
|citations|no|`{"items": {"$ref": "#/$defs/LegalReference"}, "type": "array"}`|`[]`|
|temporal_context|no|`{"items": {"$ref": "#/$defs/TemporalContext"}, "type": "array"}`|`[]`|
|search_objectives|no|`{"items": {"$ref": "#/$defs/SearchObjective"}, "maxItems": 4, "type": "array"}`|`[]`|
|planning_warnings|no|`{"items": {"type": "string"}, "type": "array"}`|`[]`|

## Subquery

Planner generated. purpose=lookup/question_part/topic describes use, not source verification.

|Field|Required|JSON shape/constraints|Default|
|---|---|---|---|
|text|yes|`{"maxLength": 10000, "minLength": 1, "type": "string"}`|`none (required)`|
|purpose|yes|`{"enum": ["lookup", "question_part", "topic"], "type": "string"}`|`none (required)`|

## StatedFact

User-supplied statement/allegation, not verified truth. text==source_quote; semantic planner additionally checks literal containment in question.

|Field|Required|JSON shape/constraints|Default|
|---|---|---|---|
|text|yes|`{"maxLength": 1000, "minLength": 1, "type": "string"}`|`none (required)`|
|source_quote|yes|`{"maxLength": 1000, "minLength": 1, "type": "string"}`|`none (required)`|

## SemanticAnalysis

Provider JSON contract. Strict extra-forbid/frozen semantic models; every field required, clarification nullable. Ordinary semantic invocation restricts intent to legal_question.

|Field|Required|JSON shape/constraints|Default|
|---|---|---|---|
|intent|yes|`{"enum": ["quote_lookup", "legal_question"], "type": "string"}`|`none (required)`|
|domain|yes|`{"enum": ["labour", "unknown"], "type": "string"}`|`none (required)`|
|facts|yes|`{"items": {"$ref": "#/$defs/StatedFact"}, "maxItems": 12, "type": "array"}`|`none (required)`|
|issues|yes|`{"items": {"$ref": "#/$defs/LegalIssue"}, "maxItems": 4, "minItems": 1, "type": "array"}`|`none (required)`|
|missing_information|yes|`{"items": {"type": "string"}, "maxItems": 8, "type": "array"}`|`none (required)`|
|temporal_mentions|yes|`{"items": {"type": "string"}, "maxItems": 12, "type": "array"}`|`none (required)`|
|clarification|yes|`{"anyOf": [{"maxLength": 1000, "type": "string"}, {"type": "null"}]}`|`none (required)`|

## LegalIssue

Provider information need and search_query, not legal conclusion; both required/nonblank.

|Field|Required|JSON shape/constraints|Default|
|---|---|---|---|
|issue|yes|`{"maxLength": 1000, "minLength": 1, "type": "string"}`|`none (required)`|
|search_query|yes|`{"maxLength": 10000, "minLength": 1, "type": "string"}`|`none (required)`|

## LegalReference

Deterministic literal extraction. source defaults user_supplied_unverified. It does not certify the cited law exists or the allegation is correct.

|Field|Required|JSON shape/constraints|Default|
|---|---|---|---|
|kind|yes|`{"enum": ["document", "article", "clause", "point", "statute_reference"], "type": "string"}`|`none (required)`|
|text|yes|`{"type": "string"}`|`none (required)`|
|start|yes|`{"minimum": 0, "type": "integer"}`|`none (required)`|
|end|yes|`{"exclusiveMinimum": 0, "type": "integer"}`|`none (required)`|
|source|no|`{"const": "user_supplied_unverified", "type": "string"}`|`"user_supplied_unverified"`|

## TemporalContext

Deterministic span and heuristic role. iso_date defaultnull, negated defaultfalse. Dates are calendar checked, not legal applicability checked.

|Field|Required|JSON shape/constraints|Default|
|---|---|---|---|
|text|yes|`{"type": "string"}`|`none (required)`|
|start|yes|`{"minimum": 0, "type": "integer"}`|`none (required)`|
|end|yes|`{"exclusiveMinimum": 0, "type": "integer"}`|`none (required)`|
|role|yes|`{"enum": ["event_date", "applicability_date", "publication_date", "effective_date", "historical_reference", "relative_reference", "duration", "current_reference", "unspecified"], "type": "string"}`|`none (required)`|
|iso_date|no|`{"anyOf": [{"type": "string"}, {"type": "null"}]}`|`null`|
|negated|no|`{"type": "boolean"}`|`false`|

## SearchObjective

Postprocessing-generated zero-based query_index→issue_indices. QueryPlan validates referred indices; legacy absent links remain empty.

|Field|Required|JSON shape/constraints|Default|
|---|---|---|---|
|query_index|yes|`{"maximum": 3, "minimum": 0, "type": "integer"}`|`none (required)`|
|issue_indices|yes|`{"items": {"type": "integer"}, "maxItems": 4, "minItems": 1, "type": "array"}`|`none (required)`|

## SearchOptions

ALL4 fields required and trusted-caller supplied. mode=bm25/dense/hybrid; reranking is configuration on hybrid, not a fourth mode enum. Strict positive integer top_k1..50; nonempty nonblank policy list deduplicated. Model never supplies execution filters.

|Field|Required|JSON shape/constraints|Default|
|---|---|---|---|
|mode|yes|`{"$ref": "#/$defs/RetrievalMode"}`|`none (required)`|
|top_k|yes|`{"maximum": 50, "minimum": 1, "type": "integer"}`|`none (required)`|
|as_of_date|yes|`{"format": "date", "type": "string"}`|`none (required)`|
|allowed_usage_policies|yes|`{"items": {"type": "string"}, "minItems": 1, "type": "array"}`|`none (required)`|

## EvidenceOccurrence

Search-generated. Required except issue_indices defaultempty tuple. Native rank/query/request provenance; empty issue mapping is meaningful.

|Field|Required|JSON shape/constraints|Default|
|---|---|---|---|
|subquery_index|yes|`{"minimum": 0, "type": "integer"}`|`none (required)`|
|response_index|yes|`{"minimum": 0, "type": "integer"}`|`none (required)`|
|query|yes|`{"type": "string"}`|`none (required)`|
|request_id|yes|`{"type": "string"}`|`none (required)`|
|rank|yes|`{"minimum": 1, "type": "integer"}`|`none (required)`|
|raw_score|yes|`{"type": "number"}`|`none (required)`|
|score_kind|yes|`{"enum": ["BM25", "COSINE_SIMILARITY", "RRF"], "type": "string"}`|`none (required)`|
|issue_indices|no|`{"items": {"type": "integer"}, "type": "array"}`|`[]`|

## AggregatedEvidence

Search-generated representative payload plus at least1 occurrence. Do not infer global rank from the representative.

|Field|Required|JSON shape/constraints|Default|
|---|---|---|---|
|evidence|yes|`{"$ref": "#/$defs/UnifiedEvidence"}`|`none (required)`|
|occurrences|yes|`{"items": {"$ref": "#/$defs/EvidenceOccurrence"}, "minItems": 1, "type": "array"}`|`none (required)`|

## RetrievalRequest

Constructed by Search. Unlike SearchOptions, top_k here defaults10, but SearchOptions still requires caller to specify it.

|Field|Required|JSON shape/constraints|Default|
|---|---|---|---|
|query|yes|`{"maxLength": 10000, "minLength": 1, "type": "string"}`|`none (required)`|
|mode|yes|`{"$ref": "#/$defs/RetrievalMode"}`|`none (required)`|
|top_k|no|`{"maximum": 50, "minimum": 1, "type": "integer"}`|`10`|
|as_of_date|yes|`{"format": "date", "type": "string"}`|`none (required)`|
|allowed_usage_policies|yes|`{"items": {"type": "string"}, "minItems": 1, "type": "array"}`|`none (required)`|

## RetrievalResponse

Native result; subtype may add fusion/reranking. Preserve query/date/policy/index, warnings and typed errors. index nullable but required; status controls evidence/error consistency.

|Field|Required|JSON shape/constraints|Default|
|---|---|---|---|
|schema_version|no|`{"const": "1", "type": "string"}`|`"1"`|
|request_id|yes|`{"format": "uuid", "type": "string"}`|`none (required)`|
|query|yes|`{"type": "string"}`|`none (required)`|
|query_used|yes|`{"type": "string"}`|`none (required)`|
|mode|yes|`{"$ref": "#/$defs/RetrievalMode"}`|`none (required)`|
|top_k|yes|`{"maximum": 50, "minimum": 1, "type": "integer"}`|`none (required)`|
|as_of_date|yes|`{"format": "date", "type": "string"}`|`none (required)`|
|allowed_usage_policies|yes|`{"items": {"type": "string"}, "type": "array"}`|`none (required)`|
|selected_index_name|yes|`{"type": "string"}`|`none (required)`|
|index|yes|`{"anyOf": [{"$ref": "#/$defs/IndexIdentity"}, {"type": "null"}]}`|`none (required)`|
|status|yes|`{"enum": ["OK", "NO_MATCH", "FAILED"], "type": "string"}`|`none (required)`|
|evidence|no|`{"items": {"$ref": "#/$defs/UnifiedEvidence"}, "type": "array"}`|`[]`|
|warnings|no|`{"items": {"$ref": "#/$defs/RetrievalWarning"}, "type": "array"}`|`[]`|
|error|no|`{"anyOf": [{"$ref": "#/$defs/RetrievalErrorDetail"}, {"type": "null"}]}`|`null`|
|retrieved_at|yes|`{"format": "date-time", "type": "string"}`|`none (required)`|
|consistency|no|`{"const": "BEST_EFFORT", "type": "string"}`|`"BEST_EFFORT"`|

## UnifiedEvidence

Retrieved stored material with unverified source claims. Nullable source/locator/date fields mostly remain REQUIRED keys; only content_representation has a default. Hash traceability is not legal verification.

|Field|Required|JSON shape/constraints|Default|
|---|---|---|---|
|retrieval_chunk_id|yes|`{"format": "uuid", "type": "string"}`|`none (required)`|
|source_document_id|yes|`{"format": "uuid", "type": "string"}`|`none (required)`|
|document_structure_id|yes|`{"format": "uuid", "type": "string"}`|`none (required)`|
|chunk_key|yes|`{"minLength": 1, "type": "string"}`|`none (required)`|
|content|yes|`{"minLength": 1, "type": "string"}`|`none (required)`|
|content_sha256|yes|`{"pattern": "^[0-9a-f]{64}$", "type": "string"}`|`none (required)`|
|hash_check|yes|`{"enum": ["MATCHED_STORED", "PAYLOAD_ONLY"], "type": "string"}`|`none (required)`|
|content_representation|no|`{"const": "retrieval_chunk_content", "type": "string"}`|`"retrieval_chunk_content"`|
|rank|yes|`{"minimum": 1, "type": "integer"}`|`none (required)`|
|raw_score|yes|`{"type": "number"}`|`none (required)`|
|score_kind|yes|`{"enum": ["BM25", "COSINE_SIMILARITY", "RRF"], "type": "string"}`|`none (required)`|
|retrieval_method|yes|`{"$ref": "#/$defs/RetrievalMode"}`|`none (required)`|
|node_id|yes|`{"anyOf": [{"type": "string"}, {"type": "null"}]}`|`none (required)`|
|block_id|yes|`{"anyOf": [{"type": "string"}, {"type": "null"}]}`|`none (required)`|
|chunk_type|yes|`{"minLength": 1, "type": "string"}`|`none (required)`|
|start_offset|yes|`{"anyOf": [{"minimum": 0, "type": "integer"}, {"type": "null"}]}`|`none (required)`|
|end_offset|yes|`{"anyOf": [{"minimum": 0, "type": "integer"}, {"type": "null"}]}`|`none (required)`|
|chunk_metadata|yes|`{"additionalProperties": true, "type": "object"}`|`none (required)`|
|source_id|yes|`{"anyOf": [{"type": "string"}, {"type": "null"}]}`|`none (required)`|
|source_record_id|yes|`{"anyOf": [{"type": "string"}, {"type": "null"}]}`|`none (required)`|
|source_snapshot_id|yes|`{"anyOf": [{"type": "string"}, {"type": "null"}]}`|`none (required)`|
|title|yes|`{"minLength": 1, "type": "string"}`|`none (required)`|
|source_url|yes|`{"anyOf": [{"type": "string"}, {"type": "null"}]}`|`none (required)`|
|language|yes|`{"anyOf": [{"type": "string"}, {"type": "null"}]}`|`none (required)`|
|issued_on|yes|`{"anyOf": [{"format": "date", "type": "string"}, {"type": "null"}]}`|`none (required)`|
|effective_from|yes|`{"anyOf": [{"format": "date", "type": "string"}, {"type": "null"}]}`|`none (required)`|
|effective_to|yes|`{"anyOf": [{"format": "date", "type": "string"}, {"type": "null"}]}`|`none (required)`|
|effect_status_reported|yes|`{"anyOf": [{"type": "string"}, {"type": "null"}]}`|`none (required)`|
|usage_policy|yes|`{"minLength": 1, "type": "string"}`|`none (required)`|
|source_metadata|yes|`{"additionalProperties": true, "type": "object"}`|`none (required)`|

## RetrievalErrorDetail

Safe typed retrieval diagnostic. retryable defaultsfalse; it does not trigger automatic retries in Search.

|Field|Required|JSON shape/constraints|Default|
|---|---|---|---|
|category|yes|`{"$ref": "#/$defs/ErrorCategory"}`|`none (required)`|
|code|yes|`{"type": "string"}`|`none (required)`|
|stage|yes|`{"type": "string"}`|`none (required)`|
|message|yes|`{"type": "string"}`|`none (required)`|
|retryable|no|`{"type": "boolean"}`|`false`|

## SearchState

TypedDict, not a BaseModel: all declared keys required at typing level; runtime search returns plain dict containing tuples/Pydantic objects. External deserialization is not automatically validated just by annotating SearchState. TypeAdapter(SearchState) handles base responses in the acceptance demo. For Hybrid/rerank output use serialize_as_any=True to retain subtype metadata. For extended JSON input restore the response subtype before validating the state; base validation alone rejects fusion/reranking fields. See05 and serialization_probe.json.

|Key|Runtime value|Meaning|
|---|---|---|
|plan|dict|Original executed plan|
|requests|tuple[RetrievalRequest,...]|Includes cache-hit requests; may be fewer than plan queries after failure|
|responses|tuple[RetrievalResponse,...]|Native response subtypes preserved|
|status|CLARIFICATION_REQUIRED/COMPLETED/FAILED|Execution outcome|
|completeness|NOT_STARTED/COMPLETE/PARTIAL/FAILED|Execution coverage, never legal sufficiency|
|evidence|tuple[AggregatedEvidence,...]|Payload groups with all native occurrences|
|warnings|tuple[str,...]|Deduplicated codes; richer warnings remain in responses|
|errors|tuple[RetrievalErrorDetail,...]|Classified backend failures|
|skipped_subqueries|tuple[int,...]|Zero-based unexecuted query indices|
|executed_searches|int|Actual backend calls, excludes exact cache hits|

NOT_STARTED with clarification: no reads. COMPLETE may have zero evidence. PARTIAL may contain only prior NO_MATCH plus failure; inspect actual evidence rather than assuming nonempty. Unexpected exceptions/cancellation do not guarantee a returned SearchState.

## Executed JSON examples and origins

All examples below are from CURRENT CONTROLLED execution using stored native evidence as fixture; none is a new live search. Raw provider replay uses original Q004 response from historical live Gemini; deterministic postprocessing is current code. Full examples retained in execution.json, not duplicated here in full.

### SearchOptions (trusted fixture context)

```json
{
  "mode": "bm25",
  "top_k": 3,
  "as_of_date": "2026-11-23",
  "allowed_usage_policies": [
    "EXPERIMENTAL_ONLY"
  ]
}
```

### QueryPlan from saved real Gemini raw replay

```json
{
  "original": "Tôi ký hợp đồng lao động 2 năm, mới làm được 6 tháng nhưng muốn nghỉ việc. Tôi có phải báo trước không và có phải bồi thường không?",
  "intent": "legal_question",
  "domain": "labour",
  "temporal_scope": [
    "2 năm",
    "6 tháng"
  ],
  "subqueries": [
    {
      "text": "người lao động đơn phương chấm dứt hợp đồng lao động xác định thời hạn nghĩa vụ báo trước; tình huống người dùng: Tôi ký hợp đồng lao động 2 năm; mới làm được 6 tháng nhưng muốn nghỉ việc",
      "purpose": "question_part"
    },
    {
      "text": "người lao động đơn phương chấm dứt hợp đồng lao động trái pháp luật nghĩa vụ bồi thường; tình huống người dùng: Tôi ký hợp đồng lao động 2 năm; mới làm được 6 tháng nhưng muốn nghỉ việc",
      "purpose": "question_part"
    }
  ],
  "clarification": null,
  "analysis_method": "llm",
  "analysis_model": "gemini-3.5-flash-lite",
  "facts": [
    {
      "text": "Tôi ký hợp đồng lao động 2 năm",
      "source_quote": "Tôi ký hợp đồng lao động 2 năm"
    },
    {
      "text": "mới làm được 6 tháng nhưng muốn nghỉ việc",
      "source_quote": "mới làm được 6 tháng nhưng muốn nghỉ việc"
    }
  ],
  "issues": [
    "Nghĩa vụ báo trước khi người lao động đơn phương chấm dứt hợp đồng lao động xác định thời hạn",
    "Nghĩa vụ bồi thường chi phí đào tạo hoặc vi phạm thời hạn báo trước khi người lao động nghỉ việc"
  ],
  "missing_information": [
    "Loại hợp đồng lao động xác định thời hạn có thỏa thuận chi phí đào tạo hay không",
    "Người lao động đơn phương chấm dứt hợp đồng có tuân thủ đúng thời hạn báo trước hay không",
    "Bạn muốn nghỉ việc vì lý do gì?"
  ],
  "citations": [],
  "temporal_context": [
    {
      "text": "2 năm",
      "start": 25,
      "end": 30,
      "role": "duration",
      "iso_date": null,
      "negated": false
    },
    {
      "text": "6 tháng",
      "start": 45,
      "end": 52,
      "role": "duration",
      "iso_date": null,
      "negated": false
    }
  ],
  "search_objectives": [
    {
      "query_index": 0,
      "issue_indices": [
        0
      ]
    },
    {
      "query_index": 1,
      "issue_indices": [
        1
      ]
    }
  ],
  "planning_warnings": []
}
```

### Reference from controlled exact lookup

```json
[
  {
    "kind": "article",
    "text": "Điều 35",
    "start": 8,
    "end": 15,
    "source": "user_supplied_unverified"
  },
  {
    "kind": "document",
    "text": "45/2019/QH14",
    "start": 33,
    "end": 45,
    "source": "user_supplied_unverified"
  }
]
```

### EvidenceOccurrence from replay fixture

```json
{
  "subquery_index": 0,
  "response_index": 0,
  "query": "người lao động đơn phương chấm dứt hợp đồng lao động xác định thời hạn nghĩa vụ báo trước; tình huống người dùng: Tôi ký hợp đồng lao động 2 năm; mới làm được 6 tháng nhưng muốn nghỉ việc",
  "request_id": "cfc805a2-0fae-47bf-a08d-184827c217d0",
  "rank": 1,
  "raw_score": 34.4547420111624,
  "score_kind": "BM25",
  "issue_indices": [
    0
  ]
}
```

### Complete SearchState for controlled NO_MATCH

```json
{
  "plan": {
    "original": "Điều kiện để hợp đồng dân sự có hiệu lực là gì?",
    "intent": "legal_question",
    "domain": "unknown",
    "temporal_scope": [],
    "subqueries": [
      {
        "text": "Điều kiện để hợp đồng dân sự có hiệu lực là gì",
        "purpose": "question_part"
      }
    ],
    "clarification": null,
    "analysis_method": "deterministic",
    "analysis_model": null,
    "facts": [],
    "issues": [],
    "missing_information": [],
    "citations": [],
    "temporal_context": [],
    "search_objectives": [],
    "planning_warnings": []
  },
  "requests": [
    {
      "query": "Điều kiện để hợp đồng dân sự có hiệu lực là gì",
      "mode": "bm25",
      "top_k": 3,
      "as_of_date": "2026-11-23",
      "allowed_usage_policies": [
        "EXPERIMENTAL_ONLY"
      ]
    }
  ],
  "responses": [
    {
      "schema_version": "1",
      "request_id": "cfc805a2-0fae-47bf-a08d-184827c217d0",
      "query": "Điều kiện để hợp đồng dân sự có hiệu lực là gì",
      "query_used": "Điều kiện để hợp đồng dân sự có hiệu lực là gì",
      "mode": "bm25",
      "top_k": 3,
      "as_of_date": "2026-11-23",
      "allowed_usage_policies": [
        "EXPERIMENTAL_ONLY"
      ],
      "selected_index_name": "vbpl-bm25-unicode-v1",
      "index": {
        "id": "2acb41da-84af-4e7b-95b6-00faa3f73528",
        "index_name": "vbpl-bm25-unicode-v1",
        "index_version": "v1",
        "status": "READY",
        "updated_at": "2026-11-14T08:27:10.966337Z",
        "algorithm": "BM25",
        "tokenizer": "unicode-nfc-lower-v1"
      },
      "status": "NO_MATCH",
      "evidence": [],
      "warnings": [],
      "error": null,
      "retrieved_at": "2026-11-23T10:45:12.359301Z",
      "consistency": "BEST_EFFORT"
    }
  ],
  "status": "COMPLETED",
  "completeness": "COMPLETE",
  "evidence": [],
  "warnings": [
    "NO_MATCH:0"
  ],
  "errors": [],
  "skipped_subqueries": [],
  "executed_searches": 1
}
```

### Partial-result projection (not a standalone complete SearchState)

```json
{
  "status": "FAILED",
  "completeness": "PARTIAL",
  "errors": [
    {
      "category": "DATABASE_FAILURE",
      "code": "FIXTURE_READ_FAILED",
      "stage": "fixture",
      "message": "Controlled acceptance fixture failure.",
      "retryable": false
    }
  ],
  "warnings": [
    "TEMPORAL_METADATA_INCOMPLETE",
    "SEARCH_INCOMPLETE"
  ],
  "skipped_subqueries": [
    2
  ],
  "executed_searches": 2
}
```

### Query errors from controlled executions

```json
[
  {
    "scenario": "invalid_input",
    "code": "QUERY_INPUT_LENGTH"
  },
  {
    "scenario": "invalid_json",
    "code": "QUERY_ANALYSIS_INVALID_RESPONSE",
    "search_calls": 0
  },
  {
    "scenario": "provider_timeout",
    "code": "QUERY_ANALYSIS_TIMEOUT",
    "search_calls": 0
  },
  {
    "scenario": "provider_error",
    "code": "QUERY_ANALYSIS_PROVIDER_ERROR",
    "search_calls": 0
  }
]
```

## Contract acceptance limit

Current controlled contract_probes.json records extra QueryPlan field ignored and an oversized end offset accepted for an externally constructed suffix reference. QueryPlan validates slice text and index relationships, not every possible trust invariant. Standard planner spans do not exhibit that probe; no production behavior changed. If ingesting plans from outside the trusted planner, establish the required trust/validation boundary explicitly. Do not treat QueryPlan.model_validate as provider grounding or authoritative citation verification.
