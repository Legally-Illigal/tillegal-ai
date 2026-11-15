import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.search_legal_chunks import main
from src.core.config import SupabaseSettings
from tests.unit.applications.tillegal.retrieval.test_contracts import response
from tests.unit.applications.tillegal.retrieval.test_service import chunk_row, index_row, source_row

ARGS = ["--query", "Thuế", "--as-of-date", "2026-11-10", "--allowed-policy", "EXPERIMENTAL_ONLY"]


class FakeService:
    def __init__(self, result=None):
        self.result = response() if result is None else result
        self.requests = []

    async def search(self, request):
        self.requests.append(request)
        return self.result


def forbidden_factory():
    raise AssertionError("Dependencies must not be constructed")


@pytest.mark.parametrize(
    "args",
    [
        [],
        ["--unknown", "private"],
        ARGS + ["--top-k", "0"],
        ARGS + ["--top-k", "secret"],
        ARGS + ["--as-of-date", "bad"],
        ARGS + ["--query", " "],
        ARGS + ["--mode", "unsupported"],
    ],
)
def test_invalid_arguments_before_dependencies(args, capsys):
    assert main(args, service_factory=forbidden_factory) == 2
    result = json.loads(capsys.readouterr().out)
    assert result["error"]["category"] == "INVALID_REQUEST"
    assert "secret" not in json.dumps(result)


def test_cli_fake_service_json_and_request(capsys):
    fake = FakeService()
    assert main(ARGS, service_factory=lambda: fake) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "NO_MATCH"
    assert result["consistency"] == "BEST_EFFORT"
    assert fake.requests[0].query == "Thuế"


def test_dense_without_configuration(capsys):
    assert main(ARGS + ["--mode", "dense"], service_factory=forbidden_factory) == 4
    assert json.loads(capsys.readouterr().out)["error"]["code"] == "MODE_NOT_CONFIGURED"


def test_configuration_error_never_echoes_exception(capsys):
    def fail():
        raise ValueError("private credential and connection URL")

    assert main(ARGS, service_factory=fail) == 4
    output = capsys.readouterr().out
    assert "private" not in output and "credential" not in output


def test_help_does_not_construct_dependencies(capsys):
    assert main(["--help"], service_factory=forbidden_factory) == 0
    assert "--as-of-date" in capsys.readouterr().out


def test_bootstrap_real_read_adapters_fake_rpc_without_model_or_worker(monkeypatch, capsys):
    import src.retrieval_bootstrap as bootstrap

    calls = []
    options = []

    class FakeClient:
        def rpc(self, name, params):
            calls.append((name, params))
            data = {
                "get_sparse_index": index_row(),
                "search_sparse_legal_chunks": [{"retrieval_chunk_id": chunk_row()["id"], "score": 1.5}],
                "get_retrieval_chunks": [chunk_row()],
                "get_source_document": source_row(),
            }
            assert name in data, "Unexpected or write RPC"
            return SimpleNamespace(execute=lambda: SimpleNamespace(data=data[name]))

    def create(url, key, **kwargs):
        options.append(kwargs["options"])
        return FakeClient()

    monkeypatch.setattr(bootstrap, "create_client", create)
    for module in ("sentence_transformers", "torch", "transformers", "src.main", "src.bootstrap", "src.workers.tasks"):
        monkeypatch.setitem(sys.modules, module, None)
    settings = SupabaseSettings(url="https://example.supabase.co", service_role_key="fake-key")
    svc = bootstrap.create_retrieval_service(settings)
    assert main(ARGS, service_factory=lambda: svc) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "OK"
    assert result["evidence"][0]["raw_score"] == 1.5
    assert [name for name, _ in calls] == [
        "get_sparse_index",
        "search_sparse_legal_chunks",
        "get_retrieval_chunks",
        "get_source_document",
        "get_sparse_index",
    ]
    assert options[0].postgrest_client_timeout == 10
    assert options[0].persist_session is options[0].auto_refresh_token is False


