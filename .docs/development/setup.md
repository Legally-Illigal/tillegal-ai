# Development Setup

## Purpose

This guide describes how to prepare a local environment for Tillegal AI Service. It is a practical checklist that must stay consistent with the repository's dependency manifest and deployment configuration.

## Before starting

- Access to the repository, Git, and a code editor.
- Python 3.12 or newer and `uv`.
- Provider credentials only if running live model integration tests.
- Supabase credentials only if running integration tests against the RAG store.

The project uses FastAPI, LangGraph, LiteLLM, and Supabase Postgres with pgvector for RAG storage. `pytest` and `ruff` are development tools. `uv` manages the project environment and lock file.

## Initial setup

1. Clone the repository and enter its root directory.
2. Check the current branch and working tree.
3. Read the root README, `docs/architecture/`, and applicable ADRs.
4. Inspect the dependency manifest and lock file.
5. Install Python 3.12 if needed, then synchronize the project environment:

   ```powershell
   uv python install 3.12
   uv sync --all-groups
   ```

6. Copy the environment example to a local environment file, if one exists.
7. Configure only the settings required for your task.
8. Run the project checks:

   ```powershell
   uv run ruff check .
   uv run pytest
   ```

Never commit local environment files, API keys, tokens, credentials, or sensitive provider traces.

## Configuration principles

| Category | Guidance |
|---|---|
| Application settings | Use documented defaults where safe. |
| Model routing | Configure logical model profiles instead of hard-coding providers in agent logic. |
| Provider credentials | Supply through local environment variables or an approved secret store. |
| Runtime limits | Keep timeouts, retries, and workflow budgets bounded. |
| Observability | Preserve redaction; do not log secrets to debug a problem. |
| External services | Configure only services the current code actually requires. |

`.env.example` must contain placeholders only. Missing optional provider or Supabase credentials should not prevent unrelated unit tests from running.

## Run and verify

The API framework is FastAPI. Start the development server from the repository root with:

```powershell
uv run python -m src.main
```

The ASGI application is exposed as `app` from `src.main`; the command uses `HOST`, `PORT`, and `DEBUG` from the environment or `configs/app.yaml`. The liveness endpoint is `/health/live`. The current runtime exposes liveness only; model workflow and Supabase readiness checks will be added when those integrations are wired.

Verify that the application starts, configuration errors are actionable, health checks work if implemented, startup logs do not expose secrets, and an offline/mock request can run without live provider credentials where supported.

## Model-provider access

All application and agent model calls must go through the shared Model Gateway. Agent modules must not instantiate provider clients or read provider credentials directly. Prefer mocks for unit tests and reserve live provider calls for explicitly selected integration tests. Treat unavailable token/cost measurements as unknown rather than fabricating values.

## RAG storage

Supabase Postgres with the `pgvector` extension is the selected vector store for RAG. Access it through a retrieval/storage adapter rather than from agent or prompt code. Configure Supabase credentials only for workflows that connect to the live store; unit tests should use fakes or fixtures.

## Troubleshooting

- **Dependency install fails:** check Python version, package-manager instructions, and lock-file consistency.
- **Configuration fails:** compare required settings with the environment example; do not share secrets in issue reports.
- **Provider authentication fails:** verify credentials and model/profile mapping without printing credentials.
- **Import fails:** check the active environment and run command.
- **Unit tests call a live provider:** inspect dependency injection and fixtures; replace the gateway with a fake.

## Ready criteria

The environment is ready when dependencies install reproducibly, configuration validation works, local checks run, unit tests need no live credentials, and the service starts using documented commands.

Update this guide when supported tooling, environment variables, setup steps, or run commands change.
