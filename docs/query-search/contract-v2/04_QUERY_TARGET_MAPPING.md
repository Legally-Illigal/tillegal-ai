# Request-scoped target identities

IdentityRegistry(context) allocates an opaque UUID scope plus opaque I/Q/C/R/E IDs. Backend request_id and revision are metadata; generated IDs do not embed user input, personal information or request_id. Keep ONE registry per active request/revision. Recreating registry even with the same request_id creates a different scope. JSON restoration alone does not restore registry issuance/bindings or promise cross-process persistence. Registry is intended for request-local application use, not a shared multi-session/thread store.

issue ID mapping follows actual legacy issue text/index. Identical text occurrences get disambiguation counters; distinct issue/query reordering retains IDs. Existing SearchObjective is the only source for automatic issue associations; absent legacy links stay empty. Projection is QA metadata only, not automatic claim extraction or citation grouping.

QueryEntry references subquery_index; query text remains ONLY in V1 subqueries. Multiple entries/purposes/claim targets can share one index; native exact-query caching remains one execution while all support target associations survive. ID-content bindings reject reuse for changed targets/text, so application must issue a new ID when semantics changes. Original input cannot change within registry, including after a provider error.

Controlled fixtures create ClaimReference/CitationTarget with registry.issue("C",key)/issue("R",key), grounded slices, then build QueryEnvelopeV2. This is an application-owned metadata API, not an assertion that the slice is truly atomic or legally correct. resolve_citation requires a citation target. Claim without citation is valid with citation_ids=(); no_citation verdict belongs to future Verification.

[Actual examples](EXAMPLES.json) include a user claim and ambiguous raw Điều35 citation, two purposes on one subquery. Verify returns unavailable without retrieval; it never assigns a top result as original citation. Citation raw text/status remains unchanged if QA support evidence is available from a separately declared support entry.
