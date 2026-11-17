> Publication note: the saved retrieval-e2e-evidence.json contains 8 scenarios: six service scenarios and CLI BM25/Dense. Historical claims below about CLI Hybrid or live fault scenarios are not corroborated by that artifact. No live scenarios were rerun for this publication.

# Live legacy compatibility verification — 2026-11-14

## Connection: PASS

Loaded configuration through `src.core.config.load_settings()`, including its existing
dotenv flow. No credential values were printed, logged or included here. Configuration
contains the Supabase URL/API key and DATABASE_URL. The PostgreSQL host/user project
identifier matches the configured Supabase API project identifier. This confirms internal
configuration agreement; no separate externally supplied project identifier was available.

Used a separate psycopg connection, not FastAPI startup or application lifespan.
Connection options enforced `default_transaction_read_only=on`; before dataset queries,
executed `BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY` and confirmed
`transaction_read_only=on`. Statement timeout: 45 seconds. Transaction ended with rollback.
Existing credentials need not be read-only because PostgreSQL enforced read-only execution.
Savepoints isolated query errors; no application RPCs were invoked.

Initial sandbox attempt returned OperationalError without SQLSTATE. Retrying outside the
sandbox through execution approval succeeded. Configuration loading and project matching
already succeeded inside the sandbox. No evidence of database corruption or missing data.
The exact low-level cause of the sandbox OperationalError was not exposed; successful
external execution resolves the access blocker for this audit.

Executed all 27 SELECT statements in `legacy-data-compatibility-selects.sql`, in one snapshot.
Evidence: [legacy-data-live-evidence.json](legacy-data-live-evidence.json).
This report supersedes the no-connection/counts-UNKNOWN conclusions in the earlier
`legacy-data-compatibility-audit.md`; its design-only precautions remain relevant.

## Actual dataset and integrity

| Measure | Observed |
|---|---:|
| Source documents | 58 |
| Canonical VBPL sources | 58 |
| Additional VBPL URL candidates with different source ID | 0 |
| Document structures | 37 |
| Retrieval chunks, all VBPL | 2,609 |
| Sources without structure and without chunks | 21 |
| Structures without chunks | 0 |
| Chunk integrity failures (full L4 scan) | 0 |
| Duplicate structure/chunk-key groups | 0 |
| Orphan structures, sparse documents, postings, embeddings | 0 |

All 37 structures declare schema `legal-structure-v1`, parser `vbpl-markdown-v7`.
Thus the populated current-schema chunk cohort is already on the current parser version;
the claim that these particular chunks necessarily use an older parser is not supported.
L4 verified stored content SHA-256, source/structure identity, required metadata fields,
offset bounds and node/block references. This does not evaluate legal text quality.

## Stored source recovery

All 58 sources have stored_files arrays; none malformed. No inline raw content.
54 sources have raw_file_ref; 5 have raw_content_ref (overlap possible; do not sum as sources).
All those references match visible Storage catalog entries.
37 sources have normalized Markdown references, all matching catalog objects and recorded
SHA-256 matching structure content hashes. Another 127 stored-files entries with NULL role
span 58 sources, all with catalog matches and SHA-256-format metadata.

No Storage bytes were downloaded, so catalog/hash metadata agreement is not a byte-level
file integrity or conversion-success test. The 21 unchunked sources are not proven lost:
all sources have stored-file catalog references. Their exact file formats and conversion
suitability require targeted inspection before assigning C or D. No recrawl is justified yet.

## BM25

Index `vbpl-bm25-unicode-v1`: READY, BM25, tokenizer `unicode-nfc-lower-v1`,
language simple, version v1, k1=1.2, b=0.75.

- Sparse documents: 2,609, all INDEXED.
- Chunks with postings and matching indexed text hash: 2,609/2,609 (100%).
- Posting rows: 159,111.
- Stored/recomputed document count: 2,609.
- Stored/recomputed token count: 253,964.
- Stored/recomputed average length: 97.3415101571483.
- Token-count/TF-sum mismatches: 0; invalid TF/positions by L7 checks: 0.

**No evidence requiring BM25 re-indexing.** Existing chunks/postings are directly reusable
at the SQL/data-contract level (A candidate). Tokenizer metadata and aggregate checks do
not prove exact token-by-token equivalence; no live RetrievalService search was executed.
Final end-to-end A acceptance still requires read-only query/hydration verification.

## Dense

