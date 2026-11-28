"""Explicit live CLI for the production single-pass QA graph; no graph logic here."""

import argparse
import asyncio
import os
import sys
from datetime import date
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--allow-live", action="store_true", help="Allow real Gemini API calls and corpus reads")
    result.add_argument("--env-file", type=Path, default=ROOT / ".env")
    result.add_argument("--question", help="Prompt interactively when omitted")
    result.add_argument("--as-of-date", type=date.fromisoformat, required=True)
    result.add_argument("--timeout-seconds", type=float, default=240)
    result.add_argument("--output-root", type=Path, default=ROOT / "tmp/orchestrator-online")
    return result


def build_workflow(args):
    # Support both python -m scripts.run_orchestrator and direct script invocation.
    for path in (ROOT, ROOT / "scripts"):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    from dotenv import load_dotenv
    from live_gemini_judge import LiveGeminiJudge
    from live_gemini_summary import LiveGeminiSummary
    from pydantic import SecretStr

    from src.applications.tillegal.agents.search.agent import SearchOptions
    from src.core.config import load_settings
    from src.qa_bootstrap import create_single_pass_workflow
    from src.query_search_bootstrap import create_query_search

    if not args.env_file.is_file():
        raise FileNotFoundError("ENV_FILE_NOT_FOUND")
    load_dotenv(args.env_file, override=False)
    required = ["GOOGLE_API_KEY", "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"]
    missing = [name for name in required if not os.getenv(name, "").strip()]
    if missing:
        # Names only; never include settings or secret values in diagnostics.
        print("Missing configuration names: " + ", ".join(missing), file=sys.stderr)
        raise ValueError("MISSING_CONFIGURATION")
    pipeline = create_query_search(
        load_settings(environ=os.environ).supabase,
        SearchOptions(
            mode="bm25",
            top_k=3,
            as_of_date=args.as_of_date,
            allowed_usage_policies=("EXPERIMENTAL_ONLY",),
        ),
        semantic_mode="gemini",
        timeout_seconds=30,
    )
    key = SecretStr(os.environ["GOOGLE_API_KEY"])
    return create_single_pass_workflow(
        pipeline,
        judge_provider=LiveGeminiJudge(key, os.getenv("JUDGE_GEMINI_MODEL") or pipeline.query_agent.model),
        summary_provider=LiveGeminiSummary(key, os.getenv("SUMMARY_GEMINI_MODEL") or pipeline.query_agent.model),
        allow_live=True,
    )


async def execute(args, workflow):
    from src.framework.runtime.execution_context import ExecutionContext

    run_id = "online-" + uuid4().hex
    print("Running Query -> Search -> Judge -> Summary (BM25 top_k=3)...", flush=True)
    result = await workflow.execute(
        args.question,
        ExecutionContext(run_id=run_id, request_id=run_id),
        timeout_seconds=args.timeout_seconds,
    )
    folder = args.output_root / run_id
    folder.mkdir(parents=True, exist_ok=False)
    path = folder / "output.json"
    path.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")
    summary = result.summary_output
    print("Trace:", " -> ".join(result.trace))
    print("Workflow:", result.workflow_status)
    print("Judge:", result.judge_status)
    print("Summary:", summary["status"] if summary else None)
    print("Verification:", result.verification_status)
    print("Stop reason:", result.stop_reason)
    if result.clarification:
        print("Clarification:", result.clarification)
    if summary:
        print("\nDraft:\n", summary["answer_draft"] or "(abstained / no draft)")
    print("\nLimitations:")
    for item in result.limitations:
        print("-", item)
    print("Errors:", result.errors)
    print("Output:", path.resolve())
    return 1 if result.workflow_status == "ERROR" else 0


def main(argv=None):
    cli = parser()
    args = cli.parse_args(argv)
    if not args.allow_live:
        cli.error("--allow-live is required; real API calls may incur charges")
    if not 0 < args.timeout_seconds < float("inf"):
        cli.error("--timeout-seconds must be finite and positive")
    if args.question is None:
        args.question = input("Question: ").strip()
    if not args.question.strip():
        cli.error("question must not be blank")
    try:
        return asyncio.run(execute(args, build_workflow(args)))
    except TimeoutError:
        print("QA_TIMEOUT: graph wait ended; sync provider may still run until its I/O timeout.", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("QA_INTERRUPTED", file=sys.stderr)
        return 130
    except Exception as error:
        # Never render raw provider/config exceptions (may include keys or bodies).
        print(
            "QA_RUN_FAILED (" + type(error).__name__ + "). Check configuration and service availability.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
