"""Lazy, local-only E5 query encoding; no hosted API or model download."""

import asyncio
import importlib
from pathlib import Path
from threading import Lock
from typing import Any

from src.applications.tillegal.retrieval.errors import ErrorCategory, RetrievalErrorDetail, RetrievalServiceError
from src.applications.tillegal.retrieval.vector_validation import validate_query_vector

MODEL_NAME = "intfloat/multilingual-e5-small"
QUERY_PREFIX = "query: "


def _encoding_error(code: str, message: str, *, invalid_input: bool = False) -> RetrievalServiceError:
    return RetrievalServiceError(
        RetrievalErrorDetail(
            category=ErrorCategory.INVALID_REQUEST if invalid_input else ErrorCategory.MODEL_UNAVAILABLE,
            code=code,
            stage="encoding",
            message=message,
        )
    )


class E5QueryEncoder:
    """Read an explicitly provisioned local checkpoint and run single-query CPU inference.

    A threading lock stays held if the awaiting coroutine is cancelled, preventing
    overlapping model work. Another request fails MODEL_BUSY instead of starting a
    second encode while a timed-out worker is still running.
    """

    def __init__(self, model_path: Path) -> None:
        self._path = model_path
        self._model: Any | None = None
        self._lock = Lock()

    async def encode_query(self, query: str) -> tuple[float, ...]:
        """Offload loading/tokenization/inference; preserve query case and accents."""
        if not query.strip():
            raise _encoding_error("EMPTY_QUERY", "Query must not be blank.", invalid_input=True)
        return await asyncio.to_thread(self._encode, query.strip())

    def _get_model(self) -> Any:
        if self._model is None:
            if not self._path.is_dir():
                raise _encoding_error("MODEL_NOT_PROVISIONED", "A local E5 checkpoint directory is required.")
            try:
                module = importlib.import_module("sentence_transformers")
                model = module.SentenceTransformer(
                    str(self._path),
                    device="cpu",
                    local_files_only=True,
                    trust_remote_code=False,
                )
                dimension_reader = getattr(model, "get_embedding_dimension", None)
                dimension = dimension_reader() if dimension_reader else model.get_sentence_embedding_dimension()
                if dimension != 384:
                    raise ValueError("incompatible model dimension")
                if type(model.max_seq_length) is not int or not 1 <= model.max_seq_length <= 512:
                    raise ValueError("incompatible model token limit")
            except Exception as error:
                raise _encoding_error("MODEL_LOAD_FAILED", "Cannot load the configured local E5 checkpoint.") from error
            self._model = model
        return self._model

    def _encode(self, query: str) -> tuple[float, ...]:
        if not self._lock.acquire(blocking=False):
            raise _encoding_error("MODEL_BUSY", "The query encoder is still processing another request.")
        try:
            model = self._get_model()
            text = f"{QUERY_PREFIX}{query}"
            tokens = model.tokenizer(text, add_special_tokens=True, truncation=False)
            if len(tokens["input_ids"]) > model.max_seq_length:
                raise _encoding_error("QUERY_TOKEN_LIMIT", "Query exceeds the model token limit.", invalid_input=True)
            # Explicit empty prompt prevents a checkpoint's default prompt being
            # added on top of our E5 query prefix.
            rows = model.encode(
                [text],
                batch_size=1,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
                prompt="",
            )
            if len(rows) != 1:
                raise ValueError("invalid encoder row count")
            try:
                return validate_query_vector(tuple(float(value) for value in rows[0]))
            except (TypeError, ValueError, OverflowError) as error:
                raise _encoding_error(
                    "INVALID_EMBEDDING", "Encoder output violates the query-vector contract."
                ) from error
        except RetrievalServiceError:
            raise
        except Exception as error:
            raise _encoding_error("ENCODING_FAILED", "Local query encoding failed.") from error
        finally:
            self._lock.release()
