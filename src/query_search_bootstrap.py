"""Compose Query/Search with the existing read-only retrieval bootstrap."""

from dataclasses import dataclass
from pathlib import Path

from src.application.services.retrieval_service import RetrievalService
from src.applications.tillegal.agents.query.agent import understand
from src.applications.tillegal.agents.search.agent import SearchOptions, SearchState, search
from src.applications.tillegal.retrieval.hybrid_models import HybridConfig
from src.applications.tillegal.retrieval.reranking_models import RerankConfig
from src.core.config import SupabaseSettings
from src.retrieval_bootstrap import create_retrieval_service


@dataclass(frozen=True)
class QuerySearch:
    retrieval: RetrievalService
    options: SearchOptions

    async def search(self, question: str) -> SearchState:
        return await search(understand(question), self.retrieval, self.options)


def create_query_search(
    settings: SupabaseSettings,
    options: SearchOptions,
    *,
    dense_model_path: Path | None = None,
    hybrid_config: HybridConfig | None = None,
    rerank_config: RerankConfig | None = None,
    timeout_seconds: float = 30,
) -> QuerySearch:
    """Require explicit filters and delegate all retrieval composition."""
    options = SearchOptions.model_validate(options)
    retrieval = create_retrieval_service(
        settings,
        dense_model_path=dense_model_path,
        hybrid_config=hybrid_config,
        rerank_config=rerank_config,
        timeout_seconds=timeout_seconds,
    )
    return QuerySearch(retrieval, options)
