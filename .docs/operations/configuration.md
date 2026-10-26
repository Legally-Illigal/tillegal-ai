# Configuration

## 1. Purpose

This document defines configuration conventions for the Tillegal AI Service across local development, testing, demo, and deployment environments.

## 2. Configuration Principles

- Keep environment-specific settings outside application source code.
- Validate configuration at startup and fail fast when required settings are missing or invalid.
- Use typed configuration models instead of reading environment variables throughout business logic.
- Keep secrets out of source control, logs, exception messages, and example files.
- Apply safe defaults only where appropriate; production must not silently inherit development settings.
- Configuration must not bypass legal-source retrieval, citation verification, or other required workflow stages.
- Bound retries, timeouts, concurrency, and workflow execution.

## 3. Configuration Categories

| Category | Examples | Responsibility |
|---|---|---|
| Application | Environment, service name, log level | Runtime identity and behavior |
| API | Host, port, request timeout, request-size limit | API runtime |
| Workflow | Workflow version, step limit, execution timeout | LangGraph orchestration |
| Model Gateway | Provider, model profile, timeout | Shared model access |
| Fallback | Fallback profiles, eligibility rules | Controlled recovery from model failures |
| Retrieval | Top-k, filters, score threshold | Evidence retrieval |
| Verification | Verification model profile, retry limit | Legal-basis and citation verification |
| Evaluation | Dataset version, enabled evaluation suites | Quality assessment |
| Observability | Logging, metrics, tracing settings | Operational visibility |
| Persistence | Supabase URL/key or secret reference | RAG vectors in Supabase Postgres with pgvector |

Exact keys, types, defaults, and requiredness must be defined in the application's configuration schema. Do not infer production values from this table.

## 4. Environment Management

Use separate configuration for local development, automated testing, demo/staging, and production when applicable.

- Commit a `.env.example` containing key names and safe placeholder values only.
- Add `.env` and other local secret files to `.gitignore`.
- Load local secrets through the team's approved development mechanism.
- Use environment variables or an approved secret manager in deployed environments.
- Never commit API keys, database credentials, signing keys, or access tokens.
- Keep Supabase credentials server-side; never expose service-role credentials to clients.
- Rotate any credential that may have been exposed.

## 5. Startup Validation

The application should validate at startup that:

1. Required configuration values are present.
2. Model profiles reference supported providers and models.
3. Timeout, retry, concurrency, and workflow limits are valid.
4. Required persistence and external dependencies are configured.
5. Production mode does not use development-only settings.
6. Secret values are not included in validation error messages.

Configuration errors should identify the affected key and expected format without exposing its value.

## 6. Model Gateway Configuration

Agents must use the shared Model Gateway rather than instantiate provider clients directly.

Model profiles should define the settings needed for a model call, such as provider, model identifier, supported capabilities, timeout, and applicable usage limits.

Fallback configuration must specify which failures qualify for fallback. Fallback must remain bounded and must not silently change a task's output contract or skip legal verification.

Token usage and cost should be recorded only when returned by the provider or calculated from reliable pricing metadata. Unknown values must remain unknown.

## 7. Configuration Change Checklist

- [ ] Update the configuration schema.
- [ ] Update safe example configuration.
- [ ] Add validation and tests for missing or invalid values.
- [ ] Review secret exposure and logging implications.
- [ ] Run relevant integration tests.
- [ ] Run evaluation tests if prompts, models, retrieval, or verification behavior changes.
- [ ] Review whether an ADR update is required.
- [ ] Record deployment and rollback instructions.

## 8. Supabase RAG Storage

Supabase Postgres with `pgvector` is the selected vector store for RAG. The retrieval adapter owns database access; application agents depend on the retrieval interface, not the Supabase SDK. Unit tests should use fakes/fixtures and do not require Supabase credentials. Live retrieval integration tests require a configured Supabase URL and server-side key.

## 9. Related Documents

- `../architecture/model-gateway.md`
- `../architecture/evaluation-design.md`
- `../architecture/observability-design.md`
- `../decisions/ADR-002-litellm.md`
- `../decisions/ADR-005-supabase-pgvector.md`
- `../decisions/ADR-004-observability.md`