Index `vbpl-multilingual-e5-small-v1`: READY, provider sentence-transformers,
model intfloat/multilingual-e5-small, cosine, version v1, dimension 384.
Index metadata declares normalized=true, passage prefix `passage: `, query prefix `query: `.
All 2,609 vectors are INDEXED, actually 384-dimensional and carry E5 model-name metadata.
All match SHA-256 of `passage: ` + current chunk content and normalization tolerance 1e-4.
Observed norms: 0.999999908852863–1.00000012895924.
Missing/numerically incompatible/hash-mismatching target vectors: 0.

Index revision/model_revision/checkpoint_revision/pooling/max_seq_length fields are NULL;
checked vector revision fields are also NULL. Metadata `prefix='passage:'` is consistent
with the source writer stripping the trailing space in metadata, while hashing actual input
with `passage: `.

**E — checkpoint compatibility UNKNOWN:** model-name, numeric and content-hash evidence
is strong but does not prove weights identity or checkpoint revision. Do not automatically
re-encode; first recover embedding-run manifest/revision/tokenizer/pooling provenance and
compare to the local query checkpoint. No model was loaded/downloaded and no embeddings made.

## RPC and filters

All six expected retrieval/getter RPCs exist with current signatures, STABLE volatility,
SECURITY INVOKER, service_role EXECUTE=true and anon EXECUTE=false. Catalog verification
does not verify function bodies, HTTP authentication/RLS visibility or actual service behavior.
All 58 sources have policy EXPERIMENTAL_ONLY; no invalid date ranges. Two have NULL start
dates and 54 have NULL end dates. Queries must explicitly choose date/policy; stored chunks
are not necessarily eligible at every date.

## Compatibility decision and minimal reuse plan

| Cohort/branch | Decision | Minimal next action |
|---|---|---|
| Existing 2,609 chunks / 37 structures | A at storage/contract level | Preserve UUIDs, content and structures; do not reparse |
| BM25 over those chunks | A candidate, SQL_VERIFIED; runtime pending | Run read-only postings-derived query and compare RPC/service hydration; no re-index justified |
| Dense over those chunks | E for complete checkpoint compatibility | Recover revision/provenance; retain current vectors pending evidence |
| Hybrid | E, runtime pending | Verify BM25 and Dense first, then independently compare RRF |
| 21 sources without structures/chunks | E, processing need not yet classified | Inspect existing stored files/conversion metadata; if suitable sources and no reusable legacy chunks, design small parse-only trial |
| B INDEX_ONLY_REQUIRED | No cohort proven | Existing target coverage is complete; do not schedule blanket indexing |
| C REPARSE_REQUIRED | No cohort proven | Different versions/absence of chunks alone do not justify replacing current chunks |
| D SOURCE_RECOVERY_REQUIRED | No cohort proven | Stored assets exist in catalog; investigate before any recovery/recrawl plan |

Before any separately authorized reparse/write task, backup exact UUIDs/relationships,
chunks, index rows and source assets; inventory citations. Current parsed-save replaces chunks,
which can change UUIDs, cascade-delete postings/vectors and mark READY indexes STALE.
Prefer reuse and branch-specific work over re-ingestion. No migration/indexing/recovery executed.

## Verification boundaries

Connection and actual counts: PASS. SQL audit: SQL_VERIFIED for executed SELECTs and their
observed results. Existing chunk integrity and numeric/index coverage: PASS as scoped above.
LIVE_INTEGRATION_VERIFIED for RetrievalService/CLI: not achieved in this data audit.
Dense revision compatibility: UNKNOWN; retrieval runtime RUNTIME_UNVERIFIED;
semantic quality QUALITY_NOT_EVALUATED. Prior unit results do not replace these distinctions.

Only local documentation/evidence artifacts were added. No application code, environment,
credentials, database data, schema, Storage or index statuses were modified.


## Addendum — actual RetrievalService and CLI E2E (2026-11-14)

This section supersedes the earlier runtime-unverified status for the executed technical scenarios. It reuses the baseline audit; the 27 SELECT statements were not repeated.

### Independent status

| Status | Result | Evidence |
|---|---|---|
| BM25_SQL_VERIFIED | PASS | Prior coverage audit; current direct SQL chunk IDs/order/scores equal live service |
| BM25_E2E_VERIFIED | PASS | Actual text → request → tokenizer → adapters → RPC → hydration; CLI also passes |
| DENSE_SQL_VERIFIED | PASS (numeric/hash scope) | Prior complete 2,609-vector audit, current READY metadata |
| DENSE_TECHNICAL_E2E_VERIFIED | PASS | Actual local encoder and real pgvector RPC; CLI also passes |
| DENSE_MODEL_COMPATIBILITY_VERIFIED | BLOCKED | Corpus checkpoint revision/weights provenance not recovered |
| HYBRID_E2E_VERIFIED | PASS (technical) | Both real branches, independent RRF/dedup/order and strict failure verified |
| RETRIEVAL_QUALITY_EVALUATED | BLOCKED | No labeled relevance evaluation |

