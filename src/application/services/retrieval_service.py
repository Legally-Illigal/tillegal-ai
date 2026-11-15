"""Read-only retrieval use case with explicit readiness and consistency guards."""

import asyncio
import hashlib
from collections.abc import Callable
from datetime import date, datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictStr, TypeAdapter, ValidationError, model_validator

from src.application.services.hybrid_retrieval import search_hybrid
from src.applications.tillegal.retrieval.contracts import (
    IndexIdentity,
    RetrievalMode,
    RetrievalRequest,
    RetrievalResponse,
    RetrievalWarning,
    UnifiedEvidence,
)
from src.applications.tillegal.retrieval.document_models import (
    RetrievedEvidence,
    SparseSearchHit,
    SparseSearchRequest,
    VectorSearchRequest,
)
from src.applications.tillegal.retrieval.errors import (
    ErrorCategory,
    RetrievalErrorDetail,
    RetrievalServiceError,
)
from src.applications.tillegal.retrieval.hybrid_models import HybridConfig, HybridRetrievalResponse
from src.applications.tillegal.retrieval.ports import (
    ChunkReader,
    IndexReader,
    QueryEmbedder,
    SourceReader,
    SparseRetriever,
)
from src.applications.tillegal.retrieval.retriever import LegalRetriever, RetrievalError
from src.applications.tillegal.retrieval.vector_validation import validate_query_vector
from src.core.clock import utc_now
from src.core.identifiers import new_id
from src.integrations.database.repositories.rpc import DatabaseRepositoryError

DEFAULT_SPARSE_INDEX = "vbpl-bm25-unicode-v1"
DEFAULT_DENSE_INDEX = "vbpl-multilingual-e5-small-v1"
_HITS = TypeAdapter(tuple[SparseSearchHit, ...])
_DENSE_HITS = TypeAdapter(tuple[RetrievedEvidence, ...])


