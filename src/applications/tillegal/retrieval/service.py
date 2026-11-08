"""Repository-backed corpus, BM25/RRF, window cosine and evidence assembly."""

import asyncio
import threading
import unicodedata
from collections import defaultdict
from copy import deepcopy

import numpy as np

from src.applications.tillegal.ingestion.data_contracts import (
    ContractError,
    DocumentVersion,
    canonical_json,
    content_hash,
)
from src.applications.tillegal.ingestion.legal_parser import validate_result
from src.applications.tillegal.retrieval.bm25 import (
    ALGORITHM_VERSION,
    DEFAULT_CONFIG,
    INDEX_SCHEMA,
    TOKENIZER,
    BM25Index,
    digest,
    term_statistics,
)
from src.applications.tillegal.retrieval.contracts import response, validate_query
from src.applications.tillegal.retrieval.evidence_builder import EvidenceBuilder
from src.applications.tillegal.retrieval.hybrid import HybridRetriever


def corpus_index(records):
    if not records:
        raise ContractError("No ingested versions selected")
    for record in records:
        validate_result(DocumentVersion.from_dict(record["document"]), record["parsed"])
    chunks = sorted([c for r in records for c in r["parsed"]["chunks"]], key=lambda c: c["chunk_id"])
    return BM25Index(
        {
            "schema_version": INDEX_SCHEMA,
            "algorithm_version": ALGORITHM_VERSION,
            "tokenizer": TOKENIZER,
            "config": DEFAULT_CONFIG,
            "usage_policy": "EXPERIMENTAL_ONLY",
            "approved_for_legal_verification": False,
            "corpus_snapshot_id": None,
            "source": {"processed_snapshot_id": digest([r["parsed"] for r in records])},
            "documents": [{k: v for k, v in r["document"].items() if k != "content"} for r in records],
            "nodes": {r["document"]["document_version_id"]: r["parsed"]["nodes"] for r in records},
            "chunks": chunks,
            "statistics": term_statistics(chunks),
        }
    )


class WindowDenseRetriever:
    """Exact max-window cosine from the source algorithm, no local index files."""

    def __init__(self, index, records, vector, profile):
        self.index, self.vector = index, np.asarray(vector, dtype=np.float32)
        self.config = {"encoder": deepcopy(profile), "chunk_aggregation": "max_window_cosine"}
        self.rows = [w for r in records for w in r["windows"]]
        chunks = {c["chunk_id"]: c for c in index.to_dict()["chunks"]}
        by_chunk = defaultdict(list)
        for row in self.rows:
            chunk = chunks.get(row["chunk_id"])
            if chunk is None or any(row[k] != chunk[k] for k in ("document_id", "document_version_id")):
                raise ContractError("Window/version mismatch")
            nfc = unicodedata.normalize("NFC", chunk["text"])
            start, end = row["start"], row["end"]
            if (
                not 0 <= start < end <= len(nfc)
                or row["offset_representation"] != "NFC_CHUNK_TEXT"
                or content_hash(nfc[start:end]) != row["text_sha256"]
            ):
                raise ContractError("Window locator mismatch")
            fields = {k: v for k, v in row.items() if k not in ("vector", "window_id")}
            if row["window_id"] != "window:" + content_hash(canonical_json([fields, profile]).decode()):
                raise ContractError("Window/profile fingerprint mismatch")
            by_chunk[row["chunk_id"]].append(row)
        if set(by_chunk) != set(chunks):
            raise ContractError("Window/chunk inventory mismatch")
        for rows in by_chunk.values():
            if sorted(w["ordinal"] for w in rows) != list(range(len(rows))) or any(
                w["window_count"] != len(rows) for w in rows
            ):
                raise ContractError("Window count or ordinal mismatch")
        self.vectors = np.asarray([w["vector"] for w in self.rows], dtype=np.float32)
        if self.vectors.shape != (len(self.rows), 384) or self.vector.shape != (384,):
            raise ContractError("Dense dimension mismatch")
        if not np.isfinite(self.vectors).all() or not np.isfinite(self.vector).all():
            raise ContractError("Non-finite dense vector")
        if not np.allclose(np.linalg.norm(self.vectors, axis=1), 1, atol=1e-4):
            raise ContractError("Invalid dense normalization")

    def search(self, query, top_k=5):
        validate_query(query, top_k)
        scores = {}
        if query.strip():
            for row, score in zip(self.rows, self.vectors @ self.vector):
                cid = row["chunk_id"]
                scores[cid] = max(scores.get(cid, -float("inf")), float(score))
        ranked = sorted(scores, key=lambda cid: (-scores[cid], cid))[:top_k]
        return response(
            self.index,
            query,
            [(cid, scores[cid], {"dense_score": scores[cid]}) for cid in ranked],
            "DENSE",
            self.config,
        )


class RetrievalService:
    def __init__(self, store, embedder, reranker=None):
        self.store, self.embedder, self.reranker = store, embedder, reranker
        self._rerank_lock = threading.Lock()

    async def search(
        self,
        question: str,
        *,
        version_ids: tuple[str, ...],
        request_id: str,
        method: str = "hybrid",
        top_k: int = 5,
        budget=None,
    ):
        validate_query(question, top_k)
        if method not in ("bm25", "dense", "hybrid"):
            raise ContractError("Unknown retrieval method")
        records = await self.store.load(version_ids, self.embedder.profile)
        if not version_ids or len(set(version_ids)) != len(version_ids):
            raise ContractError("Expected explicit unique version IDs")
        ids = [r["document"]["document_version_id"] for r in records]
        if sorted(ids) != sorted(version_ids) or any(r["profile"] != self.embedder.profile for r in records):
            raise ContractError("Unexpected corpus or embedding profile")
        records.sort(key=lambda r: r["document"]["document_version_id"])
        index = await asyncio.to_thread(corpus_index, records)
        if method == "bm25":
            retriever = index
        else:
            vector = await self.embedder.embed_query(question) if question.strip() else [0.0] * 384
            dense = await asyncio.to_thread(WindowDenseRetriever, index, records, vector, self.embedder.profile)
            retriever = (
                dense
                if method == "dense"
                else HybridRetriever(index, dense, branch_k=max(20, top_k), reranker=self.reranker)
            )

        def rank_and_build():
            if method == "hybrid" and self.reranker is not None:
                with self._rerank_lock:
                    ranked = retriever.search(question, top_k)
            else:
                ranked = retriever.search(question, top_k)
            return ranked, EvidenceBuilder(index, budget).build(ranked, request_id=request_id)

        result, bundle = await asyncio.to_thread(rank_and_build)
        return {"retrieval": result, "evidence_bundle": bundle}
