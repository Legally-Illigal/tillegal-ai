"""Read operations for parsed retrieval chunks."""

import asyncio
from uuid import UUID

import httpx
from postgrest.exceptions import APIError
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
        """Read bounded table pages; RPC SETOF JSONB does not expose order columns."""
        rows: list[dict[str, object]] = []
        seen: set[UUID] = set()
        previous: tuple[int, UUID] | None = None
        expected: int | None = None
        batch_size = 250
        while True:
            offset = len(rows)
            try:
                response = await asyncio.to_thread(
                    lambda: (
                        self._client.table("retrieval_chunks")
                        .select("*", count="exact")
                        .eq("source_document_id", str(source_document_id))
                        .order("ordinal")
                        .order("id")
                        .range(offset, offset + batch_size - 1)
                        .execute()
                    )
                )
                if not isinstance(getattr(response, "data", None), list):
                    raise ValueError("Invalid page")
                page = _CHUNK_LIST_ADAPTER.validate_python(response.data)
                count = getattr(response, "count", None)
                if type(count) is not int or count < 0 or (expected is not None and count != expected):
                    raise ValueError("Invalid or changed count")
                expected = count
                if len(page) > batch_size or len(rows) + len(page) > expected:
                    raise ValueError("Invalid page size")
                for row in page:
                    identifier = UUID(str(row.get("id")))
                    ordinal = row.get("ordinal")
                    if type(ordinal) is not int or row.get("source_document_id") != str(source_document_id):
                        raise ValueError("Invalid chunk")
                    key = (ordinal, identifier)
                    if identifier in seen or (previous is not None and key <= previous):
                        raise ValueError("Chunk pagination did not advance")
                    seen.add(identifier)
                    previous = key
                rows.extend(page)
                if len(rows) == expected:
                    return tuple(rows)
                if not page:
                    raise ValueError("Incomplete chunks")
            except (ValueError, APIError, httpx.HTTPError) as error:
                raise DatabaseRepositoryError("Chunk pagination failed validation or request") from error
