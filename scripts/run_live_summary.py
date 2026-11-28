# ruff: noqa: E402
"""Summary-only artifact replay or sequential four-agent live demo. Never retries."""

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.applications.tillegal.agents.judge.adapter import AdaptedJudgeInput, NativeJudgeResult
from src.applications.tillegal.agents.judge.schemas import validate_output
from src.applications.tillegal.agents.response.adapter import adapt_judge
from src.applications.tillegal.agents.response.agent import SummaryAgent


def load_carrier(artifacts, judge_dir):
    def read(path):
        return json.loads(path.read_text(encoding="utf-8"))

    a = AdaptedJudgeInput(**read(artifacts / "05b_identity_and_native_context.json"))
    if a.judge_input != read(artifacts / "05_judge_input.json"):
        raise ValueError("ARTIFACT_JUDGE_INPUT_MISMATCH")
    if a.native_context != read(artifacts / "04_search_output.json"):
        raise ValueError("ARTIFACT_SEARCH_MISMATCH")
    if a.native_context["plan"] != read(artifacts / "02_query_output.json"):
        raise ValueError("ARTIFACT_QUERY_MISMATCH")
    r = validate_output(read(judge_dir / "06_judge_output.json"), a.judge_input)
    if r["status"] == "ERROR":
        raise ValueError("ARTIFACT_JUDGE_ERROR")
    return NativeJudgeResult(a, r, read(judge_dir / "07_judge_telemetry.json"))


def run_summary(carrier, out, env_file):
    from dotenv import load_dotenv
    from live_gemini_summary import LiveGeminiSummary
    from pydantic import SecretStr

    load_dotenv(env_file, override=False)
    if not os.getenv("GOOGLE_API_KEY"):
        raise ValueError("GOOGLE_API_KEY_REQUIRED")
    value = adapt_judge(carrier)
    model = os.getenv("SUMMARY_GEMINI_MODEL") or carrier.telemetry.get("model")
    if not model:
        raise ValueError("SUMMARY_MODEL_REQUIRED")
    out.mkdir(parents=True, exist_ok=False)

    def save(name, data):
        (out / (name + ".json")).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    save("08_summary_input", value)
    telemetry = {}
    result = SummaryAgent(LiveGeminiSummary(SecretStr(os.environ["GOOGLE_API_KEY"]), model)).summarize(
        value, telemetry=telemetry
    )
    save("09_summary_output", result)
    save("10_summary_telemetry", telemetry)
    print(
        json.dumps(
            {
                "status": result["status"],
                "error": result["error"],
                "provider_calls": telemetry.get("provider_calls"),
                "model": model,
            }
        )
    )
    return 1 if result["status"] == "ERROR" else 0


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--judge-dir", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        return run_summary(load_carrier(args.artifacts, args.judge_dir), args.out, args.env_file)
    except Exception as error:
        print("Stopped:", getattr(error, "code", type(error).__name__))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
