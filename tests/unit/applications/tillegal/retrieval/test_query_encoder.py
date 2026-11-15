import asyncio
import math
from threading import Event
from types import SimpleNamespace

import pytest

from src.applications.tillegal.retrieval.errors import RetrievalServiceError
from src.integrations.embeddings.e5_query_encoder import E5QueryEncoder


class FakeModel:
    max_seq_length = 512

    def __init__(self):
        self.tokens = 10
        self.rows = [[1.0] + [0.0] * 383]
        self.inputs = []
        self.tokenizer = self.tokenize

    def tokenize(self, text, **options):
        assert options == {"add_special_tokens": True, "truncation": False}
        self.tokenized = text
        return {"input_ids": list(range(self.tokens))}

    def get_sentence_embedding_dimension(self):
        return 384

    def encode(self, texts, **options):
        self.inputs.append((texts, options))
        return self.rows


def encoder(monkeypatch, tmp_path, model=None):
    model = model or FakeModel()
    loads = []

    def load(path, **options):
        loads.append((path, options))
        return model

    monkeypatch.setattr(
        "src.integrations.embeddings.e5_query_encoder.importlib.import_module",
        lambda name: SimpleNamespace(SentenceTransformer=load),
    )
    return E5QueryEncoder(tmp_path), model, loads


def test_query_prefix_local_only_lazy_load_and_normalization(monkeypatch, tmp_path):
    enc, model, loads = encoder(monkeypatch, tmp_path)
    assert loads == []
    for _ in range(2):
        vector = asyncio.run(enc.encode_query("  Hợp đồng?  "))
        assert len(vector) == 384 and math.isclose(sum(v * v for v in vector), 1)
    assert len(loads) == 1
    assert loads[0][1] == {"device": "cpu", "local_files_only": True, "trust_remote_code": False}
    assert model.tokenized == "query: Hợp đồng?"
    assert model.inputs[0][0] == ["query: Hợp đồng?"]
    assert model.inputs[0][1] == {
        "batch_size": 1,
        "convert_to_numpy": True,
        "normalize_embeddings": True,
        "show_progress_bar": False,
        "prompt": "",
    }


def test_token_limit_and_empty_input(monkeypatch, tmp_path):
    enc, model, _ = encoder(monkeypatch, tmp_path)
    model.tokens = 513
    with pytest.raises(RetrievalServiceError) as exc:
        asyncio.run(enc.encode_query("query"))
    assert exc.value.detail.code == "QUERY_TOKEN_LIMIT" and model.inputs == []
    with pytest.raises(RetrievalServiceError) as exc:
        asyncio.run(enc.encode_query(" "))
    assert exc.value.detail.code == "EMPTY_QUERY"


@pytest.mark.parametrize("rows", [[], [[0.0] * 384], [[1.0] * 384], [[float("inf")] + [0.0] * 383], [[0.1] * 383]])
def test_malformed_embedding(monkeypatch, tmp_path, rows):
    enc, model, _ = encoder(monkeypatch, tmp_path)
    model.rows = rows
    with pytest.raises(RetrievalServiceError) as exc:
        asyncio.run(enc.encode_query("query"))
    assert exc.value.detail.category == "MODEL_UNAVAILABLE"


def test_load_failure_redacted(monkeypatch, tmp_path):
    def fail(name):
        raise RuntimeError("private path/token")

    monkeypatch.setattr("src.integrations.embeddings.e5_query_encoder.importlib.import_module", fail)
    with pytest.raises(RetrievalServiceError) as exc:
        asyncio.run(E5QueryEncoder(tmp_path).encode_query("query"))
    assert exc.value.detail.code == "MODEL_LOAD_FAILED"
    assert "private" not in exc.value.detail.model_dump_json()


def test_missing_model_does_not_import(monkeypatch, tmp_path):
    def forbidden(name):
        raise AssertionError("must not import")

    monkeypatch.setattr("src.integrations.embeddings.e5_query_encoder.importlib.import_module", forbidden)
    with pytest.raises(RetrievalServiceError) as exc:
        asyncio.run(E5QueryEncoder(tmp_path / "missing").encode_query("query"))
    assert exc.value.detail.code == "MODEL_NOT_PROVISIONED"


def test_busy_encoder_does_not_start_parallel_work(monkeypatch, tmp_path):
    enc, _, loads = encoder(monkeypatch, tmp_path)
    enc._lock.acquire()
    try:
        with pytest.raises(RetrievalServiceError) as exc:
            asyncio.run(enc.encode_query("query"))
        assert exc.value.detail.code == "MODEL_BUSY" and loads == []
    finally:
        enc._lock.release()


def test_new_dimension_method_and_exact_token_limit(monkeypatch, tmp_path):
    model = FakeModel()
    model.get_embedding_dimension = lambda: 384
    model.get_sentence_embedding_dimension = lambda: pytest.fail("deprecated method must not be used")
    model.tokens = 512
    enc, _, _ = encoder(monkeypatch, tmp_path, model)
    assert len(asyncio.run(enc.encode_query("query"))) == 384


@pytest.mark.parametrize(("dimension", "limit"), [(1536, 512), (384, 513), (384, 0)])
def test_incompatible_model_config(monkeypatch, tmp_path, dimension, limit):
    model = FakeModel()
    model.get_embedding_dimension = lambda: dimension
    model.max_seq_length = limit
    enc, _, _ = encoder(monkeypatch, tmp_path, model)
    with pytest.raises(RetrievalServiceError) as exc:
        asyncio.run(enc.encode_query("query"))
    assert exc.value.detail.code == "MODEL_LOAD_FAILED"


def test_cancelled_awaiter_keeps_worker_exclusive(monkeypatch, tmp_path):
    enc, model, _ = encoder(monkeypatch, tmp_path)
    entered, release, finished = Event(), Event(), Event()
    original_encode = model.encode

    def blocking_encode(*args, **kwargs):
        entered.set()
        try:
            assert release.wait(5)
            return original_encode(*args, **kwargs)
        finally:
            finished.set()

    model.encode = blocking_encode

    async def scenario():
        task = asyncio.create_task(enc.encode_query("query"))
        try:
            assert await asyncio.to_thread(entered.wait, 2)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            with pytest.raises(RetrievalServiceError) as exc:
                await enc.encode_query("another query")
            assert exc.value.detail.code == "MODEL_BUSY"
        finally:
            release.set()
            assert await asyncio.to_thread(finished.wait, 2)

    asyncio.run(scenario())
