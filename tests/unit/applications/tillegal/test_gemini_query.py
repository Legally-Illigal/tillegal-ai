"""Gemini adapter and real Query/Search interfaces with mocked provider responses."""

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
import yaml
from pydantic import SecretStr

from scripts.verify_gemini_query import fixture_retrieval, main
from src.applications.tillegal.agents.query.gemini import DEFAULT_MODEL_CONFIG, create_gemini_query_agent
from src.applications.tillegal.agents.query.schemas import SemanticAnalysis
from src.applications.tillegal.agents.query.semantic import QueryAnalysisError
from src.core.config import SupabaseSettings
from src.framework.llm.providers.gemini_adapter import GeminiProviderError, GeminiStructuredCompletion
from src.query_search_bootstrap import QuerySearch, create_query_search
from tests.unit.applications.tillegal.test_query_search import options
from tests.unit.applications.tillegal.test_query_search_semantic import QUESTION, analysis

TARGET = "src.framework.llm.providers.gemini_adapter._acompletion"
FAKE_KEY = "fixture-only-not-a-real-api-key"


def reply(content=None, finish="stop"):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                finish_reason=finish,
                message=SimpleNamespace(content=json.dumps(analysis()) if content is None else content),
            )
        ]
    )


def call(adapter):
    return adapter(
        model="gemini-3.5-flash-lite", system="system", user="user", schema=SemanticAnalysis.model_json_schema()
    )


def test_adapter_maps_key_and_schema_without_global_environment_changes(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "unrelated-existing-value")
    adapter = GeminiStructuredCompletion(SecretStr(FAKE_KEY))
    with patch(TARGET, AsyncMock(return_value=reply())) as completion:
        result = asyncio.run(call(adapter))
    assert json.loads(result) == analysis()
    kwargs = completion.call_args.kwargs
    assert kwargs["model"] == "gemini/gemini-3.5-flash-lite" and kwargs["api_key"] == FAKE_KEY
    assert kwargs["response_format"]["response_schema"] == SemanticAnalysis.model_json_schema()
    assert kwargs["messages"] == [{"role": "system", "content": "system"}, {"role": "user", "content": "user"}]
    assert kwargs["num_retries"] == 0 and kwargs["no-log"] is True and kwargs["caching"] is False
    assert FAKE_KEY not in repr(adapter)
    import os

    assert os.environ["GEMINI_API_KEY"] == "unrelated-existing-value"


@pytest.mark.parametrize(
    "status,code",
    [
        (400, "GEMINI_INVALID_REQUEST"),
        (401, "GEMINI_AUTHENTICATION_FAILED"),
        (403, "GEMINI_PERMISSION_DENIED"),
        (404, "GEMINI_MODEL_NOT_FOUND"),
        (429, "GEMINI_RATE_LIMITED"),
        (503, "GEMINI_SERVICE_UNAVAILABLE"),
        (None, "GEMINI_REQUEST_FAILED"),
    ],
)
def test_provider_errors_are_classified_without_upstream_text(status, code):
    error = RuntimeError("private header " + FAKE_KEY)
    error.status_code = status
    with patch(TARGET, AsyncMock(side_effect=error)):
        with pytest.raises(GeminiProviderError) as captured:
            asyncio.run(call(GeminiStructuredCompletion(SecretStr(FAKE_KEY))))
    assert captured.value.code == code and captured.value.http_status == status
    assert FAKE_KEY not in str(captured.value) and "private" not in str(captured.value)


@pytest.mark.parametrize(
    "response",
    [
        SimpleNamespace(choices=[]),
        reply("[]"),
        reply("not json"),
        reply("null"),
        reply(" "),
        reply("{}", "length"),
        reply("{}", "content_filter"),
        reply("x" * 32001),
        SimpleNamespace(),
    ],
)
def test_invalid_truncated_or_blocked_response_fails(response):
    with patch(TARGET, AsyncMock(return_value=response)):
        with pytest.raises(GeminiProviderError, match="^GEMINI_INVALID_RESPONSE$"):
            asyncio.run(call(GeminiStructuredCompletion(SecretStr(FAKE_KEY))))


