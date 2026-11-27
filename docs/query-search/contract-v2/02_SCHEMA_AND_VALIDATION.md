# Schema and validation

All V2 models: Pydantic extra=forbid/frozen. Freezing is shallow: embedded V1 models/containers remain V1 types. Entrypoints rebuild/validate envelopes and registry bindings before execution; original input is reserved immutably in registry. Do not mutate nested V1 data or treat model parsing alone as a security/grounding guarantee.

Required means a key is mandatory; nullable does not mean omitted. Models below are actual current definitions.

## ClarificationAnswer

|Field|Required|Default|JSON type/constraints|
|---|---|---|---|
|answer_id|True|"required"|`{"minLength": 1, "type": "string"}`|
|text|True|"required"|`{"maxLength": 10000, "minLength": 1, "type": "string"}`|
|source|False|"user"|`{"const": "user", "type": "string"}`|

## QueryContextV2

|Field|Required|Default|JSON type/constraints|
|---|---|---|---|
|request_id|True|"required"|`{"minLength": 1, "type": "string"}`|
|revision|False|"1"|`{"minLength": 1, "type": "string"}`|
|workflow_mode|False|"qa"|`{"enum": ["qa", "verify"], "type": "string"}`|
|options|True|"required"|`{"$ref": "#/$defs/SearchOptions"}`|
|jurisdiction|False|"VN"|`{"enum": ["VN", "unknown"], "type": "string"}`|
|clarification_answers|False|[]|`{"items": {"$ref": "#/$defs/ClarificationAnswer"}, "type": "array"}`|

## IssueReference

|Field|Required|Default|JSON type/constraints|
|---|---|---|---|
|issue_id|True|"required"|`{"type": "string"}`|
|issue_index|True|"required"|`{"minimum": 0, "type": "integer"}`|

## ClaimReference

|Field|Required|Default|JSON type/constraints|
|---|---|---|---|
|claim_id|True|"required"|`{"type": "string"}`|
|text|True|"required"|`{"minLength": 1, "type": "string"}`|
|source_id|False|"original"|`{"type": "string"}`|
|start|True|"required"|`{"minimum": 0, "type": "integer"}`|
|end|True|"required"|`{"exclusiveMinimum": 0, "type": "integer"}`|
|citation_ids|False|[]|`{"items": {"type": "string"}, "type": "array"}`|

## CitationTarget

|Field|Required|Default|JSON type/constraints|
|---|---|---|---|
|citation_id|True|"required"|`{"type": "string"}`|
|raw_text|True|"required"|`{"minLength": 1, "type": "string"}`|
|source_id|False|"original"|`{"type": "string"}`|
|start|True|"required"|`{"minimum": 0, "type": "integer"}`|
|end|True|"required"|`{"exclusiveMinimum": 0, "type": "integer"}`|
|unresolved_fields|False|[]|`{"items": {"type": "string"}, "type": "array"}`|
|resolution_status|False|"unresolved"|`{"const": "unresolved", "type": "string"}`|

## QueryEntry

|Field|Required|Default|JSON type/constraints|
|---|---|---|---|
|query_id|True|"required"|`{"type": "string"}`|
|subquery_index|True|"required"|`{"minimum": 0, "type": "integer"}`|
|purpose|True|"required"|`{"enum": ["find_support", "resolve_citation"], "type": "string"}`|
|issue_ids|False|[]|`{"items": {"type": "string"}, "type": "array"}`|
|claim_ids|False|[]|`{"items": {"type": "string"}, "type": "array"}`|
|citation_ids|False|[]|`{"items": {"type": "string"}, "type": "array"}`|

## QueryEnvelopeV2

|Field|Required|Default|JSON type/constraints|
|---|---|---|---|
|contract_version|False|"2"|`{"const": "2", "type": "string"}`|
|scope_id|True|"required"|`{"pattern": "^[0-9a-f]{32}$", "type": "string"}`|
|context|True|"required"|`{"$ref": "#/$defs/QueryContextV2"}`|
|legacy_plan|True|"required"|`{"$ref": "#/$defs/QueryPlan"}`|
|issues|False|[]|`{"items": {"$ref": "#/$defs/IssueReference"}, "type": "array"}`|
|claims|False|[]|`{"items": {"$ref": "#/$defs/ClaimReference"}, "type": "array"}`|
|citations|False|[]|`{"items": {"$ref": "#/$defs/CitationTarget"}, "type": "array"}`|
|queries|False|[]|`{"items": {"$ref": "#/$defs/QueryEntry"}, "type": "array"}`|

