"""CLI checks use the offline graph; never read local secrets or call live services."""

from unittest.mock import patch

import pytest

from examples.orchestrator.offline import main as offline
from scripts.run_orchestrator import main


@pytest.mark.parametrize("extra", [[], ["--allow-live", "--timeout-seconds", "0"], ["--allow-live", "--question", " "]])
def test_invalid_arguments_never_construct_services(extra):
    with patch("scripts.run_orchestrator.build_workflow") as build:
        with pytest.raises(SystemExit) as exc:
            main(["--as-of-date", "2026-11-28", *extra])
        assert exc.value.code == 2
        build.assert_not_called()


def test_cli_outputs_json_through_workflow(tmp_path, capsys):
    class OfflineWorkflow:
        async def execute(self, question, context, **kwargs):
            assert question == "fixture" and context.request_id.startswith("online-")
            return await offline()

    with patch("scripts.run_orchestrator.build_workflow", return_value=OfflineWorkflow()):
        code = main(
            ["--allow-live", "--as-of-date", "2026-11-28", "--question", "fixture", "--output-root", str(tmp_path)]
        )
    assert code == 0
    paths = list(tmp_path.glob("online-*/output.json"))
    assert len(paths) == 1 and '"NOT_RUN"' in paths[0].read_text(encoding="utf-8")
    assert "query -> search -> judge -> summary -> finalize" in capsys.readouterr().out


def test_provider_error_does_not_expose_secret(capsys):
    with patch("scripts.run_orchestrator.build_workflow", side_effect=ValueError("PRIVATE-SECRET")):
        code = main(["--allow-live", "--as-of-date", "2026-11-28", "--question", "fixture"])
    captured = capsys.readouterr()
    assert code == 1 and "QA_RUN_FAILED" in captured.err
    assert "PRIVATE-SECRET" not in captured.err + captured.out