def test_adapter_timeout_and_cancellation():
    async def wait(**kwargs):
        await asyncio.Event().wait()

    with patch(TARGET, wait):
        with pytest.raises(TimeoutError, match="^GEMINI_TIMEOUT$"):
            asyncio.run(call(GeminiStructuredCompletion(SecretStr(FAKE_KEY), timeout_seconds=0.01)))
    with patch(TARGET, AsyncMock(side_effect=asyncio.CancelledError)):
        with pytest.raises(asyncio.CancelledError):
            asyncio.run(call(GeminiStructuredCompletion(SecretStr(FAKE_KEY))))


def test_gemini_sdk_timeout_translates_to_existing_query_timeout():
    sdk_timeout_type = type("Timeout", (Exception,), {})

    agent = create_gemini_query_agent(environ={"GOOGLE_API_KEY": FAKE_KEY})
    with patch(TARGET, AsyncMock(side_effect=sdk_timeout_type("private diagnostic"))):
        with pytest.raises(QueryAnalysisError, match="^QUERY_ANALYSIS_TIMEOUT$"):
            asyncio.run(agent.understand(QUESTION))


@pytest.mark.parametrize(
    "env",
    [
        {},
        {"GOOGLE_API_KEY": " "},
        {"GOOGLE_API_KEY": FAKE_KEY, "GEMINI_MODEL": "openai/model"},
        {"GOOGLE_API_KEY": FAKE_KEY, "QUERY_LLM_TIMEOUT_SECONDS": "0"},
        {"GOOGLE_API_KEY": FAKE_KEY, "QUERY_LLM_TIMEOUT_SECONDS": "nan"},
    ],
)
def test_invalid_config_is_safe_and_never_calls_api(env):
    with patch(TARGET, AsyncMock()) as completion:
        with pytest.raises(ValueError, match="^GEMINI_QUERY_CONFIGURATION_INVALID$"):
            create_gemini_query_agent(environ=env)
    completion.assert_not_awaited()


def test_model_and_timeout_are_configurable_without_mutating_mapping():
    env = {"GOOGLE_API_KEY": FAKE_KEY, "GEMINI_MODEL": "gemini-3.8-flash", "QUERY_LLM_TIMEOUT_SECONDS": "19"}
    before = dict(env)
    agent = create_gemini_query_agent(environ=env)
    assert agent.model == "gemini-3.8-flash" and agent.timeout_seconds == 19
    assert env == before and FAKE_KEY not in repr(agent)


@pytest.mark.parametrize("change", ["disabled", "wrong_provider", "wrong_key_env", "invalid_root"])
def test_invalid_provider_profile_rejected(tmp_path, change):
    data = yaml.safe_load(DEFAULT_MODEL_CONFIG.read_text(encoding="utf-8"))
    if change == "disabled":
        data["providers"]["gemini"]["enabled"] = False
    elif change == "wrong_provider":
        data["profiles"]["query_semantic"]["provider"] = "openai"
    elif change == "wrong_key_env":
        data["providers"]["gemini"]["api_key_env"] = "OTHER_KEY"
    else:
        data = []
    path = tmp_path / "models.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(ValueError, match="^GEMINI_QUERY_CONFIGURATION_INVALID$"):
        create_gemini_query_agent(environ={"GOOGLE_API_KEY": FAKE_KEY}, config_path=path)


