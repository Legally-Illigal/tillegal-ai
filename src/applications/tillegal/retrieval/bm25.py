"""T4 experimental BM25 retrieval. No legal approval or citation verification."""

from __future__ import annotations

import hashlib
import math
import re
import unicodedata
from collections import Counter, defaultdict
from copy import deepcopy
from time import perf_counter

from src.applications.tillegal.ingestion import legal_parser
from src.applications.tillegal.ingestion.data_contracts import ContractError, canonical_json

INDEX_SCHEMA = "1"
ALGORITHM_VERSION = "bm25-okapi-v1"
TOKENIZER = {
    "version": "vi-syllable-nfc-v1",
    "unicode_version": unicodedata.unidata_version,
    "case": "casefold",
    "accents": "preserve",
    "stopwords": False,
    "markers_excluded": ["[IMAGE]", "[EMPTY_TABLE]"],
    "query_tf": "binary",
}
DEFAULT_CONFIG = {"k1": 1.2, "b": 0.75}
STATUS_FIELDS = {
    "usage_policy": "EXPERIMENTAL_ONLY",
    "legal_approval": "QUARANTINE",
    "provenance_status": "UNVERIFIED",
    "rights_status": "UNVERIFIED",
    "temporal_status": "UNKNOWN",
}


def digest(value):
    return hashlib.sha256(canonical_json(value)).hexdigest()


def tokenize(text: str) -> list[str]:
    """Accent-preserving syllables/alphanumerics, NOT Vietnamese word segmentation.

    Keep negation and numbers; punctuation separates tokens. Do not modify source
    text or reuse token positions as source offsets. Parser markers are not prose.
    """
    if not isinstance(text, str):
        raise ContractError("text/query must be a string")
    for marker in TOKENIZER["markers_excluded"]:
        text = text.replace(marker, " ")
    return re.findall(r"[^\W_]+", unicodedata.normalize("NFC", text).casefold(), re.UNICODE)


def validate_config(config):
    if not isinstance(config, dict) or set(config) != {"k1", "b"}:
        raise ContractError("BM25 config requires k1 and b")
    for name, value in config.items():
        if type(value) not in (float, int) or not math.isfinite(value):
            raise ContractError(f"{name} must be finite numeric, not boolean")
    if config["k1"] <= 0 or not 0 <= config["b"] <= 1:
        raise ContractError("require k1 > 0 and 0 <= b <= 1")


def term_statistics(chunks):
    postings = defaultdict(list)
    lengths = []
    for ordinal, chunk in enumerate(chunks):
        counts = Counter(tokenize(chunk["text"]))
        lengths.append(sum(counts.values()))
        for token, count in sorted(counts.items()):
            postings[token].append([ordinal, count])
    if not lengths or not sum(lengths):
        raise ContractError("index needs at least one searchable token")
    return {
        "lengths": lengths,
        "average_length": sum(lengths) / len(lengths),
        "postings": dict(sorted(postings.items())),
    }


