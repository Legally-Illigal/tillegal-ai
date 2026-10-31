"""Sparse/inverted-index lifecycle and posting operations."""

from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictStr, TypeAdapter, ValidationError
from supabase import Client

from src.integrations.database.repositories.rpc import (
    DatabaseRepositoryError,
    SupabaseRpcRepository,
)

_ROW_LIST_ADAPTER = TypeAdapter(list[dict[str, object]])


class SparseIndexWrite(BaseModel):
    """Configuration and statistics for a sparse BM25 index."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    index_name: str = Field(min_length=1)
    algorithm: Literal["BM25"] = "BM25"
    tokenizer: str = "unicode"
    language_config: str = "simple"
    k1: float = Field(default=1.2, gt=0)
    b: float = Field(default=0.75, ge=0, le=1)
    index_version: str = "v1"
    status: Literal["BUILDING", "READY", "STALE", "FAILED", "DISABLED"] = "BUILDING"
    metadata: dict[str, Any] = Field(default_factory=dict)


class SparsePostingWrite(BaseModel):
    """A normalized term and its positions in one chunk."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    term: StrictStr = Field(min_length=1)
    term_frequency: int = Field(default=1, gt=0)
    positions: tuple[Annotated[int, Field(ge=0)], ...] | None = None


class SparseChunkWrite(BaseModel):
    """Tokenized chunk state and postings for one sparse index."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    retrieval_chunk_id: UUID
    token_count: int = Field(ge=0)
    indexed_text_sha256: str = Field(min_length=1)
    status: Literal["PENDING", "INDEXED", "STALE", "FAILED", "SKIPPED"] = "INDEXED"
    metadata: dict[str, Any] = Field(default_factory=dict)
    postings: tuple[SparsePostingWrite, ...] = ()


class SparseIndexRepository(SupabaseRpcRepository):
    """Manage sparse indexes, chunk documents, and inverted postings."""

    def __init__(self, client: Client) -> None:
        super().__init__(client)

    async def upsert_index(self, index: SparseIndexWrite) -> dict[str, object]:
        result = await self.call_rpc(
            "upsert_sparse_index",
            {"p_index": index.model_dump(mode="json")},
        )
        if not isinstance(result, dict):
            raise DatabaseRepositoryError("upsert_sparse_index returned an invalid response")
        return result

    async def get_index(self, index_name: str) -> dict[str, object] | None:
        result = await self.call_rpc("get_sparse_index", {"p_index_name": index_name})
        if result is None:
            return None
        if not isinstance(result, dict):
            raise DatabaseRepositoryError("get_sparse_index returned an invalid response")
        return result

    async def upsert_chunk_documents(
        self,
        index_name: str,
        chunks: tuple[SparseChunkWrite, ...],
    ) -> int:
        result = await self.call_rpc(
            "upsert_sparse_chunk_documents",
            {
                "p_index_name": index_name,
                "p_chunks": [chunk.model_dump(mode="json") for chunk in chunks],
            },
        )
        if not isinstance(result, int):
            raise DatabaseRepositoryError("upsert_sparse_chunk_documents returned an invalid response")
        return result

    async def list_index_work(
        self,
        index_name: str,
        statuses: tuple[str, ...] = ("PENDING", "STALE", "FAILED"),
        limit: int = 100,
    ) -> tuple[dict[str, object], ...]:
        result = await self.call_rpc(
            "list_sparse_index_work",
            {"p_index_name": index_name, "p_statuses": list(statuses), "p_limit": limit},
        )
        try:
            return tuple(_ROW_LIST_ADAPTER.validate_python(result))
        except ValidationError as error:
            raise DatabaseRepositoryError("list_sparse_index_work returned an invalid response") from error