def test_semantic_factory_runs_adapter_query_search_and_real_retrieval(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", FAKE_KEY)
    with (
        patch("src.query_search_bootstrap.create_retrieval_service", return_value=fixture_retrieval()),
        patch(TARGET, AsyncMock(return_value=reply())) as completion,
    ):
        pipeline = create_query_search(SupabaseSettings(), options(), semantic_mode="gemini")
        result = asyncio.run(pipeline.search(QUESTION))
    assert result["plan"]["analysis_method"] == "llm" and result["plan"]["analysis_model"] == pipeline.query_agent.model
    assert result["plan"]["facts"] == analysis()["facts"] and len(result["plan"]["issues"]) == 2
    assert result["status"] == "COMPLETED" and result["completeness"] == "COMPLETE"
    assert result["executed_searches"] == 2 and all(response.status == "NO_MATCH" for response in result["responses"])
    completion.assert_awaited_once()


@pytest.mark.parametrize(
    "raw", ["{}", json.dumps(analysis(issues=[{"issue": "Điều 999", "search_query": "Điều 999"}]))]
)
def test_schema_and_hallucination_guards_preserved(raw):
    agent = create_gemini_query_agent(environ={"GOOGLE_API_KEY": FAKE_KEY})
    retrieval = AsyncMock()
    with patch(TARGET, AsyncMock(return_value=reply(raw))):
        with pytest.raises(QueryAnalysisError, match="^QUERY_ANALYSIS_INVALID_RESPONSE$"):
            asyncio.run(QuerySearch(retrieval, options(), agent).search(QUESTION))
    retrieval.search.assert_not_awaited()


def test_provider_failure_never_falls_back_or_calls_search():
    agent = create_gemini_query_agent(environ={"GOOGLE_API_KEY": FAKE_KEY})
    retrieval = AsyncMock()
    with patch(TARGET, AsyncMock(side_effect=RuntimeError(FAKE_KEY))):
        with pytest.raises(QueryAnalysisError, match="^QUERY_ANALYSIS_PROVIDER_ERROR$"):
            asyncio.run(QuerySearch(retrieval, options(), agent).search(QUESTION))
    retrieval.search.assert_not_awaited()


def test_deterministic_factory_needs_no_google_key(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with (
        patch("src.query_search_bootstrap.create_retrieval_service", return_value=fixture_retrieval()),
        patch(TARGET, AsyncMock()) as completion,
    ):
        pipeline = create_query_search(SupabaseSettings(), options(), semantic_mode="deterministic")
        result = asyncio.run(pipeline.search(QUESTION))
    assert result["plan"]["analysis_method"] == "deterministic" and result["status"] == "COMPLETED"
    completion.assert_not_awaited()


def test_factory_rejects_ambiguous_or_unknown_mode_before_retrieval():
    with patch("src.query_search_bootstrap.create_retrieval_service") as factory:
        with pytest.raises(ValueError, match="QUERY_AGENT_CONFIGURATION_CONFLICT"):
            create_query_search(SupabaseSettings(), options(), query_agent=object(), semantic_mode="gemini")
        with pytest.raises(ValueError, match="QUERY_SEMANTIC_MODE_INVALID"):
            create_query_search(SupabaseSettings(), options(), semantic_mode="unknown")
    factory.assert_not_called()


def test_cli_mocked_smoke_and_legal_question(monkeypatch, capsys):
    monkeypatch.setenv("GOOGLE_API_KEY", FAKE_KEY)
    with patch(TARGET, AsyncMock(return_value=reply('{"ok": true}'))):
        assert main(["--mode", "gemini", "--smoke-test"]) == 0
    smoke = json.loads(capsys.readouterr().out)
    assert smoke["status"] == "PASS" and smoke["smoke"] == {"ok": True}
    with patch(TARGET, AsyncMock(return_value=reply())):
        assert main(["--mode", "gemini", "--search-backend", "fixture"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "PASS" and report["search"]["executed_searches"] == 2
    assert FAKE_KEY not in json.dumps(report)


def test_cli_failure_is_safe_and_exits_nonzero(monkeypatch, capsys):
    monkeypatch.setenv("GOOGLE_API_KEY", FAKE_KEY)
    error = RuntimeError("Authorization " + FAKE_KEY)
    error.status_code = 429
    with patch(TARGET, AsyncMock(side_effect=error)):
        assert main(["--mode", "gemini", "--search-backend", "fixture"]) == 1
    output = capsys.readouterr().out
    report = json.loads(output)
    assert report["error"]["provider_code"] == "GEMINI_RATE_LIMITED" and report["error"]["http_status"] == 429
    assert FAKE_KEY not in output and "Authorization" not in output
