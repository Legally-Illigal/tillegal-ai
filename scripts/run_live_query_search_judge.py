"""Live sequential Query/Search/Judge demo (optional Summary); no fixtures, migrations or corpus writes."""

import argparse
import asyncio
import json
import os
import sys
from dataclasses import asdict
from datetime import date
from pathlib import Path
from uuid import uuid4


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--question", required=True)
    parser.add_argument("--as-of-date", type=date.fromisoformat, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--with-summary", action="store_true")
    args = parser.parse_args()
    sys.path.insert(0, str(args.repo.resolve()))
    os.chdir(args.repo)
    from dotenv import load_dotenv

    load_dotenv(args.env_file.resolve(), override=False)
    required = ["GOOGLE_API_KEY", "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"]
    missing = [key for key in required if not os.environ.get(key)]
    if missing:
        print("Missing configuration names: " + ", ".join(missing))
        return 2
    from pydantic import SecretStr, TypeAdapter

    from src.applications.tillegal.agents.judge.adapter import adapt_search
    from src.applications.tillegal.agents.judge.agent import JudgeAgent, judge_messages
    from src.applications.tillegal.agents.search.agent import SearchOptions, SearchState, search
    from src.core.config import load_settings
    from src.query_search_bootstrap import create_query_search

    options = SearchOptions(
        mode="bm25", top_k=3, as_of_date=args.as_of_date, allowed_usage_policies=("EXPERIMENTAL_ONLY",)
    )
    pipeline = create_query_search(
        load_settings(environ=os.environ).supabase, options, semantic_mode="gemini", timeout_seconds=60
    )
    args.out.mkdir(parents=True, exist_ok=False)

    def save(name, value):
        (args.out / (name + ".json")).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        print(name + " saved", flush=True)

    async def stages():
        save("01_query_input", {"question": args.question})
        plan = await pipeline.query_agent.understand(args.question)
        save("02_query_output", plan)
        save("03_search_input", {"plan": plan, "options": options.model_dump(mode="json")})
        state = await search(plan, pipeline.retrieval, options)
        save("04_search_output", TypeAdapter(SearchState).dump_python(state, mode="json", serialize_as_any=True))
        return plan, state

    try:
        plan, state = asyncio.run(stages())
        texts = list(dict.fromkeys(request.query for request in state["requests"]))
        adapted = adapt_search(
            state,
            request_id=str(uuid4()),
            options=options,
            search_rounds_completed=1,
            query_history=[str(request.request_id) for request in state["responses"]],
            query_text_history=texts,
        )
        save("05_judge_input", adapted.judge_input)
        save("05b_identity_and_native_context", asdict(adapted))

        from live_gemini_judge import LiveGeminiJudge

        save("05c_judge_messages", judge_messages(adapted.judge_input))
        telemetry = {}
        result = JudgeAgent(
            LiveGeminiJudge(
                SecretStr(os.environ["GOOGLE_API_KEY"]), os.getenv("JUDGE_GEMINI_MODEL", pipeline.query_agent.model)
            )
        ).evaluate(adapted.judge_input, telemetry=telemetry)
        save("06_judge_output", result)
        save("07_judge_telemetry", telemetry)
        print("Judge:", result["status"])
        print("Provider calls:", telemetry.get("provider_calls"))
        print("Inspect source IDs/URLs in 04_search_output.json to confirm corpus membership.")
        if args.with_summary and result["status"] != "ERROR":
            from run_live_summary import run_summary

            from src.applications.tillegal.agents.judge.adapter import NativeJudgeResult

            return run_summary(NativeJudgeResult(adapted, result, telemetry), args.out / "summary", args.env_file)
        return 0 if result["status"] != "ERROR" else 1
    except Exception as error:
        # Never print upstream response bodies, settings or credentials.
        code = getattr(error, "code", type(error).__name__)
        if type(error).__name__ == "QueryAnalysisError" and str(error) in {
            "QUERY_ANALYSIS_TIMEOUT",
            "QUERY_ANALYSIS_PROVIDER_ERROR",
            "QUERY_ANALYSIS_INVALID_RESPONSE",
        }:
            code = str(error)
        save("failure", {"code": code})
        print("Stopped; see saved stages and failure.json")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
