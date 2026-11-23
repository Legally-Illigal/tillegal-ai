# Limitations and ownership

Verdicts apply specifically to Query/Search technical handoff. Production execution has no demonstrated blocking defect in the documented planner→Search path. Acceptance is READY WITH LIMITATIONS, not whole-system completion. Prior corpus/ranking observations do not prove another owner's implementation is defective.

|Issue|Owner/boundary|Priority|Status|Evidence/interpretation|
|---|---|---|---|---|
|Query grounding variability/Q007|Query/Search|P2|READY WITH LIMITATIONS|Historical primary source-quote mismatch rejected; current error tests pass. No new success claimed; safety behavior preserved.|
|Narrow missing-information/domain/issue quality|Query/Search|P2|READY WITH LIMITATIONS|domain only labour/unknown, slot regexes narrow, prior MI proxy7/12. No completeness guarantee.|
|External manual-plan schema boundary|Query/Search + integrator trust boundary|P2 for external plans; nonblocking standard path|READY WITH LIMITATIONS|Current probe accepts end145 for actual end45 suffix and ignores unknown fields. Parser spans correct; schema parsing alone does not rerun grounding. No production change authorized absent blocking normal-path defect.|
|Exact-source warning scope|Query/Search + future consumer|P2|READY WITH LIMITATIONS|Only quote_lookup/document-number/title check, no authoritative article matching; Q025 legal_question not guaranteed warning.|
|Source identities/coverage|Corpus/Ingestion|P1 for supported legal use cases|BLOCKED for corpus sufficiency|Historical complete visible58 metadata rows and exact probe lack45/2019 identity; only local-resolution chunk mentions it. Not global semantic absence.|
|Effectivity metadata|Corpus/Ingestion|P1 for historical applicability|BLOCKED for legal applicability|Q0192010 request received2026 source with null effective range. Metadata uncertain, not evidence of a Search orchestration bug.|
|Ranking/candidate relevance|Retrieval evaluation with corpus/legal reviewer|P2|READY WITH LIMITATIONS operationally; quality inconclusive|All4 modes worked historically, topical mismatches remain. No verified algorithm implementation defect or expert relevance truth.|
|Expert relevance labels|Evaluation/legal reviewer|P1 for expert quality claims|BLOCKED for expert P@K/NDCG|57 reused and280 experimental rows null; assistant observations separate. Relevance is distinct from legal correctness.|
|Cold checkpoint initialization|Retrieval/operations|P2|READY WITH LIMITATIONS|Historical E5~15.7s/CE~3.25s initialization; local-only checkpoints/deadlines matter. No installation/download in acceptance.|
|Correct partial/error/legacy/subtype JSON consumption|Future integration owner|P1 at integration boundary|READY WITH LIMITATIONS|Contracts tested; consumer must honor skipped queries/empty mappings/uncertainty, serialize subtype fields with serialize_as_any=True and restore native response subtype for JSON input.|
|Legal answer/verification|Future integration/verification owner|P1 for legal-answer release|BLOCKED outside this handoff|No correctness/applicability validation supplied by Query/Search; no Judge/Answer/Verification or graph changes.|

## Acceptance by capability

READY: deterministic planner startup, explicit Gemini configuration path (mock-tested), Search request mapping/cache/provenance, typed errors/partial semantics and existing graph compatibility.

READY WITH LIMITATIONS: both agents as technical modules; semantic completeness, externally constructed plans, citation-title uncertainty, dependency/model/deadline provisioning and caller interpretation.

BLOCKED: expert ranking metrics, corpus adequacy for the inspected questions and historical/legal applicability verification. These do not mean the Query/Search code cannot be handed off; they limit what a consumer may claim from its output.

No additional optimization project initiated. Existing owners receive concrete evidence and boundaries, not speculative defect assignments. No change to scoring/schema/corpus/graph/other agents was made.
