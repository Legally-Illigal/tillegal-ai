"""Compose Query/Search with the existing read-only retrieval bootstrap."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from src.application.services.retrieval_service import RetrievalService
from src.applications.tillegal.agents.query.agent import understand
from src.applications.tillegal.agents.query.semantic import SemanticQueryAgent
from src.applications.tillegal.agents.search.agent import SearchOptions, SearchState, search
from src.applications.tillegal.retrieval.hybrid_models import HybridConfig
from src.applications.tillegal.retrieval.reranking_models import RerankConfig
from src.core.config import SupabaseSettings
from src.retrieval_bootstrap import create_retrieval_service


@dataclass(frozen=True)
class QuerySearch:
    retrieval: RetrievalService
    options: SearchOptions
    query_agent: SemanticQueryAgent | None = None

    async def search(self, question: str) -> SearchState:
        plan = await self.query_agent.understand(question) if self.query_agent else understand(question)
        return await search(plan, self.retrieval, self.options)


def create_query_search(
    settings: SupabaseSettings,
    options: SearchOptions,
    *,
    query_agent: SemanticQueryAgent | None = None,
    semantic_mode: Literal["deterministic", "gemini"] = "deterministic",
    dense_model_path: Path | None = None,
    hybrid_config: HybridConfig | None = None,
    rerank_config: RerankConfig | None = None,
    timeout_seconds: float = 30,
) -> QuerySearch:
    """Require explicit filters and delegate all retrieval composition."""
    if semantic_mode not in {"deterministic", "gemini"}:
        raise ValueError("QUERY_SEMANTIC_MODE_INVALID")
    if semantic_mode == "gemini":
        if query_agent is not None:
            raise ValueError("QUERY_AGENT_CONFIGURATION_CONFLICT")
        from src.applications.tillegal.agents.query.gemini import create_gemini_query_agent

        query_agent = create_gemini_query_agent()
    options = SearchOptions.model_validate(options)
    retrieval = create_retrieval_service(
        settings,
        dense_model_path=dense_model_path,
        hybrid_config=hybrid_config,
        rerank_config=rerank_config,
        timeout_seconds=timeout_seconds,
    )
    return QuerySearch(retrieval, options, query_agent)
