from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from src.applications.tillegal.ingestion.legal_parser import make_chunks
from src.applications.tillegal.ingestion.service import IngestionService
from src.integrations.embedding.adapter import LocalEmbeddingAdapter

from .test_module_flow import FixtureEncoder, MemoryStore, document


def test_entrypoint_loads_shared_encoder_once(monkeypatch):
    import importlib
    import sys

    client = object()
    monkeypatch.setattr("src.bootstrap.create_supabase_client", lambda settings: client)
    encoder = Mock(return_value=FixtureEncoder())
    monkeypatch.setattr("src.integrations.embedding.local_encoder.LocalEncoder", encoder)
    for name, value in {
        "TILLEGAL_RAG_ENABLED": "true",
        "TILLEGAL_E5_PATH": "fixture-model",
        "TILLEGAL_E5_REVISION": "fixture-revision",
        "SUPABASE_URL": "https://fixture.invalid",
        "SUPABASE_SERVICE_ROLE_KEY": "fixture",
        "SUPABASE_AUTO_MIGRATE": "false",
        "LANGGRAPH_CHECKPOINTER_ENABLED": "false",
    }.items():
        monkeypatch.setenv(name, value)
    monkeypatch.delitem(sys.modules, "src.main", raising=False)
    app = importlib.import_module("src.main").app
    with TestClient(app) as http:
        assert http.get("/").is_success
        modules = app.state.tillegal_modules
        assert modules.ingestion.embedder is modules.retrieval.embedder
        encoder.assert_called_once_with("fixture-model", "fixture-revision")
    assert app.state.tillegal_modules is None
    encoder.side_effect = RuntimeError("snapshot unavailable")
    with pytest.raises(RuntimeError, match="snapshot unavailable"), TestClient(app):
        pass


def test_service_calls_injected_chunker():
    import asyncio

    chunker = Mock(wraps=make_chunks)
    service = IngestionService(MemoryStore(), LocalEmbeddingAdapter(FixtureEncoder()), chunker=chunker)
    doc = document()
    assert asyncio.run(service.ingest(doc)) == doc.document_version_id
    chunker.assert_called_once()
    source, blocks, nodes, limit = chunker.call_args.args
    assert source == doc and blocks and nodes and limit == 1800