Overall unrestricted Retrieval verification remains **BLOCKED** on model compatibility and quality; all three technical E2E paths passed their executed scenarios.

### Execution environment, safety and configuration

Configuration was loaded through existing `load_settings()`; identifiers in API URL and PostgreSQL connection agree. Both target indexes were rechecked READY with the same updated_at values as the baseline. No dataset-wide recount was performed.

The production CLI still calls `load_settings(environ=os.environ)`. The verification launcher first calls normal `load_settings()`, which provisions dotenv variables into its process, then runs the unchanged CLI through `runpy` in a fresh subprocess. No service_factory/fake service was supplied. API key/connection string values never appear in commands or evidence.

SQL seed/comparison reads used a separate PostgreSQL REPEATABLE READ READ ONLY transaction with default_transaction_read_only=on and rollback. HTTP adapter calls used the real SDK RPC implementation with verification-only `get=True` instrumentation. PostgreSQL/PostgREST GET RPC mode is read-only; a transport guard rejects every non-GET request and every RPC outside the six-name retrieval allowlist. Array parameters were serialized as equivalent PostgreSQL array literals for GET.

This is E2E of the unchanged service, tokenizer/encoder, repository mappings and actual RPCs under read-only transport instrumentation. The default POST transport of the unwrapped CLI was not executed or verified. No production source, credentials, data, schema or statuses changed. No app/worker/migration/ingestion/indexer was started.

Local inference used the provisioned snapshot `614241f622f53c4eeff9890bdc4f31cfecc418b3`, CPU/local_files_only, offline environment flags. The model was warmed before service tests; standalone CLI runs loaded their model independently. No download occurred.

### Inputs and evidence

- Seed chunk: `0029f385-4290-4359-bf32-87aea3da43cc` (eligible stored chunk with existing postings).
- Exact text query derived from its stored content using the actual tokenizer: `văn bản hợp nhất 60 2026 vbhn nđ`.
- Date: `2026-11-14`; policy: `EXPERIMENTAL_ONLY`; top-k=5.
- Hybrid budgets: BM25=5, Dense=5, RRF k=60.
- Finite query vector: 384 dimensions, norm 1.0000000200572066; actual query encoder source applies `query: ` prefix.
- Evidence artifact: [retrieval-e2e-evidence.json](retrieval-e2e-evidence.json); includes per-test request context, relevant response fields, UUIDs/ranks/scores, errors/warnings and observed RPC call sequences. Full legal text and arbitrary source metadata were not persisted.

| Test | Result | Evidence count / observation |
|---|---|---|
| bm25_hits | OK | 5 evidence |
| bm25_filter_no_match | NO_MATCH | 0 evidence |
| dense_hits | OK | 5 evidence |
| dense_filter_no_match | NO_MATCH | 0 evidence |
| hybrid_hits | OK | 5 evidence |
| hybrid_filter_no_match | NO_MATCH | 0 evidence |
| cli_bm25 | OK | 5 evidence; exit 0 |
| cli_dense | OK | 5 evidence; exit 0 |
| cli_hybrid | OK | 5 evidence; exit 0 |
| bm25_invalid_request | REJECTED | validation boundary |
| bm25_controlled_missing_index | FAILED | zero partial evidence |
| cli_bm25_invalid | FAILED | validation boundary; exit 2 |
| dense_invalid_request | REJECTED | validation boundary |
| dense_controlled_missing_index | FAILED | zero partial evidence |
| cli_dense_invalid | FAILED | validation boundary; exit 2 |
| hybrid_invalid_request | REJECTED | validation boundary |
| hybrid_controlled_missing_index | FAILED | zero partial evidence |
| cli_hybrid_invalid | FAILED | validation boundary; exit 2 |

### Observed rankings


bm25:

| Rank | Chunk UUID | Score | Kind |
|---|---|---|---|
| 1 | 4bf655a2-a1f7-427e-aea9-ddb952b18b85 | 13.9595546836106 | BM25 |
| 2 | 09982b9b-cfc7-4b57-a656-9ca8daa369fc | 13.7857169260629 | BM25 |
| 3 | 69019f42-d59c-45ce-9313-9c4c9153b1b2 | 13.4507145414879 | BM25 |
| 4 | 4e25db41-5d45-49b3-bce5-978dfa7a7385 | 12.9776652791903 | BM25 |
| 5 | 46ccc6eb-69e4-4926-90ba-3fafc3b4440e | 12.6803608581204 | BM25 |

dense:

