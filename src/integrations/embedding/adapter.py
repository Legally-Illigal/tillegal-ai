"""Async boundary for the transferred E5 encoder; one model per instance."""

import asyncio
import threading
import unicodedata
from copy import deepcopy

import numpy as np

from src.applications.tillegal.ingestion.data_contracts import ContractError, canonical_json, content_hash


class LocalEmbeddingAdapter:
    def __init__(self, encoder):
        self.encoder = encoder
        self._lock = threading.Lock()
        self._profile = deepcopy(encoder.config)
        if self._profile.get("dimension") != 384:
            raise ContractError("E5 adapter requires 384 dimensions")
        for field in ("model", "revision", "pooling", "text_policy"):
            if not isinstance(self._profile.get(field), str) or not self._profile[field].strip():
                raise ContractError("Missing embedding profile " + field)

    @property
    def profile(self):
        return deepcopy(self._profile)

    def _validate(self, values, count):
        values = np.asarray(values, dtype=np.float32)
        if values.shape != (count, 384) or not np.isfinite(values).all():
            raise ContractError("Invalid embedding count/dimension/values")
        if not np.allclose(np.linalg.norm(values, axis=1), 1, atol=1e-4):
            raise ContractError("Embedding must be normalized, nonzero E5 vectors")
        return values.tolist()

    def _documents(self, chunks):
        # A thread lock survives coroutine cancellation until actual encode completes.
        with self._lock:
            rows, texts, seen = [], [], set()
            for chunk in chunks:
                for key in ("chunk_id", "document_id", "document_version_id", "text"):
                    if not isinstance(chunk.get(key), str) or not chunk[key].strip():
                        raise ContractError("Invalid chunk " + key)
                if chunk["chunk_id"] in seen or content_hash(chunk["text"]) != chunk.get("text_sha256"):
                    raise ContractError("Duplicate chunk or changed text")
                seen.add(chunk["chunk_id"])
                normalized = unicodedata.normalize("NFC", chunk["text"])
                windows = self.encoder.windows(chunk["text"])
                if not windows:
                    raise ContractError("Encoder returned no windows")
                for ordinal, (start, end, text) in enumerate(windows):
                    if not 0 <= start < end <= len(normalized) or normalized[start:end] != text:
                        raise ContractError("Invalid NFC window mapping")
                    row = {
                        "document_id": chunk["document_id"],
                        "document_version_id": chunk["document_version_id"],
                        "chunk_id": chunk["chunk_id"],
                        "ordinal": ordinal,
                        "window_count": len(windows),
                        "start": start,
                        "end": end,
                        "offset_representation": "NFC_CHUNK_TEXT",
                        "text_sha256": content_hash(text),
                    }
                    row["window_id"] = "window:" + content_hash(canonical_json([row, self._profile]).decode())
                    rows.append(row)
                    texts.append(text)
            if not rows:
                return []
            values = self._validate(self.encoder.encode(texts, "passage"), len(rows))
            return [dict(row, vector=vector) for row, vector in zip(rows, values)]

    async def embed_documents(self, chunks):
        if not isinstance(chunks, list):
            raise ContractError("chunks must be a list")
        return await asyncio.to_thread(self._documents, deepcopy(chunks))

    def _query(self, question):
        with self._lock:
            return self._validate(self.encoder.encode([question], "query"), 1)[0]

    async def embed_query(self, question):
        if not isinstance(question, str) or not question.strip():
            raise ContractError("query must be nonblank text")
        return await asyncio.to_thread(self._query, question)
