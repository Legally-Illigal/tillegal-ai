"""Compose retrieval without the ASGI lifecycle or workers; Dense is explicit opt-in."""

from pathlib import Path

from supabase import ClientOptions, create_client

from src.application.services.retrieval_service import DEFAULT_SPARSE_INDEX, RetrievalService
from src.application.services.vbpl_markdown_indexing_service import tokenize_sparse_text
from src.applications.tillegal.retrieval.hybrid_models import HybridConfig
from src.applications.tillegal.retrieval.ports import IndexReader, QueryEmbedder
from src.applications.tillegal.retrieval.reranking_models import RerankConfig
from src.applications.tillegal.retrieval.retriever import LegalRetriever
from src.core.config import SupabaseSettings
from src.integrations.database.repositories.chunk_repository import ChunkRepository
from src.integrations.database.repositories.dense_index_repository import DenseIndexRepository
from src.integrations.database.repositories.source_document_repository import SourceDocumentRepository
from src.integrations.database.repositories.sparse_index_repository import SparseIndexRepository
from src.integrations.database.repositories.sparse_retrieval_repository import SparseRetrievalRepository
from src.integrations.database.repositories.supabase_vector_repository import SupabaseVectorRepository


def create_retrieval_service(
    settings: SupabaseSettings,
    *,
    dense_model_path: Path | None = None,
    hybrid_config: HybridConfig | None = None,
    rerank_config: RerankConfig | None = None,
    timeout_seconds: float = 30,
) -> RetrievalService:
    """Create read adapters only. Credentials are never rendered or logged here.

    Session persistence/refresh is disabled; search calls only existing read RPCs.
    HTTP timeouts bound worker-thread I/O even after an application deadline expires.
    """
    if settings.url is None or settings.api_key is None:
        raise ValueError("Supabase retrieval configuration is required")
    client = create_client(
        str(settings.url),
        settings.api_key.get_secret_value(),
        options=ClientOptions(persist_session=False, auto_refresh_token=False, postgrest_client_timeout=10),
    )
    dense_retriever: LegalRetriever | None = None
    dense_indexes: IndexReader | None = None
    query_embedder: QueryEmbedder | None = None
    if dense_model_path is not None:
        from src.integrations.embeddings.e5_query_encoder import E5QueryEncoder

        dense_retriever = SupabaseVectorRepository(client)
        dense_indexes = DenseIndexRepository(client)
        query_embedder = E5QueryEncoder(dense_model_path)
    scorer = None
    if rerank_config is not None and rerank_config.enabled:
        from src.integrations.embeddings.cross_encoder_reranker import LocalCrossEncoder

        scorer = LocalCrossEncoder(rerank_config)
    return RetrievalService(
        SparseRetrievalRepository(client),
        ChunkRepository(client),
        SourceDocumentRepository(client),
        SparseIndexRepository(client),
        tokenize_sparse_text,
        sparse_index_name=DEFAULT_SPARSE_INDEX,
        dense_retriever=dense_retriever,
        dense_indexes=dense_indexes,
        query_embedder=query_embedder,
        hybrid_config=hybrid_config,
        rerank_config=rerank_config,
        pair_scorer=scorer,
        timeout_seconds=timeout_seconds,
    )
