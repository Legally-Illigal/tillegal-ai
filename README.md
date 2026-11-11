# tillegal-ai
Tillegal - Phần AI Service của hệ thống, repo nhằm triển khai chi tiết cho hệ thống AI.

The directory tree below is the agreed target structure currently being implemented. It describes the intended architecture; some listed modules may not exist in the working code yet.

## VBPL daily crawl API

The API accepts a date (default: today in `Asia/Ho_Chi_Minh`), creates a durable `crawl_jobs` row, and returns immediately.
The application worker claims the job with a PostgreSQL lease, scans the public sitemap index and all child sitemaps,
then fetches metadata and source files for matching document URLs.

```http
POST /ingestion/vbpl/crawl
Content-Type: application/json

{"crawl_date": "2026-11-09"}
```

Omit the body or `crawl_date` to use today's Vietnam date. The response is `202 Accepted` with a job ID; poll
`GET /ingestion/vbpl/jobs/{job_id}` for `PENDING`, `RUNNING`, `SUCCEEDED`, or `FAILED` and its result/error. Duplicate
requests for the same VBPL date reuse an already-active job. `DATABASE_URL`, `SUPABASE_URL`,
`SUPABASE_SERVICE_ROLE_KEY`, and the private `vbpl-raw` Storage bucket are required for jobs with matching documents.
The durable worker runs as part of the API application's lifespan and resumes pending/expired jobs after a restart; the
same worker, with the same file-storage wiring, is also available as a standalone process with
`uv run python -m src.workers.worker`.
Crawler limits, request timeouts, pacing, and worker lease/poll intervals can be tuned with the `VBPL_*` environment
variables documented in `.env.example`; defaults preserve the current crawl behavior.

For each sitemap candidate, the worker reads page metadata and uses the public file-list action exposed by the VBPL
detail page, then downloads the listed `.doc`, original `.pdf`, and body `.html` files using VBPL-provided signed URLs
or the public download gateway. When a body HTML attachment is absent, `.docx` is used as the Markdown source if
available; otherwise a legacy `.doc` is converted with `antiword`. The Docker image installs `antiword`; when it is
unavailable on a directly-run worker, the original `.doc` is still stored and the crawl continues without creating
Markdown for that document.
For a new source record, all listed files are uploaded to the private `vbpl-raw` bucket under ASCII,
content-hash-based object keys such as `vbpl/{source_record_id}/{sha256}/origin.pdf` (the upstream filename is retained
in metadata, not used as a Storage path). Body HTML is converted to Markdown and stored as `origin.md`; the HTML, PDF,
and Markdown references and hashes are recorded in the existing `source_documents` columns and `raw_metadata`.
Existing records with stored HTML but no Markdown are converted from the stored HTML without replacing the original
files. If a previous partial attempt created the metadata record but stored no file references, the worker backfills its
missing source files and Markdown. The
`20261109220000_vbpl_source_document_upsert.sql` migration updates the existing upsert function to persist and preserve
stored refs/hashes when a field is omitted; it does not add or alter tables/columns. Apply this migration before running
the worker; it verifies that newly stored file references were actually persisted.

Sitemap `lastmod` is only a discovery signal, not proof that legal content changed. Chunking and embedding are not part
of this stage.

For manual source research, `scripts\crawl_vbpl_sitemap.py` can write a local JSON scan report and
`scripts\inspect_vbpl.py` can capture individual raw HTML pages; neither script is the production crawl entry point.

## Shared core

`src/core` contains cross-layer utilities: validated application settings, UTC time handling, UUID creation/parsing, shared exceptions and typed results, and recursive redaction of sensitive fields. API, application, framework, and integration code can reuse these without placing use-case behavior in the core.

## LangGraph foundation

`src/framework/graphs` provides shared helpers to create and compile LangGraph state graphs. PostgreSQL checkpoint storage is implemented by `src/integrations/langgraph/postgres_checkpointer.py`; it uses an async connection pool and initializes LangGraph's checkpoint tables when opened. To enable it, set `LANGGRAPH_CHECKPOINTER_ENABLED=true` and provide `DATABASE_URL`. The application exposes the initialized saver as `app.state.langgraph_checkpointer` for workflow compilation and closes its pool on shutdown. Checkpointing remains disabled by default.

`src/framework/human_in_the_loop` provides a reusable approval gate. Add `approval_gate` to a graph after the step requiring review and route its result with `approval_route`. The graph must be compiled with a checkpointer and invoked with a stable `configurable.thread_id`. When the graph returns an interrupt, present its request to the reviewer; then resume the same thread with `approval_resume_command(ApprovalDecision(...))`. Decisions are restricted to `approve` or `reject` and must reference the pending `approval_id`. The legal QA graph and HTTP endpoints for submitting or reviewing executions are not yet wired.

## Workflow framework components

`src/framework/resilience` provides bounded synchronous/asynchronous retries, a thread-safe circuit breaker, and an async concurrency limiter. Idempotency is persisted by `src/integrations/database/idempotency_store.py`, not held in a process-local cache. Configure retries with an explicit exception allowlist for operations that are safe to repeat.

`src/framework/runtime` propagates immutable execution metadata through context variables, exposes cooperative cancellation, validates lifecycle transitions, and runs an async graph with optional timeout enforcement. `GraphExecutor.execute()` expects a compiled graph with an `ainvoke(input, config=...)` method. Cancellation and timeout cancel the graph task; synchronous tool handlers run in a worker thread and cannot be forcibly stopped once running.

`src/framework/state` contains reusable `WorkflowState` and message schemas, immutable message/artifact values, and reducers for message/artifact identity updates, ordered unique append, and metadata merging. Application-specific state schemas may extend these fields and use the reducers in LangGraph annotations.

