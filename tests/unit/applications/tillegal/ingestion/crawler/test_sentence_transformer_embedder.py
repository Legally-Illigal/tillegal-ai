import sys
from types import ModuleType

from src.applications.tillegal.ingestion.crawler.embeddings.sentence_transformer import (
    EMBEDDING_DIMENSION,
    MODEL_NAME,
    SentenceTransformerPassageEmbedder,
)


class FakeModel:
    def __init__(self) -> None:
        self.encoded: list[str] = []
        self.tokenizer = self

    def __call__(self, text: str, *, add_special_tokens: bool, truncation: bool):
        assert add_special_tokens
        assert not truncation
        return {"input_ids": text.split()}

    def encode(self, texts, **kwargs):
        self.encoded = texts
        assert kwargs["normalize_embeddings"] is True
        assert kwargs["show_progress_bar"] is False
        return [[0.01] * EMBEDDING_DIMENSION for _ in texts]


def test_embedder_uses_e5_passage_prefix_and_expected_dimension(monkeypatch) -> None:
    model = FakeModel()
    observed: dict[str, object] = {}

    class FakeSentenceTransformer:
        def __new__(cls, model_name: str, *, device: str):
            observed["model_name"] = model_name
            observed["device"] = device
            return model

    fake_module = ModuleType("sentence_transformers")
    fake_module.SentenceTransformer = FakeSentenceTransformer
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)

    embedder = SentenceTransformerPassageEmbedder()

    assert embedder.count_tokens("legal text") == 3
    vectors = embedder.embed_passages(["legal text"], batch_size=4)

    assert observed == {"model_name": MODEL_NAME, "device": "cpu"}
    assert model.encoded == ["passage: legal text"]
    assert len(vectors) == 1
    assert len(vectors[0]) == EMBEDDING_DIMENSION
