# Integration guide

## Environment and configuration

Use existing project root and existing.venv, Python>=3.12 (pyproject.toml). Dependencies already declared: Pydantic via current environment, python-dotenv, PyYAML, LiteLLM, Supabase; sentence-transformers/transformers/torch for local models. pytest/Ruff are dev tools. This acceptance installs nothing; use the project's provisioned/locked environment rather than changing versions during integration. Version evidence in scope_report.json.

Supabase loader: src/core/config.py:load_settings. SUPABASE_URL with SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY; server-only key must stay server-side, anon access depends on configured RLS/RPC permissions. Existing read privileges determine visible scope. DATABASE_URL is not required for retrieval-only composition unless existing settings enable auto_migrate validation. Do not start ASGI workers/crawler/migration for this handoff. create_query_search delegates only to read retrieval composition; it does not call migration/write APIs. No config/env file is overwritten.

Gemini: GOOGLE_API_KEY must be available to the process by factory call. Config profile query_semantic currently uses gemini-3.5-flash-lite; GEMINI_MODEL and QUERY_LLM_TIMEOUT_SECONDS optional overrides. semantic_mode="gemini" is explicit. To inject a planner using a separate environ mapping, call create_gemini_query_agent(environ=...) and pass query_agent=..., leaving semantic_mode at its default; do not provide both query_agent and semantic_mode="gemini".

## Retrieval modes and checkpoints

|Choice|SearchOptions.mode|Requirements|
|---|---|---|
|BM25|bm25|Ready sparse index + read RPC/metadata permissions; no local encoder|
|Dense|dense|Existing local multilingual-e5-small checkpoint, matching384D dense index|
|Hybrid RRF|hybrid|Both prior branches, HybridConfig budgets; strict branch failure policy|
|Hybrid+rerank|hybrid|RerankConfig(enabled=True,model_path=existing CE path), E5 and existing cross-encoder/mmarco-mMiniLMv2-L12-H384-v1 checkpoint|

There is no SearchOptions.mode="rerank". Local adapters use local_files_only/trust_remote_code=False and CPU; no automatic model download. Existing evaluation scripts name actual cached snapshot directories; see18_QUERY_FORMULATION_EXPERIMENTS.md and scripts/evaluate_query_search_retrieval.py:DENSE/CE. Do not assume those user-specific paths exist on a teammate's computer. Supply provisioned paths explicitly. Model loading can exceed ordinary request budgets on a cold CPU; this remains an operational limit, not resolved by acceptance.

## A. Complete offline deterministic example

Run the following as a Python file from project root. No key, network or local ML checkpoint required. This exercises the existing QuerySearch facade with an injected controlled backend; it does NOT exercise RetrievalService or prove legal relevance. Acceptance separately executes the public factory with patched composition and a nonempty recorded-evidence fixture.

```python
import asyncio
from datetime import UTC, datetime
from uuid import uuid4

from pydantic import TypeAdapter

from src.applications.tillegal.agents.search.agent import SearchOptions, SearchState
from src.applications.tillegal.retrieval.contracts import RetrievalResponse
from src.query_search_bootstrap import QuerySearch


class NoMatchBackend:
    async def search(self, request):
        return RetrievalResponse(
            **request.model_dump(),
            request_id=uuid4(),
            query_used=request.query.strip(),
            selected_index_name="controlled-fixture",
            index=None,
            status="NO_MATCH",
            retrieved_at=datetime.now(UTC),
        )


async def main():
    options = SearchOptions(
        mode="bm25", top_k=3, as_of_date="2026-11-23",
        allowed_usage_policies=("EXPERIMENTAL_ONLY",),
    )
    runner = QuerySearch(retrieval=NoMatchBackend(), options=options)
    state = await runner.search("Điều kiện để hợp đồng dân sự có hiệu lực là gì?")
    assert state["completeness"] == "COMPLETE" and not state["evidence"]
    print(TypeAdapter(SearchState).dump_json(state, serialize_as_any=True).decode())


if __name__ == "__main__":
    asyncio.run(main())
```

## B. Complete configured invocation helper

The helper below uses only existing APIs. Defining/importing it makes no provider request; calling it performs REAL Supabase retrieval, and semantic_mode="gemini" may call REAL Gemini. This acceptance syntax-checks this helper but deliberately does not run its live calls. Factory/provider integration is exercised by current mocked tests; historical real calls are linked in06.

```python
import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from src.applications.tillegal.agents.query.agent import QueryInputError
from src.applications.tillegal.agents.query.semantic import QueryAnalysisError
from src.applications.tillegal.agents.search.agent import SearchOptions
from src.applications.tillegal.retrieval.hybrid_models import HybridConfig
from src.applications.tillegal.retrieval.reranking_models import RerankConfig
from src.core.config import load_settings
from src.query_search_bootstrap import create_query_search


async def run_live(
    question: str, *, as_of_date: str, allowed_usage_policies: tuple[str, ...],
    semantic_mode="deterministic", mode="bm25", top_k=3,
    dense_model_path: Path | None = None,
    reranker_model_path: Path | None = None,
):
    # Preserve existing process values; do not print configuration or credentials.
    load_dotenv(override=False)
    settings = load_settings(environ=os.environ)
    if mode in {"dense", "hybrid"} and (dense_model_path is None or not dense_model_path.is_dir()):
        raise ValueError("An existing local E5 checkpoint is required")
    if reranker_model_path is not None and (mode != "hybrid" or not reranker_model_path.is_dir()):
        raise ValueError("Reranking requires hybrid and an existing local checkpoint")
    options = SearchOptions(mode=mode, top_k=top_k, as_of_date=as_of_date,
                            allowed_usage_policies=allowed_usage_policies)
    rerank = RerankConfig(enabled=True, model_path=reranker_model_path) if reranker_model_path else None
    runner = create_query_search(
        settings.supabase, options, semantic_mode=semantic_mode,
        dense_model_path=dense_model_path,
        hybrid_config=HybridConfig(bm25_candidates=10, dense_candidates=10),
        rerank_config=rerank, timeout_seconds=30,
    )
    try:
        async with asyncio.timeout(90):  # Caller-owned overall deadline.
            state = await runner.search(question)
    except (QueryInputError, QueryAnalysisError) as error:
        print(type(error).__name__, str(error))  # Safe public code only.
        raise
    print(state["status"], state["completeness"], state["warnings"])
    for error in state["errors"]:
        print(error.category, error.code, error.stage, error.retryable)
    if state["completeness"] == "PARTIAL":
        print("Incomplete execution; skipped query indices:", state["skipped_subqueries"])
    plan = state["plan"]
    for group in state["evidence"]:
        item = group.evidence
        print(item.source_document_id, item.retrieval_chunk_id, item.title)
        for occurrence in group.occurrences:
            issues = [plan["issues"][i] for i in occurrence.issue_indices]
            print(occurrence.subquery_index, occurrence.rank, issues)
        # Retrieved content remains unverified supporting material.
    return state
```