`src/framework/tools` provides a thread-safe registry and async executor. A tool declares a Pydantic input schema, handler, timeout, and required permission grants. The caller must pass a `ToolPrincipal`; authorization and input validation happen before handler execution. Optional idempotency keys use the `ToolIdempotencyStore` port, implemented by `PostgresIdempotencyStore` and scoped by tool and principal. Pass `PostgresIdempotencyStore(settings.supabase.database_url)` to `ToolExecutor` to enable it. The adapter stores only hashes of idempotency keys and normalized inputs, plus the JSON result. It uses renewable leases to coordinate workers and retains completed results for 24 hours by default; expired rows are opportunistically cleaned up during later idempotent calls. Apply [`20261103230000_tool_idempotency.sql`](./src/integrations/database/supabase/migrations/20261103230000_tool_idempotency.sql) before enabling the adapter. A handler's external side effects and saving its result are not one atomic transaction; side-effecting handlers should also enforce idempotency at their own persistence boundary. Handler failures are surfaced as `ToolExecutionError` without exposing the underlying message to the caller; the original exception remains available as `__cause__` for trusted diagnostics.

## Request limits and caching

The AI Service is an internal service called by the .NET Backend. User authentication, authorization, and request rate limiting belong to the Backend; the AI Service does not currently implement its own rate limiter.

The AI Service has no cache or Redis dependency. Do not add a cache adapter or require Redis unless an approved workload need is documented. Request timeouts and bounded workflow/model concurrency remain responsibilities of the AI Service.

## Observability

The service currently emits JSON logs for request lifecycle and Supabase retrieval, with validated `X-Request-ID` propagation and sensitive-field redaction. Workflow run IDs can be bound to the same event context as graph and model integrations are implemented. The service does not require OpenTelemetry or an external telemetry backend.

## Supabase

The API creates a Supabase client during startup when database credentials are present. Configure these values in a local `.env` file (copy `.env.example`); do not commit real keys:

```dotenv
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<server-only-key>
DATABASE_URL=postgresql://postgres:<database-password>@db.<project-ref>.supabase.co:5432/postgres
SUPABASE_AUTO_MIGRATE=false
```

`SUPABASE_URL` and API keys are for the Supabase HTTP API. The application uses `DATABASE_URL` to connect directly to Supabase PostgreSQL for schema migrations. Get the database connection string from Supabase Dashboard → **Project Settings → Database → Connection string**; use the connection mode appropriate for your network (for example, Session Pooler if direct connections are unavailable). URL-encode special characters in the database password. Treat this URL as a secret and do not commit it. Keep the service-role key on the server only because it bypasses Row Level Security. The migration enables RLS without public policies, so the service-role key is required for server-side Data API and Storage access unless you add suitable policies. `SUPABASE_ANON_KEY` alone does not grant access to these tables. `SUPABASE_URL` and at least one API key must be configured together.

Database migrations are kept under [`src/integrations/database/supabase/migrations`](./src/integrations/database/supabase/migrations). The migration [`20261028170000_unified_rag_storage.sql`](./src/integrations/database/supabase/migrations/20261028170000_unified_rag_storage.sql) creates the `dense_chunk_embeddings` table used for vector data and enables RLS on all schema tables. Its vector column and HNSW index are configured for 1536-dimensional cosine embeddings; the retrieval RPC also assumes that dimension, so keep both migrations aligned if changing the embedding model.

RAG data access is split by responsibility under [`src/integrations/database/repositories`](./src/integrations/database/repositories): source-document metadata, parsed document persistence, chunk reads, dense-index lifecycle, sparse-index lifecycle, and retrieval. The use case coordinates these repositories. Parse output (structure, nodes, blocks, and chunks) is persisted through one RPC so this multi-table write is atomic.

Execution submission uses a PostgreSQL transactional outbox. The execution row and its `execution.queued` event are written in one `DATABASE_URL` transaction by separate execution and outbox repositories. The outbox dispatcher leases pending events with `FOR UPDATE SKIP LOCKED`, publishes through the `ExecutionQueuePublisher` interface, and records acknowledgements or bounded exponential retries. Delivery is at least once: queue consumers must make execution handling idempotent. This establishes persistence and dispatch boundaries; a concrete broker adapter and execution worker are not yet wired to the legal QA graph.

The execution/outbox runtime therefore requires `DATABASE_URL`, independently of the Supabase Data API credentials. Apply the migration with the same migration command described below before enabling execution submission or dispatch.

Apply all SQL migrations in filename order. Agent-facing dense vector retrieval uses `search_legal_chunks`; keyword retrieval uses `search_sparse_legal_chunks` over the BM25 inverted index. Both apply the requested effective date and require explicit allowlists for all source-governance statuses. Other repository operations use dedicated RPCs. These functions are exposed through Supabase's Data API, so query/write traffic does not use `DATABASE_URL`; keep the service-role key server-side because only `service_role` is granted permission to execute them. The dense query embedding must come from the same 1536-dimensional model/index named in the request.

To apply pending migrations manually from the repository root:

```powershell
uv run python -m src.integrations.database.migrator
```

Or run `make db-migrate`. Both commands use `DATABASE_URL`; Supabase CLI login/link is not needed.

To apply pending migrations automatically when the API starts, set `SUPABASE_AUTO_MIGRATE=true` and provide `DATABASE_URL` in `.env`. Startup applies each SQL migration once and aborts if the database connection or migration fails. Keep this setting `false` in production unless you explicitly want migrations to run on application startup; otherwise run them as a deployment step.