"""Local-only CPU pair classifier. Cancellation never releases a running worker's lock."""

import asyncio
import time
from threading import Lock
from typing import Any

from src.applications.tillegal.retrieval.reranker import RerankingOperationalError
from src.applications.tillegal.retrieval.reranking_models import PairScores, RerankConfig


class LocalCrossEncoder:
    def __init__(self, config: RerankConfig) -> None:
        self._config = config
        self._model: Any = None
        self._tokenizer: Any = None
        self._lock = Lock()

    async def score_pairs(self, query: str, passages: tuple[str, ...]) -> PairScores:
        return await asyncio.to_thread(self._score, query, passages)

    def _load(self) -> None:
        path = self._config.model_path
        if path is None or not path.is_dir():
            raise RerankingOperationalError("MODEL_NOT_PROVISIONED")
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(str(path), local_files_only=True, trust_remote_code=False)
        model = AutoModelForSequenceClassification.from_pretrained(
            str(path),
            local_files_only=True,
            trust_remote_code=False,
        ).to(device="cpu", dtype=torch.float32)
        if (
            model.config.model_type != "xlm-roberta"
            or model.config.num_labels != 1
            or model.config.hidden_size != 384
            or model.config.num_hidden_layers != 12
            or tokenizer.model_max_length < self._config.max_length
        ):
            raise RerankingOperationalError("MODEL_INCOMPATIBLE")
        model.eval()
        self._tokenizer, self._model = tokenizer, model

    def _score(self, query: str, passages: tuple[str, ...]) -> PairScores:
        if not self._lock.acquire(blocking=False):
            raise RerankingOperationalError("MODEL_BUSY")
        stage = "MODEL_LOAD_FAILED"
        try:
            cold = self._model is None
            started = time.perf_counter()
            if cold:
                self._load()
            load_seconds = time.perf_counter() - started if cold else 0.0
            import torch

            stage = "TOKENIZATION_FAILED"
            tokenizer = self._tokenizer
            query_ids = tokenizer(query, add_special_tokens=False)["input_ids"]
            overhead = tokenizer.num_special_tokens_to_add(pair=True)
            if not query.strip() or len(query_ids) + overhead >= self._config.max_length:
                raise RerankingOperationalError("QUERY_TOO_LONG")
            truncated = tuple(
                len(query_ids) + overhead + len(tokenizer(p, add_special_tokens=False)["input_ids"])
                > self._config.max_length
                for p in passages
            )
            scores = []
            started = time.perf_counter()
            with torch.inference_mode():
                for start in range(0, len(passages), self._config.batch_size):
                    batch = passages[start : start + self._config.batch_size]
                    stage = "TOKENIZATION_FAILED"
                    inputs = tokenizer(
                        [query] * len(batch),
                        list(batch),
                        padding=True,
                        truncation="only_second",
                        max_length=self._config.max_length,
                        return_tensors="pt",
                    )
                    stage = "INFERENCE_FAILED"
                    logits = self._model(**inputs).logits
                    if tuple(logits.shape) != (len(batch), 1):
                        raise RerankingOperationalError("INVALID_SCORES")
                    scores.extend(float(x) for x in logits[:, 0].cpu().tolist())
            return PairScores(
                scores=tuple(scores),
                truncated=truncated,
                cold=cold,
                load_seconds=load_seconds,
                inference_seconds=time.perf_counter() - started,
            )
        except RerankingOperationalError:
            raise
        except Exception as error:
            raise RerankingOperationalError(stage) from error
        finally:
            self._lock.release()
