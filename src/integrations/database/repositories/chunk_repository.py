"""Read operations for parsed retrieval chunks."""

from uuid import UUID

from pydantic import TypeAdapter, ValidationError
from supabase import Client

from src.integrations.database.repositories.rpc import DatabaseRepositoryError, SupabaseRpcRepository

_CHUNK_LIST_ADAPTER = TypeAdapter(list[dict[str, object]])


class ChunkRepository(SupabaseRpcRepository):
    """Load stored chunks for citation reconstruction and follow-up retrieval."""

    def __init__(self, client: Client) -> None:
        super().__init__(client)

    async def get_by_ids(self, chunk_ids: tuple[UUID, ...]) -> tuple[dict[str, object], ...]:
        """Load chunks by stable identifiers; an empty request returns no rows."""
        if not chunk_ids:
            return ()
        result = await self.call_rpc(
            "get_retrieval_chunks",
            {"p_chunk_ids": [str(chunk_id) for chunk_id in chunk_ids]},
        )
        try:
            return tuple(_CHUNK_LIST_ADAPTER.validate_python(result))
        except ValidationError as error:
            raise DatabaseRepositoryError("get_retrieval_chunks returned an invalid response") from error

    async def list_for_document(self, source_document_id: UUID) -> tuple[dict[str, object], ...]:
        """Load chunks in document order for inspection or citation assembly."""
        result = await self.call_rpc(
            "list_retrieval_chunks_for_document",
            {"p_source_document_id": str(source_document_id)},
        )
        try:
            return tuple(_CHUNK_LIST_ADAPTER.validate_python(result))
        except ValidationError as error:
            raise DatabaseRepositoryError("list_retrieval_chunks_for_document returned an invalid response") from error
