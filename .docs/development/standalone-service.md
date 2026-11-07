# Standalone packaging checkpoint

**Update 2026-11-07.** Use the current setup at the beginning of the repository README. A new Python 3.12.16 venv installed 109 locked packages using a warmed uv download cache. The suite passed 142 tests with three optional ML skips. The new socket smoke passed against the local Qwen runtime and the restored BM25 artifact, including claim-span and locator checks. Compose now shares the local model network namespace. Docker startup remains NOT VERIFIED. The original observations below describe the previous checkpoint.

The service now includes the `ai_core` Python package. It is imported locally and included in the wheel alongside `src`. The parent BasicRAG checkout remains an unchanged historical baseline, not a runtime dependency. Retrieval, evidence and generation algorithms are not changed by this import.

## Setup

From the AI Service repository root, use Python 3.12 and `uv sync --frozen --group dev`. Do not set PYTHONPATH to a parent checkout. Run commands as modules: `uv run python -m scripts.quality_http_smoke` and `uv run python -m pytest`.

Install the separately delivered Python 3.12 BM25 artifact pair (`manifest.json`, `index.json`) under `data/indexes/labor-pilot-3-t4-bm25/`. The index contains runtime chunks; its historical processed-input path is provenance, not a runtime input. Do not edit recorded hashes or mix the Python 3.14 index with Python 3.12. Existing source-integrity and Unicode-tokenizer checks remain active.

Start an operator-managed local llama.cpp runtime with Qwen2.5-1.5B-Instruct Q4_K_M, alias `qwen-pilot`, context 8192, temperature 0, four CPU threads, one slot, loopback port 18963. Model and runtime binaries are separate artifacts, never Git source. No paid provider is required.

Set process environment: APP_ENV=development, TILLEGAL_RAG_PILOT=1, TILLEGAL_ANSWER_PROVIDER=local, TILLEGAL_ANSWER_MODEL=qwen-pilot, TILLEGAL_LOCAL_PORT=18963, TILLEGAL_CONTEXT_POLICY=context_judge. Keep Supabase and checkpoint integrations disabled for this pilot. Start `uv run python -m uvicorn src.main:app --host 127.0.0.1 --port 8000`.

POST `/pilot/legal-qa` with JSON `{"question":"Người lao động có quyền tham gia bảo hiểm xã hội không?","top_k":3,"workflow":"semantic"}`. Default workflow remains basic; pilot remains opt-in. A DRAFT is not proof of legal validity. The current per-worker concurrency limit rejects overlapping requests with 429; it does not establish production throughput.

## Commit boundaries

Commit service `src/`, `ai_core/` Python source (no caches), `tests/`, `scripts/`, `pyproject.toml`, `uv.lock`, `.gitattributes`, `.gitignore`, `.dockerignore`, `.env.example`, configs and deployment files after review against the lead repository. Commit concise development documentation separately. Do not commit parent baseline, credentials, virtual environments, raw corpus, models, local outputs or heavy benchmark traces.

Docker uses the service root as build context. Mount the compatible index under `/app/data/indexes/labor-pilot-3-t4-bm25` read-only. The present provider connects to loopback, so a model in another container is not reachable through the existing configuration; Docker real-model deployment remains unverified. No production default has been changed.

## Validation 2026-11-06

Service-root full suite: 142 passed, 3 skipped in 22.42s. Independent source copy with PYTHONPATH unset: 142 passed, 3 skipped in 23.27s; module locations verified inside the copy. Skips are dense/hybrid ML variants. Existing request isolation, backpressure, cancellation and failure-path regressions passed. This is source-copy isolation, not a fresh network clone from a verified lead remote.

Real BM25 + Qwen semantic TestClient smoke: 200/DRAFT (17.66s); independent source-copy smoke: 200/DRAFT (9.59s). Actual Uvicorn socket request also returned DRAFT with request_id standalone-socket-user-1. Raw evidence is in ignored data/standalone-*.json; one initial 504 timeout is preserved. No benchmark rerun or cloud calls.

Wheel build/install succeeded: tillegal_ai-0.1.0-py3-none-any.whl, SHA256 48d800a9ee432a85750d2a995a38909e5362b2566d3dbe46ec8c86e2744169ae. Installed-wheel imports were checked with isolated Python (-I). Dependency environment was the existing frozen Python 3.12 environment; a brand-new dependency installation remains unverified.

Docker executable is unavailable, so Docker build/startup is NOT TESTED. Compose/model sidecar connectivity has not been completed; local semantic deployment uses the documented host runtime. This packaging checkpoint does not establish production readiness or complete Project 1/9. Remaining work includes fresh environment setup, Docker local-model networking, artifact installer/validation automation and review against the actual lead Git base.

The explicit candidate source list is COMMIT_FILES.txt. Review it against the lead checkout before staging; it includes existing lead files because their authoritative Git base is unavailable. Do not stage the parent folder wholesale.
