"""Coordinate existing parser, encoder and repository without a graph."""

import asyncio
from copy import deepcopy

from src.applications.tillegal.ingestion.data_contracts import DocumentVersion
from src.applications.tillegal.ingestion.legal_parser import parse_document, validate_result
from src.applications.tillegal.ingestion.ports import Embedder, IngestionStore


class IngestionService:
    def __init__(self, store: IngestionStore, embedder: Embedder):
        self.store, self.embedder = store, embedder

    async def ingest(self, document: DocumentVersion, *, parsed: dict | None = None, max_chars: int = 1800) -> str:
        document = DocumentVersion.from_dict(document.to_dict())
        if parsed is None:
            parsed = await asyncio.to_thread(parse_document, document, max_chars)
        else:
            parsed = deepcopy(parsed)
            await asyncio.to_thread(validate_result, document, parsed)
        windows = await self.embedder.embed_documents(parsed["chunks"])
        return await self.store.save(document.to_dict(), parsed, self.embedder.profile, windows)
