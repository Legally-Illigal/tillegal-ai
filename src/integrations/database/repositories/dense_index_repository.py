"""Dense-index metadata and embedding lifecycle operations."""

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError
from supabase import Client

from src.integrations.database.repositories.rpc import DatabaseRepositoryError, SupabaseRpcRepository

_ROW_LIST_ADAPTER = TypeAdapter(list[dict[str, object]])


class DenseIndexWrite(BaseModel):
    """Configuration for a dense embedding index."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    index_name: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    model_name: str = Field(min_length=1)
    embedding_dimension: Literal[1536] = 1536
    distance_metric: Literal["cosine"] = "cosine"
    index_version: str = "v1"
    status: Literal["BUILDING", "READY", "STALE", "FAILED", "DISABLED"] = "BUILDING"
    metadata: dict[str, Any] = Field(default_factory=dict)


class DenseEmbeddingWrite(BaseModel):
    """Embedding data for one retrieval chunk."""

    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)

    retrieval_chunk_id: UUID
    embedding: tuple[float, ...] = Field(min_length=1536, max_length=1536)
    embedded_text_sha256: str = Field(min_length=1)
    status: Literal["INDEXED"] = "INDEXED"
    metadata: dict[str, Any] = Field(default_factory=dict)


class DenseEmbeddingStatusWrite(BaseModel):
    """A non-indexed embedding outcome, including retries and failures."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    retrieval_chunk_id: UUID
    embedded_text_sha256: str = Field(min_length=1)
    status: Literal["PENDING", "STALE", "FAILED", "SKIPPED"]
    error_message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DenseIndexRepository(SupabaseRpcRepository):
    """Manage dense index definitions and embedding state."""

    def __init__(self, client: Client) -> None:
        super().__init__(client)

    async def upsert_index(self, index: DenseIndexWrite) -> dict[str, object]:
        result = await self.call_rpc(
            "upsert_dense_index",
            {"p_index": index.model_dump(mode="json")},
        )
        if not isinstance(result, dict):
            raise DatabaseRepositoryError("upsert_dense_index returned an invalid response")
        return result

    async def get_index(self, index_name: str) -> dict[str, object] | None:
        result = await self.call_rpc("get_dense_index", {"p_index_name": index_name})
        if result is None:
            return None
        if not isinstance(result, dict):
            raise DatabaseRepositoryError("get_dense_index returned an invalid response")
        return result

    async def upsert_embeddings(
        self,
        index_name: str,
        embeddings: tuple[DenseEmbeddingWrite, ...],
    ) -> int:
        result = await self.call_rpc(
            "upsert_dense_embeddings",
            {
                "p_index_name": index_name,
                "p_embeddings": [embedding.model_dump(mode="json") for embedding in embeddings],
            },
        )
        if not isinstance(result, int):
            raise DatabaseRepositoryError("upsert_dense_embeddings returned an invalid response")
        return result

    async def record_embedding_statuses(
        self,
        index_name: str,
        statuses: tuple[DenseEmbeddingStatusWrite, ...],
    ) -> int:
        result = await self.call_rpc(
            "upsert_dense_embedding_statuses",
            {
                "p_index_name": index_name,
                "p_statuses": [status.model_dump(mode="json") for status in statuses],
            },
        )
        if not isinstance(result, int):
            raise DatabaseRepositoryError("upsert_dense_embedding_statuses returned an invalid response")
        return result

    async def list_embedding_work(
        self,
        index_name: str,
        statuses: tuple[str, ...] = ("PENDING", "STALE", "FAILED"),
        limit: int = 100,
    ) -> tuple[dict[str, object], ...]:
        result = await self.call_rpc(
            "list_dense_embedding_work",
            {"p_index_name": index_name, "p_statuses": list(statuses), "p_limit": limit},
        )
        try:
            return tuple(_ROW_LIST_ADAPTER.validate_python(result))
        except ValidationError as error:
            raise DatabaseRepositoryError("list_dense_embedding_work returned an invalid response") from error
