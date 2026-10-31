"""Supabase RPC adapter for dense legal-document retrieval."""

import asyncio

import httpx
from postgrest.exceptions import APIError
from pydantic import TypeAdapter, ValidationError
from supabase import Client

from src.applications.tillegal.retrieval.document_models import RetrievedEvidence, VectorSearchRequest
from src.applications.tillegal.retrieval.retriever import RetrievalError

_EVIDENCE_ADAPTER = TypeAdapter(list[RetrievedEvidence])


class SupabaseVectorRepository:
    """Retrieve typed evidence through the ``search_legal_chunks`` RPC."""

    def __init__(self, client: Client) -> None:
        self._client = client

    async def search(self, request: VectorSearchRequest) -> tuple[RetrievedEvidence, ...]:
        """Run the synchronous Supabase client call off the event loop."""
        try:
            response_data = await asyncio.to_thread(self._execute_search, request)
        except (APIError, httpx.HTTPError) as error:
            raise RetrievalError("Supabase legal-document search failed") from error

        try:
            evidence = _EVIDENCE_ADAPTER.validate_python(response_data)
        except ValidationError as error:
            raise RetrievalError("Supabase returned evidence that violates the retrieval contract") from error
        return tuple(evidence)

    def _execute_search(self, request: VectorSearchRequest) -> object:
        response = self._client.rpc(
            "search_legal_chunks",
            {
                "p_query_embedding": _format_vector(request.query_embedding),
                "p_dense_index_name": request.dense_index_name,
                "p_top_k": request.top_k,
                "p_as_of_date": request.as_of_date.isoformat(),
                "p_legal_approvals": list(request.allowed_legal_approvals),
                "p_usage_policies": list(request.allowed_usage_policies),
                "p_provenance_statuses": list(request.allowed_provenance_statuses),
                "p_temporal_statuses": list(request.allowed_temporal_statuses),
                "p_rights_statuses": list(request.allowed_rights_statuses),
            },
        ).execute()
        return response.data


def _format_vector(values: tuple[float, ...]) -> str:
    """Serialize validated floats using pgvector's text input format."""
    return f"[{','.join(format(value, '.9g') for value in values)}]"
