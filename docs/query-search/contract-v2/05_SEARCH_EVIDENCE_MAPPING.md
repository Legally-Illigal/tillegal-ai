# Actual SearchState → V2 view

Evidence adapter iterates existing aggregate groups and native occurrences, without changing order or scores. For each support QueryEntry matching occurrence.subquery_index it creates a separate EvidenceLink with group_index/occurrence_index/query ID and declared issue/claim/citation target IDs. The native fields, rank/raw_score/score_kind/request_id/chunk/source IDs and metadata remain in legacy_state; links use validated pointers rather than duplicating them independently.

E ID registry key is the same full payload distinction used for aggregation: exclude query-local rank/raw_score/score_kind/retrieval_method, retain source/structure/snapshot/content hash/dates/metadata. Conflicting versions sharing a native chunk UUID remain separate groups/E IDs. Same payload through multiple query occurrences shares E ID but retains every occurrence/target. IDs stable while the same registry is retained, not globally across processes.

All links have purpose support_suggestion, resolution_status unresolved, legal_validity unknown and url_access not_attempted. No resolver is implemented; resolve_citation entries receive EXACT_RESOLVER_UNAVAILABLE and NEVER inherit support links. This foundation cannot produce original_citation_source/resolved claims. A source URL is stored provenance, not HTTP success.

Native failures, warnings, no-match, skipped_subqueries and completeness remain in legacy_state. QueryOutcome mirrors response status or skipped; COMPLETE is execution only, including empty evidence. Clarification can be NOT_STARTED with skipped outcomes. View-only evidence_view validates its supplied plan/options but performs no I/O; caller must supply actual trusted SearchState, not externally fabricated material.

## JSON

Use result.to_json(), which sets serialize_as_any=True. Restore using SearchEnvelopeV2.model_validate_json(...). The before-validator reconstructs RerankedHybridRetrievalResponse when reranking is present, HybridRetrievalResponse when fusion is present, otherwise RetrievalResponse. Default base-type serialization can lose extension fields; do not use it as a native archive. All four backend variants were round-trip tested with fake read/model ports.

Full controlled QA output is in [EXAMPLES.json](EXAMPLES.json), including native ranks/metadata/links. There are no live provider calls or database reads in generating this artifact.
