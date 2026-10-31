"""Sparse BM25 retrieval through the Supabase RPC."""

from datetime import date
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictStr, TypeAdapter, ValidationError, field_validator
from supabase import Client

from src.integrations.database.repositories.rpc import DatabaseRepositoryError, SupabaseRpcRepository

_HIT_LIST_ADAPTER = TypeAdapter(list[dict[str, Any]])


class SparseSearchRequest(BaseModel):
    """Search terms and mandatory source-governance filters for sparse retrieval."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    sparse_index_name: str = Field(min_length=1)
    terms: tuple[StrictStr, ...] = Field(min_length=1)
    top_k: int = Field(default=10, ge=1, le=50)
    as_of_date: date
    allowed_legal_approvals: tuple[StrictStr, ...] = Field(min_length=1)
    allowed_usage_policies: tuple[StrictStr, ...] = Field(min_length=1)
    allowed_provenance_statuses: tuple[StrictStr, ...] = Field(min_length=1)
    allowed_temporal_statuses: tuple[StrictStr, ...] = Field(min_length=1)
    allowed_rights_statuses: tuple[StrictStr, ...] = Field(min_length=1)

    @field_validator(
        "terms",
        "allowed_legal_approvals",
        "allowed_usage_policies",
        "allowed_provenance_statuses",
        "allowed_temporal_statuses",
        "allowed_rights_statuses",
    )
    @classmethod
    def reject_blank_values(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(not value.strip() for value in values):
            raise ValueError("Search terms and source status allowlists must not contain blank values")
        return tuple(dict.fromkeys(value.strip() for value in values))

    @field_validator("sparse_index_name")
    @classmethod
    def reject_blank_index_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("sparse_index_name must not be blank")
        return value


class SparseSearchHit(BaseModel):
    """Ranked chunk identifier from inverted-index retrieval."""

    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)

    retrieval_chunk_id: UUID
    score: float


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
                "p_legal_approvals": list(request.allowed_legal_approvals),
                "p_usage_policies": list(request.allowed_usage_policies),
                "p_provenance_statuses": list(request.allowed_provenance_statuses),
                "p_temporal_statuses": list(request.allowed_temporal_statuses),
                "p_rights_statuses": list(request.allowed_rights_statuses),
            },
        )
        try:
            rows = _HIT_LIST_ADAPTER.validate_python(result)
            return tuple(SparseSearchHit.model_validate(row) for row in rows)
        except ValidationError as error:
            raise DatabaseRepositoryError("search_sparse_legal_chunks returned an invalid response") from error
