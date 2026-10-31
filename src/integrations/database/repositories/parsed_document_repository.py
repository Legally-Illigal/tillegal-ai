"""Atomic persistence for parser output and its retrieval chunks."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator
from supabase import Client

from src.integrations.database.repositories.rpc import DatabaseRepositoryError, SupabaseRpcRepository


class DocumentStructureWrite(BaseModel):
    """Parser/version metadata for one parsed source document."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_document_id: UUID
    schema_version: str = Field(min_length=1)
    parser_version: str = Field(min_length=1)
    content_sha256: str = Field(min_length=1)
    max_chars: int | None = Field(default=None, ge=0)
    excluded_segments: list[dict[str, Any]] = Field(default_factory=list)
    issues: list[dict[str, Any]] = Field(default_factory=list)


class DocumentNodeWrite(BaseModel):
    """One hierarchical node in a parsed document."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    node_id: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    parent_node_id: str | None = None
    label: str | None = None
    scope: str | None = None
    heading_block_id: str | None = None
    ordinal: int | None = Field(default=None, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentBlockWrite(BaseModel):
    """One text block associated with a parsed node."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    block_id: str = Field(min_length=1)
    content: str
    node_id: str | None = None
    block_type: str = "paragraph"
    ordinal: int = Field(default=0, ge=0)
    start_offset: int | None = Field(default=None, ge=0)
    end_offset: int | None = Field(default=None, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_offsets(self) -> DocumentBlockWrite:
        if self.start_offset is not None and self.end_offset is not None:
            if self.end_offset < self.start_offset:
                raise ValueError("end_offset must be greater than or equal to start_offset")
        return self


class RetrievalChunkWrite(BaseModel):
    """One searchable text segment mapped to parsed structure."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    chunk_key: str = Field(min_length=1)
    content: str = Field(min_length=1)
    content_sha256: str = Field(min_length=1)
    node_id: str | None = None
    block_id: str | None = None
    chunk_type: str = "text"
    ordinal: int = Field(default=0, ge=0)
    start_offset: int | None = Field(default=None, ge=0)
    end_offset: int | None = Field(default=None, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_offsets(self) -> RetrievalChunkWrite:
        if self.start_offset is not None and self.end_offset is not None:
            if self.end_offset < self.start_offset:
                raise ValueError("end_offset must be greater than or equal to start_offset")
        return self


class ParsedDocumentWrite(BaseModel):
    """Parser output persisted as one transaction by a PostgreSQL RPC."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    structure: DocumentStructureWrite
    nodes: tuple[DocumentNodeWrite, ...] = ()
    blocks: tuple[DocumentBlockWrite, ...] = ()
    chunks: tuple[RetrievalChunkWrite, ...] = ()


class ParsedDocumentRepository(SupabaseRpcRepository):
    """Persist a structure, its nodes/blocks, and chunks atomically."""

    def __init__(self, client: Client) -> None:
        super().__init__(client)

    async def save(self, parsed_document: ParsedDocumentWrite) -> UUID:
        """Save all parser output in one database transaction."""
        result = await self.call_rpc(
            "save_parsed_document",
            {
                "p_structure": parsed_document.structure.model_dump(mode="json"),
                "p_nodes": [node.model_dump(mode="json") for node in parsed_document.nodes],
                "p_blocks": [block.model_dump(mode="json") for block in parsed_document.blocks],
                "p_chunks": [chunk.model_dump(mode="json") for chunk in parsed_document.chunks],
            },
        )
        if not isinstance(result, str):
            raise DatabaseRepositoryError("save_parsed_document returned an invalid response")
        try:
            return UUID(result)
        except ValueError as error:
            raise DatabaseRepositoryError("save_parsed_document returned an invalid structure identifier") from error
