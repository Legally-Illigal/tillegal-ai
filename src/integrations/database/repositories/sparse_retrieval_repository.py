"""Sparse BM25 retrieval through the Supabase RPC."""

from typing import Any

from pydantic import TypeAdapter, ValidationError
from supabase import Client

from src.applications.tillegal.retrieval.document_models import (
    SparseSearchHit as SparseSearchHit,
)
from src.applications.tillegal.retrieval.document_models import (
    SparseSearchRequest as SparseSearchRequest,
)
from src.integrations.database.repositories.rpc import DatabaseRepositoryError, SupabaseRpcRepository

_HIT_LIST_ADAPTER = TypeAdapter(list[dict[str, Any]])


class SparseRetrievalRepository(SupabaseRpcRepository):
    """Retrieve ranked chunk identifiers from the BM25 inverted index."""

    def __init__(self, client: Client) -> None:
        super().__init__(client)

    async def search(self, request: SparseSearchRequest) -> tuple[SparseSearchHit, ...]:
        result = await self.call_rpc(
            "search_sparse_legal_chunks",
            {
                "p_terms": list(request.terms),
                "p_sparse_index_name": request.sparse_index_name,
                "p_top_k": request.top_k,
                "p_as_of_date": request.as_of_date.isoformat(),
                "p_usage_policies": list(request.allowed_usage_policies),
            },
        )
        try:
            rows = _HIT_LIST_ADAPTER.validate_python(result)
            return tuple(SparseSearchHit.model_validate(row) for row in rows)
        except ValidationError as error:
            raise DatabaseRepositoryError("search_sparse_legal_chunks returned an invalid response") from error