## EvidenceLink

|Field|Required|Default|JSON type/constraints|
|---|---|---|---|
|evidence_id|True|"required"|`{"type": "string"}`|
|query_id|True|"required"|`{"type": "string"}`|
|group_index|True|"required"|`{"minimum": 0, "type": "integer"}`|
|occurrence_index|True|"required"|`{"minimum": 0, "type": "integer"}`|
|issue_ids|False|[]|`{"items": {"type": "string"}, "type": "array"}`|
|claim_ids|False|[]|`{"items": {"type": "string"}, "type": "array"}`|
|citation_ids|False|[]|`{"items": {"type": "string"}, "type": "array"}`|
|purpose|False|"support_suggestion"|`{"const": "support_suggestion", "type": "string"}`|
|resolution_status|False|"unresolved"|`{"const": "unresolved", "type": "string"}`|
|legal_validity|False|"unknown"|`{"const": "unknown", "type": "string"}`|
|url_access|False|"not_attempted"|`{"const": "not_attempted", "type": "string"}`|

## QueryOutcome

|Field|Required|Default|JSON type/constraints|
|---|---|---|---|
|query_id|True|"required"|`{"type": "string"}`|
|status|True|"required"|`{"enum": ["retrieved", "no_match", "failed", "skipped", "unavailable"], "type": "string"}`|
|reason|False|null|`{"anyOf": [{"type": "string"}, {"type": "null"}]}`|

## SearchEnvelopeV2

|Field|Required|Default|JSON type/constraints|
|---|---|---|---|
|contract_version|False|"2"|`{"const": "2", "type": "string"}`|
|query|True|"required"|`{"$ref": "#/$defs/QueryEnvelopeV2"}`|
|legacy_state|True|"required"|`{"anyOf": [{"$ref": "#/$defs/SearchState"}, {"type": "null"}]}`|
|status|True|"required"|`{"enum": ["completed", "failed", "clarification_required", "unavailable"], "type": "string"}`|
|evidence_links|False|[]|`{"items": {"$ref": "#/$defs/EvidenceLink"}, "type": "array"}`|
|query_outcomes|True|"required"|`{"items": {"$ref": "#/$defs/QueryOutcome"}, "type": "array"}`|

## Cross-field rules

- Context owns trusted options, request_id/revision and qa/verify business mode; request/revision must not be blank. Answer IDs are unique and cannot shadow original. Text is user provenance, not verified fact.
- IDs match opaque scope:kind:UUID and unique keys; issue maps cover actual legacy issues, query entries cover all native subqueries. All targets must exist in the same envelope. Runtime registry additionally rejects unissued IDs or different context; correct-format forged IDs are not executable.
- Claims/citations require exact source slices with explicit finite bounds. Original source offsets use NFC/trimmed question; clarification offsets use answer text exactly as supplied. Unknown source refs and oversized end offsets rejected in V2. No LLM Verify extraction is supplied.
- CitationTarget deliberately stores raw literal plus unresolved fields, not guessed canonical document/article/version. Claim citation IDs may be empty; facts never auto-convert to claims.
- Registry binds entity ID content after validation; changed text/targets cannot reuse a bound ID. Issue/query reordering can retain identity by content and explicit occurrence keys. Different revisions/registry instances have independent scopes.
- Search state plan/options/status, native response counts and every expected support occurrence link must agree. Lost/duplicate links, conflicting group E IDs, dangling queries and mismatched outcome statuses reject. Retrieval outcomes use retrieved/no_match/failed/skipped; exact resolution is always unavailable in this foundation.
- Null legacy_state is required explicitly for unavailable and cannot carry evidence links. Legal validity unknown, URL access not_attempted, citation resolution unresolved are constrained literals, not inferred from rank.

## Ownership

Backend supplies trusted context; caller retains registry; application code issues IDs. QA planner produces legacy plan. Controlled claim/citation fixtures are caller metadata, not output from a new extractor. Search adapter issues evidence IDs/links from actual native state. Legal validation and URL checks remain future owners.