class _ChunkRow(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: UUID
    source_document_id: UUID
    document_structure_id: UUID
    chunk_key: StrictStr = Field(min_length=1)
    content: StrictStr = Field(min_length=1)
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    node_id: str | None = None
    block_id: str | None = None
    chunk_type: StrictStr = Field(min_length=1)
    start_offset: int | None = None
    end_offset: int | None = None
    metadata: dict[str, object]


class _SourceRow(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: UUID
    title: StrictStr = Field(min_length=1)
    usage_policy: StrictStr = Field(min_length=1)
    raw_metadata: dict[str, object]
    source_id: str | None = None
    source_record_id: str | None = None
    source_snapshot_id: str | None = None
    source_url: str | None = None
    language: str | None = None
    issued_on: date | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    effect_status_reported: str | None = None


class _SparseIndex(BaseModel):
    """Validate the metadata used for search and compare it across RPC reads."""

    model_config = ConfigDict(extra="ignore", frozen=True, allow_inf_nan=False)

    id: UUID
    index_name: str
    index_version: str
    status: str
    updated_at: datetime
    algorithm: str
    tokenizer: str
    language_config: str
    k1: float = Field(gt=0)
    b: float = Field(ge=0, le=1)
    document_count: int = Field(ge=0)
    total_token_count: int = Field(ge=0)
    average_document_length: float = Field(ge=0)
    metadata: dict[str, object]

    @model_validator(mode="after")
    def aware_timestamp(self) -> Self:
        if self.updated_at.utcoffset() is None:
            raise ValueError("index timestamp must include a timezone")
        return self

    def identity(self) -> IndexIdentity:
        return IndexIdentity.model_validate(self.model_dump(include=set(IndexIdentity.model_fields)))


class _DenseIndex(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True, allow_inf_nan=False)

    id: UUID
    index_name: str
    index_version: str
    status: str
    updated_at: datetime
    provider: str
    model_name: str
    embedding_dimension: int
    distance_metric: str
    metadata: dict[str, object]

    def identity(self) -> IndexIdentity:
        # Preserve the public response schema; model config remains an internal check.
        return IndexIdentity.model_validate(self.model_dump(include=set(IndexIdentity.model_fields)))


def _failure(category: ErrorCategory, code: str, stage: str, message: str) -> RetrievalServiceError:
    return RetrievalServiceError(
        RetrievalErrorDetail(
            category=category,
            code=code,
            stage=stage,
            message=message,
        )
    )


class RetrievalService:
    """Coordinate read-only ports. No retries or cross-mode fallback.

    Pre/post metadata checks detect observed index changes, not a database snapshot.
    The existing repository exception is translated without exposing its message.
    """

    def __init__(
        self,
        sparse_retriever: SparseRetriever,
        chunks: ChunkReader,
        sources: SourceReader,
        indexes: IndexReader,
        tokenizer: Callable[[str], tuple[str, ...]],
        *,
        sparse_index_name: str = DEFAULT_SPARSE_INDEX,
        timeout_seconds: float = 30,
        dense_retriever: LegalRetriever | None = None,
        query_embedder: QueryEmbedder | None = None,
        dense_indexes: IndexReader | None = None,
        dense_index_name: str = DEFAULT_DENSE_INDEX,
        hybrid_config: HybridConfig | None = None,
    ) -> None:
        if not sparse_index_name.strip() or not 0 < timeout_seconds < float("inf"):
            raise ValueError("index name and finite positive timeout are required")
        self._sparse = sparse_retriever
        self._chunks = chunks
        self._sources = sources
        self._indexes = indexes
        self._tokenizer = tokenizer
        self._index_name = sparse_index_name.strip()
        self._timeout = timeout_seconds
        self._dense = dense_retriever
        self._query_embedder = query_embedder
        self._dense_indexes = dense_indexes
        self._dense_index_name = dense_index_name
        self._hybrid_config = hybrid_config or HybridConfig()

    async def search(self, request: RetrievalRequest) -> RetrievalResponse | HybridRetrievalResponse:
        """Return a classified outcome; malformed requests never invoke dependencies."""
        request = RetrievalRequest.model_validate(request)
        if request.mode == RetrievalMode.HYBRID:
            return await search_hybrid(
                request,
                run_branch=self.search,
                sparse_indexes=self._indexes,
                dense_indexes=self._dense_indexes,
                sparse_index_name=self._index_name,
                dense_index_name=self._dense_index_name,
                dense_configured=self._dense is not None and self._query_embedder is not None,
                config=self._hybrid_config,
                timeout_seconds=self._timeout,
            )
        request_id = new_id()
        index: _SparseIndex | _DenseIndex | None = None
        evidence: tuple[UnifiedEvidence, ...] = ()
        error: RetrievalErrorDetail | None = None
        stage = "validation"
        try:
            if request.mode == RetrievalMode.DENSE and (
                self._dense is None or self._query_embedder is None or self._dense_indexes is None
            ):
                raise _failure(
                    ErrorCategory.CONFIGURATION_ERROR,
                    "MODE_NOT_CONFIGURED",
                    stage,
                    "Dense retrieval requires a local query encoder and read adapters.",
                )
            async with asyncio.timeout(self._timeout):
                if request.mode == RetrievalMode.BM25:
                    stage = "preprocessing"
                    terms = self._prepare_sparse_terms(request.query.strip())
                    stage = "index_preflight"
                    index = await self._read_and_validate_index()
                    stage = "search"
                    hits = await self._search_sparse(request, terms)
                    stage = "hydration"
                    evidence = await self._hydrate_sparse_hits(hits, request)
                    stage = "index_postflight"
                    await self._check_index_unchanged(index)
                else:
                    stage = "index_preflight"
                    index = await self._read_dense_index()
                    stage = "encoding"
                    vector = await self._query_embedder.encode_query(request.query.strip())
                    try:
                        vector = validate_query_vector(vector)
                    except (TypeError, ValueError) as failure:
                        raise _failure(
                            ErrorCategory.MODEL_UNAVAILABLE,
                            "INVALID_EMBEDDING",
                            stage,
                            "Query encoder returned an invalid normalized vector.",
                        ) from failure
                    stage = "search"
                    dense_hits = await self._dense.search(
                        VectorSearchRequest(
                            dense_index_name=self._dense_index_name,
                            query_embedding=vector,
                            top_k=request.top_k,
                            as_of_date=request.as_of_date,
                            allowed_usage_policies=request.allowed_usage_policies,
                        )
                    )
                    stage = "hydration"
                    evidence = await self._map_dense_evidence(dense_hits, request, index)
                    stage = "index_postflight"
                    await self._check_dense_index_unchanged(index)
        except RetrievalServiceError as failure:
            error = failure.detail
        except TimeoutError:
            error = RetrievalErrorDetail(
                category=ErrorCategory.TIMEOUT,
                code="RETRIEVAL_TIMEOUT",
                stage=stage,
                message="Retrieval exceeded its deadline.",
                retryable=True,
            )
        except (DatabaseRepositoryError, RetrievalError) as failure:
            invalid_response = isinstance(failure.__cause__, ValidationError)
            error = RetrievalErrorDetail(
                category=ErrorCategory.INCONSISTENT_EVIDENCE if invalid_response else ErrorCategory.DATABASE_FAILURE,
                code="INVALID_REPOSITORY_RESPONSE" if invalid_response else "DATABASE_READ_FAILED",
                stage=stage,
                message="Repository returned invalid data." if invalid_response else "Database read failed.",
            )
        return RetrievalResponse(
            **request.model_dump(),
            request_id=request_id,
            query_used=request.query.strip(),
            selected_index_name=self._index_name if request.mode == RetrievalMode.BM25 else self._dense_index_name,
            index=index.identity() if index is not None else None,
            status="FAILED" if error else "OK" if evidence else "NO_MATCH",
            evidence=() if error else evidence,
            warnings=() if error else self._evidence_warnings(evidence),
            error=error,
            retrieved_at=utc_now(),
        )

    def _prepare_sparse_terms(self, query: str) -> tuple[str, ...]:
        """Use the injected indexing tokenizer, without introducing a second tokenizer."""
        terms = tuple(dict.fromkeys(self._tokenizer(query)))
        if not terms:
            raise _failure(
                ErrorCategory.INVALID_REQUEST,
                "EMPTY_TERMS",
                "preprocessing",
                "Query does not contain searchable tokens.",
            )
        return terms

    async def _search_sparse(self, request: RetrievalRequest, terms: tuple[str, ...]) -> tuple[SparseSearchHit, ...]:
        """Pass explicit filters to the existing sparse port, preserving rank and score."""
        raw_hits = await self._sparse.search(
            SparseSearchRequest(
                sparse_index_name=self._index_name,
                terms=terms,
                top_k=request.top_k,
                as_of_date=request.as_of_date,
                allowed_usage_policies=request.allowed_usage_policies,
            )
        )
        try:
            hits = _HITS.validate_python(raw_hits)
        except ValidationError as error:
            raise _failure(
                ErrorCategory.INCONSISTENT_EVIDENCE, "INVALID_HITS", "search", "Sparse search returned invalid hits."
            ) from error
        if len(hits) > request.top_k or any(a.score < b.score for a, b in zip(hits, hits[1:])):
            raise _failure(
                ErrorCategory.INCONSISTENT_EVIDENCE,
                "INVALID_RANKING",
                "search",
                "Sparse search returned an invalid ranking.",
            )
        return hits

    async def _hydrate_sparse_hits(
        self,
        hits: tuple[SparseSearchHit, ...],
        request: RetrievalRequest,
    ) -> tuple[UnifiedEvidence, ...]:
        """Batch chunks, memoize sources per request, then reconstruct original hit order."""
        if not hits:
            return ()
        ids = tuple(hit.retrieval_chunk_id for hit in hits)
        if len(set(ids)) != len(ids):
            raise _failure(
                ErrorCategory.INCONSISTENT_EVIDENCE,
                "DUPLICATE_HITS",
                "hydration",
                "Sparse search returned duplicate chunk identities.",
            )
        rows = await self._chunks.get_by_ids(ids)
        try:
            chunks = tuple(_ChunkRow.model_validate(row) for row in rows)
        except ValidationError as error:
            raise _failure(
                ErrorCategory.INCONSISTENT_EVIDENCE, "INVALID_CHUNK", "hydration", "Stored chunk data is invalid."
            ) from error
        by_id = {chunk.id: chunk for chunk in chunks}
        if len(by_id) != len(chunks) or set(by_id) != set(ids):
            raise _failure(
                ErrorCategory.INCONSISTENT_EVIDENCE,
                "CHUNK_IDENTITY_MISMATCH",
                "hydration",
                "Hydration returned missing, duplicate or unexpected chunks.",
            )
        sources: dict[UUID, _SourceRow] = {}
        evidence = []
        for rank, hit in enumerate(hits, 1):
            chunk = by_id[hit.retrieval_chunk_id]
            source_id = chunk.source_document_id
            if source_id not in sources:
                raw = await self._sources.get(source_id)
                if raw is None:
                    raise _failure(
                        ErrorCategory.INCONSISTENT_EVIDENCE,
                        "SOURCE_MISSING",
                        "hydration",
                        "A retrieved chunk has no source document.",
                    )
                try:
                    source = _SourceRow.model_validate(raw)
                except ValidationError as error:
                    raise _failure(
                        ErrorCategory.INCONSISTENT_EVIDENCE,
                        "INVALID_SOURCE",
                        "hydration",
                        "Source document metadata is invalid.",
                    ) from error
                if source.id != source_id:
                    raise _failure(
                        ErrorCategory.INCONSISTENT_EVIDENCE,
                        "SOURCE_IDENTITY_MISMATCH",
                        "hydration",
                        "Source document identity does not match its chunk.",
                    )
                self._check_eligibility(source, request)
                sources[source_id] = source
            evidence.append(self._make_evidence(chunk, sources[source_id], hit, rank))
        return tuple(evidence)

    @staticmethod
    def _check_eligibility(source: _SourceRow, request: RetrievalRequest) -> None:
        """Reapply the SQL's inclusive filters to the source observed during hydration."""
        if (
            source.effective_from is not None
            and source.effective_to is not None
            and source.effective_to < source.effective_from
        ):
            raise _failure(
                ErrorCategory.INCONSISTENT_EVIDENCE,
                "INVALID_EFFECTIVE_DATES",
                "hydration",
                "Source document dates are inconsistent.",
            )
        if (
            source.usage_policy not in request.allowed_usage_policies
            or (source.effective_from is not None and source.effective_from > request.as_of_date)
            or (source.effective_to is not None and source.effective_to < request.as_of_date)
        ):
            raise _failure(
                ErrorCategory.INCONSISTENT_EVIDENCE,
                "ELIGIBILITY_CHANGED",
                "hydration",
                "Hydrated source no longer satisfies the requested filters.",
            )

    @staticmethod
    def _make_evidence(chunk: _ChunkRow, source: _SourceRow, hit: SparseSearchHit, rank: int) -> UnifiedEvidence:
        """Check the stored content digest; do not alter content or infer legal approval."""
        digest = hashlib.sha256(chunk.content.encode("utf-8")).hexdigest()
        if digest != chunk.content_sha256:
            raise _failure(
                ErrorCategory.INCONSISTENT_EVIDENCE,
                "CONTENT_HASH_MISMATCH",
                "hydration",
                "Stored chunk content does not match its SHA-256.",
            )
        try:
            return UnifiedEvidence(
                **chunk.model_dump(exclude={"id", "metadata"}),
                **source.model_dump(exclude={"id", "raw_metadata"}),
                retrieval_chunk_id=chunk.id,
                chunk_metadata=chunk.metadata,
                source_metadata=source.raw_metadata,
                hash_check="MATCHED_STORED",
                rank=rank,
                raw_score=hit.score,
                score_kind="BM25",
                retrieval_method=RetrievalMode.BM25,
            )
        except ValidationError as error:
            raise _failure(
                ErrorCategory.INCONSISTENT_EVIDENCE,
                "INVALID_EVIDENCE",
                "hydration",
                "Retrieved evidence violates its content or metadata contract.",
            ) from error

    @staticmethod
    def _evidence_warnings(evidence: tuple[UnifiedEvidence, ...]) -> tuple[RetrievalWarning, ...]:
        """Report missing optional locators/dates without synthesizing replacement values."""
        warnings = []
        for item in evidence:
            if not item.source_url:
                warnings.append(
                    RetrievalWarning(
                        code="SOURCE_URL_MISSING",
                        message="Source URL is unavailable.",
                        retrieval_chunk_id=item.retrieval_chunk_id,
                    )
                )
            if item.effective_from is None or item.effective_to is None:
                warnings.append(
                    RetrievalWarning(
                        code="TEMPORAL_METADATA_INCOMPLETE",
                        message="Effective dates are partly unspecified; legal applicability has not been evaluated.",
                        retrieval_chunk_id=item.retrieval_chunk_id,
                    )
                )
        return tuple(warnings)

    async def _read_and_validate_index(self) -> _SparseIndex:
        row = await self._indexes.get_index(self._index_name)
        if row is None:
            raise _failure(
                ErrorCategory.INDEX_UNAVAILABLE,
                "INDEX_NOT_FOUND",
                "index_preflight",
                "Configured sparse index does not exist.",
            )
        try:
            index = _SparseIndex.model_validate(row)
        except ValidationError as error:
            raise _failure(
                ErrorCategory.CONFIGURATION_ERROR,
                "INVALID_INDEX_METADATA",
                "index_preflight",
                "Sparse index metadata is invalid.",
            ) from error
        if index.index_name != self._index_name or (
            index.algorithm,
            index.tokenizer,
            index.index_version,
            index.language_config,
        ) != ("BM25", "unicode-nfc-lower-v1", "v1", "simple"):
            raise _failure(
                ErrorCategory.CONFIGURATION_ERROR,
                "INDEX_INCOMPATIBLE",
                "index_preflight",
                "Sparse index configuration is incompatible with this tokenizer.",
            )
        if index.status != "READY":
            raise _failure(
                ErrorCategory.INDEX_UNAVAILABLE, "INDEX_NOT_READY", "index_preflight", "Sparse index is not READY."
            )
        if index.document_count == 0 or index.average_document_length <= 0:
            raise _failure(
                ErrorCategory.INDEX_UNAVAILABLE,
                "INDEX_EMPTY",
                "index_preflight",
                "Sparse index has no searchable corpus statistics.",
            )
        return index

    async def _check_index_unchanged(self, before: _SparseIndex) -> None:
        """Read again without refreshing or writing index state."""
        row = await self._indexes.get_index(self._index_name)
        try:
            after = _SparseIndex.model_validate(row)
        except ValidationError as error:
            raise _failure(
                ErrorCategory.INDEX_UNAVAILABLE,
                "INDEX_CHANGED_DURING_SEARCH",
                "index_postflight",
                "Sparse index disappeared or changed during retrieval.",
            ) from error
        if after != before:
            raise _failure(
                ErrorCategory.INDEX_UNAVAILABLE,
                "INDEX_CHANGED_DURING_SEARCH",
                "index_postflight",
                "Sparse index changed during retrieval; retry the complete request.",
            )

    async def _read_dense_index(self) -> _DenseIndex:
        row = await self._dense_indexes.get_index(self._dense_index_name)
        if row is None:
            raise _failure(
                ErrorCategory.INDEX_UNAVAILABLE,
                "INDEX_NOT_FOUND",
                "index_preflight",
                "Configured dense index does not exist.",
            )
        try:
            index = _DenseIndex.model_validate(row)
            if index.updated_at.utcoffset() is None:
                raise ValueError("missing index timezone")
        except (ValidationError, ValueError) as error:
            raise _failure(
                ErrorCategory.CONFIGURATION_ERROR,
                "INVALID_INDEX_METADATA",
                "index_preflight",
                "Dense index metadata is invalid.",
            ) from error
        if (
            (
                index.index_name,
                index.index_version,
                index.provider,
                index.model_name,
                index.embedding_dimension,
                index.distance_metric,
            )
            != (self._dense_index_name, "v1", "sentence-transformers", "intfloat/multilingual-e5-small", 384, "cosine")
            or index.metadata.get("normalized") is not True
            or (index.metadata.get("passage_prefix"), index.metadata.get("query_prefix")) != ("passage: ", "query: ")
        ):
            raise _failure(
                ErrorCategory.CONFIGURATION_ERROR,
                "INDEX_INCOMPATIBLE",
                "index_preflight",
                "Dense index does not match the E5 query-encoding contract.",
            )
        if index.status != "READY":
            raise _failure(
                ErrorCategory.INDEX_UNAVAILABLE, "INDEX_NOT_READY", "index_preflight", "Dense index is not READY."
            )
        return index

    async def _check_dense_index_unchanged(self, before: _DenseIndex) -> None:
        row = await self._dense_indexes.get_index(self._dense_index_name)
        try:
            after = _DenseIndex.model_validate(row)
        except ValidationError as error:
            raise _failure(
                ErrorCategory.INDEX_UNAVAILABLE,
                "INDEX_CHANGED_DURING_SEARCH",
                "index_postflight",
                "Dense index disappeared or changed during retrieval.",
            ) from error
        if before != after:
            raise _failure(
                ErrorCategory.INDEX_UNAVAILABLE,
                "INDEX_CHANGED_DURING_SEARCH",
                "index_postflight",
                "Dense index changed during retrieval; retry the complete request.",
            )

    async def _map_dense_evidence(
        self,
        raw_hits: tuple[RetrievedEvidence, ...],
        request: RetrievalRequest,
        index: _DenseIndex,
    ) -> tuple[UnifiedEvidence, ...]:
        """Preserve RPC ranking and verify content against stored chunks before returning it.

        The existing vector RPC omits content_sha256. One batch chunk read permits
        MATCHED_STORED semantics without modifying SQL or trusting a payload-only digest.
        """
        try:
            hits = _DENSE_HITS.validate_python(raw_hits)
        except ValidationError as error:
            raise _failure(
                ErrorCategory.INCONSISTENT_EVIDENCE,
                "INVALID_DENSE_HITS",
                "hydration",
                "Vector search returned malformed evidence.",
            ) from error
        if not hits:
            return ()
        ids = tuple(hit.retrieval_chunk_id for hit in hits)
        if (
            len(set(ids)) != len(ids)
            or len(hits) > request.top_k
            or any(a.similarity < b.similarity for a, b in zip(hits, hits[1:]))
            or any(abs(hit.similarity) > 1.000001 or hit.dense_index_id != index.id for hit in hits)
        ):
            raise _failure(
                ErrorCategory.INCONSISTENT_EVIDENCE,
                "INVALID_DENSE_RANKING",
                "hydration",
                "Dense ranking, index identity or similarity is invalid.",
            )
        rows = await self._chunks.get_by_ids(ids)
        try:
            chunks = tuple(_ChunkRow.model_validate(row) for row in rows)
        except ValidationError as error:
            raise _failure(
                ErrorCategory.INCONSISTENT_EVIDENCE, "INVALID_CHUNK", "hydration", "Stored chunk data is invalid."
            ) from error
        by_id = {chunk.id: chunk for chunk in chunks}
        if len(by_id) != len(chunks) or set(by_id) != set(ids):
            raise _failure(
                ErrorCategory.INCONSISTENT_EVIDENCE,
                "CHUNK_IDENTITY_MISMATCH",
                "hydration",
                "Dense integrity verification found missing or changed chunks.",
            )
        fields = {
            "source_document_id",
            "document_structure_id",
            "chunk_key",
            "content",
            "node_id",
            "block_id",
            "chunk_type",
            "start_offset",
            "end_offset",
        }
        result = []
        for rank, hit in enumerate(hits, 1):
            chunk = by_id[hit.retrieval_chunk_id]
            if (
                chunk.model_dump(include=fields) != hit.model_dump(include=fields)
                or chunk.metadata != hit.chunk_metadata
            ):
                raise _failure(
                    ErrorCategory.INCONSISTENT_EVIDENCE,
                    "DENSE_CHUNK_CHANGED",
                    "hydration",
                    "Vector evidence differs from the stored chunk observed during verification.",
                )
            digest = hashlib.sha256(hit.content.encode("utf-8")).hexdigest()
            if digest != chunk.content_sha256:
                raise _failure(
                    ErrorCategory.INCONSISTENT_EVIDENCE,
                    "CONTENT_HASH_MISMATCH",
                    "hydration",
                    "Dense evidence content does not match its stored SHA-256.",
                )
            try:
                source = _SourceRow.model_validate(
                    {**hit.model_dump(), "id": hit.source_document_id, "raw_metadata": hit.source_metadata}
                )
                self._check_eligibility(source, request)
                result.append(
                    UnifiedEvidence(
                        **hit.model_dump(exclude={"similarity", "dense_index_id"}),
                        content_sha256=digest,
                        hash_check="MATCHED_STORED",
                        rank=rank,
                        raw_score=hit.similarity,
                        score_kind="COSINE_SIMILARITY",
                        retrieval_method=RetrievalMode.DENSE,
                    )
                )
            except ValidationError as error:
                raise _failure(
                    ErrorCategory.INCONSISTENT_EVIDENCE,
                    "INVALID_EVIDENCE",
                    "hydration",
                    "Dense evidence violates its source or content contract.",
                ) from error
        return tuple(result)
