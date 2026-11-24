# Query/Search

Query plans information needs; Search executes those plans through the existing read-only RetrievalService. Neither component generates a legal answer or verifies legal applicability.

## Runtime flow

`src/query_search_bootstrap.py:create_query_search` → `QuerySearch.search(question)` → deterministic `query/agent.py:understand` or `query/semantic.py:SemanticQueryAgent.understand` → `search/agent.py:search` → `RetrievalService.search` → `search/agent.py:_finish`.

Query/Search modules live under `src/applications/tillegal/agents/`. Gemini configuration is isolated in `query/gemini.py`, with the LiteLLM adapter in `src/framework/llm/providers/gemini_adapter.py`. The shared OpenAI defaults for unrelated agents remain untouched. Existing graph, retrieval algorithms, ingestion and database are not changed.

Deterministic input validation always runs. Exact lookup/clarification short circuit Gemini. Semantic mode makes one bounded structured call, validates grounding and returns a QueryPlan or explicit error, without silent fallback. Search runs subqueries sequentially, reuses exact duplicate requests and keeps native evidence/provenance/partial failures.

## Maintainer reading order

- [Contracts](CONTRACTS.md): fields, origins, uncertainty and JSON.
- [Integration](INTEGRATION.md): configuration, runnable offline smoke and invocation.
- [Limitations](LIMITATIONS.md): responsibilities and safe interpretation.

## Verification

```sh
python -m pytest tests/unit/applications/tillegal tests/graph/test_query_search_workflow.py -q
python -m pytest -q
python -m ruff check .
python -m ruff format --check src/applications/tillegal/agents/query src/applications/tillegal/agents/search src/query_search_bootstrap.py src/framework/llm/providers/gemini_adapter.py scripts/verify_gemini_query.py
python -m scripts.verify_gemini_query --mode deterministic --search-backend fixture
```

Tests use mocked completion/read ports; they do not establish live Gemini or database availability. No raw API responses, large datasets or model files are required by this subset. Historical evaluation and academic documents remain available on the [preserved source branch](https://github.com/Legally-Illigal/tillegal-ai/tree/73360f249112dab2caf781e39d74e8ea8647190e/docs/query-search).