def test_default_configuration_does_not_read_dotenv(monkeypatch, capsys):
    import src.core.config as config
    import src.retrieval_bootstrap as bootstrap

    def forbidden(*args, **kwargs):
        raise AssertionError(".env must not be read")

    monkeypatch.setattr(config, "load_dotenv", forbidden)
    monkeypatch.setattr("scripts.search_legal_chunks.os.environ", {})
    monkeypatch.setattr(bootstrap, "create_retrieval_service", lambda settings: FakeService())
    assert main(ARGS) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "NO_MATCH"


@pytest.mark.parametrize(
    ("category", "exit_code"),
    [
        ("INDEX_UNAVAILABLE", 3),
        ("DATABASE_FAILURE", 5),
        ("INCONSISTENT_EVIDENCE", 5),
        ("TIMEOUT", 6),
    ],
)
def test_service_failure_exit_codes(category, exit_code, capsys):
    from src.applications.tillegal.retrieval.errors import RetrievalErrorDetail

    result = response(
        status="FAILED",
        error=RetrievalErrorDetail(category=category, code="TEST_FAILURE", stage="search", message="Safe failure"),
    )
    assert main(ARGS, service_factory=lambda: FakeService(result)) == exit_code
    assert json.loads(capsys.readouterr().out)["status"] == "FAILED"