Example calls inside your application's async context (trusted date/policy supplied deliberately):

```python
# Deterministic Query with real BM25 retrieval:
state = await run_live(question, as_of_date="2026-11-23",
                       allowed_usage_policies=("EXPERIMENTAL_ONLY",))
# Gemini Query with real BM25 retrieval:
state = await run_live(question, as_of_date="2026-11-23",
                       allowed_usage_policies=("EXPERIMENTAL_ONLY",), semantic_mode="gemini")
# To use Dense/Hybrid, pass mode plus an EXISTING dense_model_path.
# To rerank, use mode="hybrid" and pass an EXISTING reranker_model_path.
```

Create settings/runner once in the application's appropriate lifecycle rather than reconstructing local models per question. The example has an outer90-second caller deadline; choose a measured operational budget for your application. create_query_search timeout_seconds=30 configures RetrievalService; Search per-query default45 remains separate. RerankConfig defaults inference10/total40 seconds, pool20, batch4/max_length512. HybridConfig defaults20/20 unless explicitly configured as above. Provider timeout defaults30; injected SemanticQueryAgent default15. No timeout here implies infinite retries.

## Serialization and interpretation

SearchState is a dict, not an object with model_dump. Use TypeAdapter(SearchState).dump_python(state,mode="json",serialize_as_any=True) or dump_json(state,serialize_as_any=True); date/UUID/enum/tuples then serialize correctly. Current serialization_probe.json confirms default TypeAdapter serialization omits fusion/reranking because responses is annotated as the base type. serialize_as_any=True preserves them. Do not directly validate extended response JSON as base RetrievalResponse: its extra-forbid rejects subtype fields. Restore the actual subtype first, then validate the containing state:

```python
from pydantic import TypeAdapter
from src.applications.tillegal.agents.search.agent import SearchState
from src.applications.tillegal.retrieval.contracts import RetrievalResponse
from src.applications.tillegal.retrieval.hybrid_models import HybridRetrievalResponse
from src.applications.tillegal.retrieval.reranking_models import RerankedHybridRetrievalResponse


def restore_search_state(payload):
    responses = []
    for raw in payload["responses"]:
        model = (RerankedHybridRetrievalResponse if "reranking" in raw
                 else HybridRetrievalResponse if "fusion" in raw
                 else RetrievalResponse)
        responses.append(model.model_validate(raw))
    return TypeAdapter(SearchState).validate_python({**payload, "responses": tuple(responses)})
```

This helper is for trusted SearchState JSON with known native schemas, not a security gate for arbitrary externally authored QueryPlan. Other metadata/contracts and downstream trust rules still apply. The acceptance independently round-trips a stored native rerank response through this procedure without a network call.

Facts are user statements, issues are information needs, evidence is stored retrieved material. COMPLETE means execution completed, not enough law found. Source-title warnings do not prove identity/authority. Missing effective dates remain uncertainty, not auto-applicability. Use occurrence.rank for native provenance, not representative score as global rank. Partial results must not silently become a completed legal answer.

## Downstream consumer checklist (documentation only)

- Provide trusted mode/top_k/date/policies; do not accept these directly from model or untrusted client plan.
- Preserve original, clarification, planning_warnings and typed reference/time context; do not infer dates from document year.
- Use planner-created plans. If importing external/legacy plans, understand schema limits and do not assume manual facts/citation spans were grounded.
- Handle QueryInputError/QueryAnalysisError separately from returned retrieval errors; cancellation/unexpected exceptions can propagate.
- Inspect status/completeness, each response, NO_MATCH, errors and skipped_subqueries before using evidence.
- Follow group occurrences and zero-based issue indices. Empty legacy association is unknown, not every issue.
- Preserve source/structure/snapshot/content hash/version fields and Hybrid/rerank subtype JSON extensions. Do not merge distinct versions or compare heterogeneous scores.
- Inspect source identity, content context and temporal applicability separately; do not treat a cross-reference as the requested provision.
- Preserve uncertainty/warnings. Legal interpretation/answer/verification remains future integration ownership; no such agent implemented here.

## Safe reproducibility

verify_query_search_handoff refuses an existing output path. Original evaluator live outputs also refuse overwrite; relevance reanalysis refuses annotated JSON reviews. Use fresh output locations. validate_query_semantics replay/summarize intentionally regenerate derived summaries; preserve annotated review files and immutable raw runs. This acceptance does not regenerate the full dataset or repeat live benchmarks.
