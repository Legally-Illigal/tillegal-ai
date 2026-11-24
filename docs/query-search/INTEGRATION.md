# Integration

Use Python>=3.12 and the existing pyproject/lock environment. No dependency changes are introduced by Query/Search. Relevant libraries: Pydantic, PyYAML, python-dotenv, LiteLLM, Supabase; sentence-transformers/transformers/torch for optional local retrieval models.

## Offline smoke: no keys, network or models

```sh
python -m scripts.verify_gemini_query --mode deterministic --search-backend fixture
```

This composes the real RetrievalService with empty in-memory read ports and runs QuerySearch. The CLI defaults to deterministic mode. It is retained because Gemini mocked integration tests import its fixture/main; it is not an unused diagnostic tool. Choosing --mode gemini performs real provider calls; acceptance/CI should use mocks or deterministic fixture mode.

## Real invocation (when explicitly authorized)

```python
import asyncio
from src.core.config import load_settings
from src.query_search_bootstrap import create_query_search
from src.applications.tillegal.agents.search.agent import SearchOptions

async def main():
    settings = load_settings()  # Existing dotenv/process config; do not print credentials.
    options = SearchOptions(mode="bm25", top_k=3, as_of_date="2026-11-24",
                            allowed_usage_policies=("EXPERIMENTAL_ONLY",))
    runner = create_query_search(settings.supabase, options, semantic_mode="deterministic")
    state = await runner.search("Điều kiện để hợp đồng dân sự có hiệu lực là gì?")
    print(state["status"], state["completeness"], state["warnings"])
    for error in state["errors"]:
        print(error.code, error.stage, error.retryable)
    for group in state["evidence"]:
        print(group.evidence.source_document_id, group.evidence.title)
        for occurrence in group.occurrences:
            issues = [state["plan"]["issues"][i] for i in occurrence.issue_indices]
            print(occurrence.subquery_index, occurrence.rank, issues)
    if state["skipped_subqueries"]:
        print("Incomplete execution:", state["skipped_subqueries"])

if __name__ == "__main__":
    asyncio.run(main())
```

Running this example calls the real database. load_settings reads existing configuration; API keys remain server-side. Retrieval requires SUPABASE_URL and an already configured Supabase key with read/RPC permissions. No crawler/ASGI startup, migration or write is invoked by create_query_search.

## Gemini

Set semantic_mode="gemini" explicitly. GOOGLE_API_KEY must be in process environment before factory call. query_semantic profile in configs/models.yaml selects Gemini, currently gemini-3.5-flash-lite; GEMINI_MODEL and QUERY_LLM_TIMEOUT_SECONDS are supported overrides. The key value is never included in reports. Factory construction itself does not call provider. A query_agent may be injected instead, but must not be supplied together with semantic_mode="gemini".

Provider adapter uses structured JSON, no retry/cache and safe errors. No silent deterministic fallback. Exact lookup/clarification bypasses provider even in semantic mode. Query errors are safe codes; provider diagnostics can be intentionally coarsened at the semantic boundary.

## Retrieval configuration and deadlines

BM25 needs ready sparse index/read ports only. Dense or Hybrid needs dense_model_path pointing at an existing local multilingual-e5-small checkpoint matching the384-dimensional dense index. Hybrid may receive HybridConfig(bm25_candidates=10,dense_candidates=10). Optional reranking uses mode="hybrid" and RerankConfig(enabled=True,model_path=existing_cross_encoder_path). Local models use CPU/local_files_only; do not auto-download checkpoints.

create_query_search timeout_seconds(default30) configures RetrievalService, not the Search per-query45-second outer deadline. Multiple subqueries have separate budgets; caller may apply an overall asyncio.timeout. Provider profile defaults30 seconds; directly constructed SemanticQueryAgent defaults15. RerankConfig has its own inference/total deadlines. Preserve explicit fallback diagnostics if the optional reranker retains RRF order.

Cache/model instances should be provisioned in an appropriate application lifecycle. Cold model initialization can exceed normal budgets. No universal latency SLA or automatic source sufficiency is promised.

## Consumer requirements

Use trusted date/policy/mode/top_k; preserve clarification/warnings/errors/partials/skips. Facts may be allegations; issues are needs; evidence is unverified material. Respect empty legacy issue mappings and native occurrence ranks. Keep versions separate and serialize subtype fields as documented in CONTRACTS.md. Do not treat COMPLETE or an absent identity warning as legal validation. No Judge/Answer/Verification integration is implemented here.