def test_cold_bootstrap_import_never_imports_models_or_starts_network():
    script = """
import builtins
import socket
original = builtins.__import__
def guarded(name, globals=None, locals=None, fromlist=(), level=0):
    forbidden = ("torch", "transformers", "sentence_transformers", "src.workers")
    if level == 0 and (name in ("src.main", "src.bootstrap") or name.startswith(forbidden)):
        raise AssertionError("Forbidden model/worker import")
    return original(name, globals, locals, fromlist, level)
def offline(*args, **kwargs):
    raise AssertionError("Unexpected network access")
builtins.__import__ = guarded
socket.socket.connect = offline
socket.socket.connect_ex = offline
import src.retrieval_bootstrap
print("COLD_IMPORT_OK")
"""
    root = Path(__file__).resolve().parents[6]
    result = subprocess.run([sys.executable, "-c", script], cwd=root, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "COLD_IMPORT_OK"


def test_dense_cli_bootstrap_existing_vector_adapter_fake_rpc(monkeypatch, tmp_path, capsys):
    import src.retrieval_bootstrap as bootstrap
    from tests.unit.applications.tillegal.retrieval.test_dense_service import FakeEncoder, dense_hit, dense_index

    calls = []

    class FakeClient:
        def rpc(self, name, params):
            calls.append((name, params))
            data = {
                "get_dense_index": dense_index(),
                "search_legal_chunks": [dense_hit().model_dump(mode="json")],
                "get_retrieval_chunks": [chunk_row()],
            }
            assert name in data, "Unexpected RPC or write"
            return SimpleNamespace(execute=lambda: SimpleNamespace(data=data[name]))

    monkeypatch.setattr(bootstrap, "create_client", lambda *a, **kw: FakeClient())
    monkeypatch.setattr("src.integrations.embeddings.e5_query_encoder.E5QueryEncoder", lambda path: FakeEncoder())
    settings = SupabaseSettings(url="https://example.supabase.co", service_role_key="fake-key")
    svc = bootstrap.create_retrieval_service(settings, dense_model_path=tmp_path)
    assert main(ARGS + ["--mode", "dense", "--dense-model-path", str(tmp_path)], service_factory=lambda: svc) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["mode"] == "dense"
    assert output["evidence"][0]["score_kind"] == "COSINE_SIMILARITY"
    assert output["evidence"][0]["hash_check"] == "MATCHED_STORED"
    assert [name for name, _ in calls] == [
        "get_dense_index",
        "search_legal_chunks",
        "get_retrieval_chunks",
        "get_dense_index",
    ]
    assert calls[1][1]["p_top_k"] == 10


def test_bm25_cli_ignores_dense_path_and_does_not_enable_encoder(monkeypatch, tmp_path, capsys):
    import scripts.search_legal_chunks as cli

    paths = []

    def configured(*, dense_model_path=None):
        paths.append(dense_model_path)
        return FakeService()

    monkeypatch.setattr(cli, "_configured_service", configured)
    assert main(ARGS + ["--dense-model-path", str(tmp_path)]) == 0
    assert paths == [None]
    assert json.loads(capsys.readouterr().out)["status"] == "NO_MATCH"


@pytest.mark.parametrize("options", [["--rrf-k", "0"], ["--bm25-candidates", "51"], ["--dense-candidates", "0"]])
def test_invalid_hybrid_config_before_dependencies(options, capsys):
    assert main(ARGS + options, service_factory=forbidden_factory) == 2
    assert json.loads(capsys.readouterr().out)["error"]["category"] == "INVALID_REQUEST"


def test_hybrid_requires_local_model_path(capsys):
    assert main(ARGS + ["--mode", "hybrid"], service_factory=forbidden_factory) == 4
    assert json.loads(capsys.readouterr().out)["error"]["code"] == "MODE_NOT_CONFIGURED"


def test_hybrid_cli_configuration_and_existing_read_adapters(monkeypatch, tmp_path, capsys):
    import scripts.search_legal_chunks as cli
    import src.retrieval_bootstrap as bootstrap
    from tests.unit.applications.tillegal.retrieval.test_dense_service import FakeEncoder, dense_hit, dense_index

    calls = []

    class FakeClient:
        def rpc(self, name, params):
            calls.append((name, params))
            data = {
                "get_sparse_index": index_row(),
                "get_dense_index": dense_index(),
                "search_sparse_legal_chunks": [{"retrieval_chunk_id": chunk_row()["id"], "score": 7.2}],
                "search_legal_chunks": [dense_hit().model_dump(mode="json")],
                "get_retrieval_chunks": [chunk_row()],
                "get_source_document": source_row(
                    effective_from=None, source_id="vbpl", source_record_id="demo", language="vi"
                ),
            }
            assert name in data, "Unexpected write or Storage call"
            return SimpleNamespace(execute=lambda: SimpleNamespace(data=data[name]))

    monkeypatch.setattr(bootstrap, "create_client", lambda *a, **kw: FakeClient())
    monkeypatch.setattr("src.integrations.embeddings.e5_query_encoder.E5QueryEncoder", lambda path: FakeEncoder())
    settings = SupabaseSettings(url="https://example.supabase.co", service_role_key="fake-key")

    def configure(*, dense_model_path=None, hybrid_config=None):
        return bootstrap.create_retrieval_service(
            settings, dense_model_path=dense_model_path, hybrid_config=hybrid_config
        )

    monkeypatch.setattr(cli, "_configured_service", configure)
    assert (
        main(
            ARGS
            + [
                "--mode",
                "hybrid",
                "--dense-model-path",
                str(tmp_path),
                "--rrf-k",
                "10",
                "--bm25-candidates",
                "3",
                "--dense-candidates",
                "4",
            ]
        )
        == 0
    )
    output = json.loads(capsys.readouterr().out)
    assert output["mode"] == "hybrid"
    assert output["fusion"]["config"] == {"rrf_k": 10, "bm25_candidates": 3, "dense_candidates": 4}
    assert output["evidence"][0]["score_kind"] == "RRF"
    assert output["evidence"][0]["raw_score"] == pytest.approx(2 / 11)
    assert [name for name, _ in calls] == [
        "get_sparse_index",
        "search_sparse_legal_chunks",
        "get_retrieval_chunks",
        "get_source_document",
        "get_sparse_index",
        "get_dense_index",
        "search_legal_chunks",
        "get_retrieval_chunks",
        "get_dense_index",
        "get_sparse_index",
        "get_dense_index",
    ]
    assert next(params for name, params in calls if name == "search_sparse_legal_chunks")["p_top_k"] == 3
    assert next(params for name, params in calls if name == "search_legal_chunks")["p_top_k"] == 4