| Rank | Chunk UUID | Score | Kind |
|---|---|---|---|
| 1 | e72ce95a-258b-4f3b-9cba-18c9117a1d3c | 0.899065381344238 | COSINE_SIMILARITY |
| 2 | 2244d304-77d2-4796-b843-548bea0a3c0e | 0.898479169697813 | COSINE_SIMILARITY |
| 3 | 67c18b69-c5c5-4ab9-abac-0294b5b7ba0f | 0.897835916409737 | COSINE_SIMILARITY |
| 4 | 09982b9b-cfc7-4b57-a656-9ca8daa369fc | 0.896894467247198 | COSINE_SIMILARITY |
| 5 | 4bf655a2-a1f7-427e-aea9-ddb952b18b85 | 0.891103393369712 | COSINE_SIMILARITY |

hybrid:

| Rank | Chunk UUID | Score | Kind |
|---|---|---|---|
| 1 | 4bf655a2-a1f7-427e-aea9-ddb952b18b85 | 0.03177805800756621 | RRF |
| 2 | 09982b9b-cfc7-4b57-a656-9ca8daa369fc | 0.031754032258064516 | RRF |
| 3 | e72ce95a-258b-4f3b-9cba-18c9117a1d3c | 0.01639344262295082 | RRF |
| 4 | 2244d304-77d2-4796-b843-548bea0a3c0e | 0.016129032258064516 | RRF |
| 5 | 67c18b69-c5c5-4ab9-abac-0294b5b7ba0f | 0.015873015873015872 | RRF |

### Verification details and scenario limits

BM25 SQL comparison was exact for UUID/order/scores. For all successful service responses, targeted SQL reads confirmed content equality, SHA-256, source/structure IDs and chunk metadata equality. All captured service/CLI hit responses pass consecutive-rank, unique-UUID, nonincreasing-score and date/policy checks. Service performs its real source hydration and integrity gates. CLI UUIDs and scores equal their corresponding service results.

Independent Hybrid recomputation used the full five-candidate lists from the separately executed BM25 and Dense branches, not only final contributions: sum(1/(60+rank)), sort descending then UUID ascending, truncate five. Final UUIDs and scores match within 1e-12. CLI repeats the same output, providing a second ordering observation.

NO_MATCH was produced by an explicitly nonexistent policy allowlist, not a nonsense Dense query. Invalid top-k=0 requests were rejected before service/database operations; the real CLI returned INVALID_ARGUMENTS/exit 2 in each mode.

Unavailable-index tests changed only the private index-name field on a newly created verification service instance to `audit-deliberately-unavailable-index`. The database returned no index row through real GET RPC. BM25/Dense/Hybrid all failed with zero evidence. For Hybrid the BM25 branch actually succeeded before Dense index lookup failed: strict no-partial-result behavior was observed without changing production infrastructure. These are controlled configuration faults, not claims that the production indexes were unavailable.

Database transport/RPC failure taxonomy uses the existing unit/fake evidence (200 tests from the earlier verification); no network outage was manufactured. This remains UNIT_VERIFIED, not a new live outage test. No semantic relevance, citation legal correctness or recall benchmark was performed.

### Checkpoint provenance investigation

Reused index/vector metadata from baseline: revision/model_revision/checkpoint_revision absent. Searched repository Markdown/JSON/Python artifacts for revision/checkpoint evidence and filenames for manifests/logs; no corpus embedding-run manifest or log establishing weights identity was found. Existing Task 5 documents the local snapshot only. The writer source loads model name without pinning revision, so matching names/dimensions and successful inference do not establish historical corpus revision. No model download or vector modification was attempted. Missing provenance is uncertainty, not proof of incompatibility.

### Reproduction and minimum next actions

Run from main with the existing venv and authorized network execution:

```powershell
.venv/Scripts/python.exe .docs/development/retrieval-e2e-verifier.py
.venv/Scripts/python.exe .docs/development/retrieval-e2e-scenarios.py
```

The first launcher records exact sanitized child CLI argv per mode in the evidence file. The second records invalid-request and controlled missing-index cases. Both are documentation-side verification tools, not product changes.

1. Preserve and reuse the existing 2,609 chunks/postings/vectors; no evidence in these runs justifies blanket reparse/re-index.
2. Recover corpus embedding-run revision/weights/tokenizer/pooling provenance and compare with local checkpoint. If unrecoverable, retain compatibility BLOCKED and design a separate bounded compatibility study; do not automatically re-encode.
3. If semantic quality is required, prepare labeled queries/expected sources and evaluate BM25/Dense/Hybrid separately. Technical hits do not establish quality improvement.
4. Separately inspect stored source assets for the 21 unchunked documents; these E2E tests concern the indexed cohort only.