class BM25Index:
    """Small in-memory index. Payload and results are defensive copies."""

    def __init__(self, payload):
        payload = deepcopy(payload)
        if (
            payload.get("schema_version") != INDEX_SCHEMA
            or payload.get("algorithm_version") != ALGORITHM_VERSION
            or payload.get("tokenizer") != TOKENIZER
            or payload.get("usage_policy") != "EXPERIMENTAL_ONLY"
            or payload.get("approved_for_legal_verification") is not False
            or payload.get("corpus_snapshot_id") is not None
        ):
            raise ContractError("incompatible or promoted index")
        validate_config(payload["config"])
        chunks = payload["chunks"]
        if [c["chunk_id"] for c in chunks] != sorted({c["chunk_id"] for c in chunks}):
            raise ContractError("chunks must be unique and sorted by chunk_id")
        if payload["statistics"] != term_statistics(chunks):
            raise ContractError("index term statistics mismatch")
        self._documents = {d["document_version_id"]: d for d in payload["documents"]}
        if len(self._documents) != len(payload["documents"]) or set(payload["nodes"]) != set(self._documents):
            raise ContractError("index document/node inventory mismatch")
        self._nodes = {n["node_id"]: n for nodes in payload["nodes"].values() for n in nodes}
        self._block_chunks = defaultdict(list)
        self._heading_chunks = defaultdict(list)
        heading_blocks = {n["heading_block_id"] for n in self._nodes.values() if n["heading_block_id"]}
        for chunk in chunks:
            document = self._documents.get(chunk["document_version_id"])
            if document is None or document["document_id"] != chunk["document_id"]:
                raise ContractError("chunk document identity mismatch")
            if any(chunk.get(k) != v or document.get(k) != v for k, v in STATUS_FIELDS.items()):
                raise ContractError("experimental source status mismatch")
            if chunk["attachment_status"] not in legal_parser.ATTACHMENT_STATUSES:
                raise ContractError("unknown attachment status")
            locator = chunk["source_locator"]
            if (
                locator["content_sha256"] != document["content_sha256"]
                or locator["end_exclusive"] is not True
                or locator["offset_unit"] != "unicode_code_point"
            ):
                raise ContractError("source locator mismatch")
            if hashlib.sha256(chunk["text"].encode("utf-8")).hexdigest() != chunk["text_sha256"]:
                raise ContractError("chunk text hash mismatch")
            if any(n not in self._nodes for n in chunk["ancestor_ids"]) or chunk["node_id"] not in self._nodes:
                raise ContractError("missing context node")
            self._block_chunks[chunk["block_id"]].append(chunk["chunk_id"])
            if chunk["block_id"] in heading_blocks:
                self._heading_chunks[chunk["block_id"]].append(chunk["chunk_id"])
        by_id = {c["chunk_id"]: c for c in chunks}
        for ids in self._block_chunks.values():
            ids.sort(key=lambda cid: by_id[cid]["text_start"])
        self._payload = payload
        self.index_id = "bm25:" + digest(payload)

    def to_dict(self):
        return deepcopy(self._payload)

    def _context_and_cautions(self, chunk):
        ancestry = [self._nodes[n] for n in chunk["ancestor_ids"]]
        cautions = ["EXPERIMENTAL_UNVERIFIED_SOURCE", "LEGAL_SUPPORT_NOT_EVALUATED"]
        address_status = {
            "STRUCTURAL": "RULE_BASED_UNVERIFIED",
            "HEURISTIC": "HEURISTIC_CANDIDATE",
            "REVIEW_REQUIRED": "REVIEW_REQUIRED",
        }[chunk["attachment_status"]]
        if chunk["attachment_status"] != "STRUCTURAL":
            cautions.append("ATTACHMENT_" + chunk["attachment_status"])
        if chunk["block_kind"] == "table":
            cautions.append("TABLE_REQUIRES_RAW_LAYOUT")
        cautions.extend(chunk["issues"])
        if chunk["scope"] == "quoted":
            cautions.append("QUOTED_ADDRESS_IS_OUTER_CONTEXT")
        if any(n["heading_block_id"] == chunk["block_id"] for n in ancestry):
            cautions.append("HEADING_BLOCK_MAY_REQUIRE_BODY")
        refs = {
            "block_chunk_ids": self._block_chunks[chunk["block_id"]],
            "ancestor_heading_chunk_ids": sorted(
                {
                    cid
                    for n in ancestry
                    for cid in self._heading_chunks.get(n["heading_block_id"], [])
                    if cid != chunk["chunk_id"]
                }
            ),
            "ancestor_ids": chunk["ancestor_ids"],
            "processed_snapshot_id": self._payload["source"]["processed_snapshot_id"],
        }
        return {
            "address_status": address_status,
            "exact_citation_verified": False,
            "legal_evidence_status": "NOT_EVALUATED",
            "context_review_required": True,
            "context_expanded": False,
            "cautions": sorted(set(cautions)),
            "context_refs": refs,
        }

    def search(self, query, top_k=5):
        started = perf_counter()
        if type(top_k) is not int or not 1 <= top_k <= 100:
            raise ContractError("top_k must be an integer in [1,100]")
        if not isinstance(query, str) or len(query) > 10000:
            raise ContractError("query must be a string of at most 10000 characters")
        tokens = sorted(set(tokenize(query)))
        stats = self._payload["statistics"]
        known = [t for t in tokens if t in stats["postings"]]
        scores = defaultdict(float)
        matched = defaultdict(list)
        n = len(self._payload["chunks"])
        k1, b = self._payload["config"]["k1"], self._payload["config"]["b"]
        for token in known:
            postings = stats["postings"][token]
            idf = math.log1p((n - len(postings) + 0.5) / (len(postings) + 0.5))
            for ordinal, tf in postings:
                norm = k1 * (1 - b + b * stats["lengths"][ordinal] / stats["average_length"])
                scores[ordinal] += idf * tf * (k1 + 1) / (tf + norm)
                matched[ordinal].append(token)
        ordered = sorted(scores, key=lambda i: (-scores[i], self._payload["chunks"][i]["chunk_id"]))[:top_k]
        results = []
        for rank, ordinal in enumerate(ordered, 1):
            chunk = self._payload["chunks"][ordinal]
            results.append(
                {
                    "rank": rank,
                    "bm25_score": scores[ordinal],
                    "matched_terms": matched[ordinal],
                    "chunk": chunk,
                    "document": self._documents[chunk["document_version_id"]],
                    **self._context_and_cautions(chunk),
                }
            )
        response = deepcopy(
            {
                "schema_version": "1",
                "retrieval_method": "BM25",
                "index_id": self.index_id,
                "source": self._payload["source"],
                "corpus_snapshot_id": None,
                "usage_policy": "EXPERIMENTAL_ONLY",
                "query": query,
                "query_tokens": tokens,
                "unmatched_terms": [t for t in tokens if t not in stats["postings"]],
                "top_k": top_k,
                "status": "EMPTY_QUERY" if not tokens else "OK" if results else "NO_MATCH",
                "results": results,
            }
        )
        response["latency_ms"] = (perf_counter() - started) * 1000
        return response
