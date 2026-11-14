"""Local normalized passage embeddings for multilingual legal retrieval."""

from __future__ import annotations

import math
from threading import Lock
from typing import Any, Protocol

MODEL_NAME = "intfloat/multilingual-e5-small"
EMBEDDING_DIMENSION = 384
PASSAGE_PREFIX = "passage: "


class PassageEmbedder(Protocol):
    """Tokenizer and passage embedding operations required by the indexer."""

    def count_tokens(self, text: str) -> int: ...

    def embed_passages(self, texts: list[str], batch_size: int) -> list[tuple[float, ...]]: ...


class SentenceTransformerPassageEmbedder:
    """Lazily load E5-small and produce normalized passage vectors."""

    def __init__(self) -> None:
        self._model: Any | None = None
        self._model_lock = Lock()

    def count_tokens(self, text: str) -> int:
        model = self._get_model()
        tokenized = model.tokenizer(f"{PASSAGE_PREFIX}{text}", add_special_tokens=True, truncation=False)
        return len(tokenized["input_ids"])

    def embed_passages(self, texts: list[str], batch_size: int) -> list[tuple[float, ...]]:
        if not texts:
            return []
        model = self._get_model()
        vectors = model.encode(
            [f"{PASSAGE_PREFIX}{text}" for text in texts],
            batch_size=batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        result: list[tuple[float, ...]] = []
        for vector in vectors:
            values = tuple(float(value) for value in vector)
            if len(values) != EMBEDDING_DIMENSION:
                raise RuntimeError(f"{MODEL_NAME} returned {len(values)} dimensions; expected {EMBEDDING_DIMENSION}")
            if not all(math.isfinite(value) for value in values):
                raise RuntimeError(f"{MODEL_NAME} returned a non-finite embedding value")
            result.append(values)
        return result

    def _get_model(self):
        if self._model is None:
            with self._model_lock:
                if self._model is None:
                    from sentence_transformers import SentenceTransformer

                    self._model = SentenceTransformer(MODEL_NAME, device="cpu")
        return self._model
