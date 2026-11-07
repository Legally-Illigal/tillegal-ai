"""Auditable local-only paired experiments; no legal gold labels implied."""

import argparse
import asyncio
import hashlib
import json
import platform
from pathlib import Path
from time import perf_counter

from ai_core.rag_generation import GenerationError, GenerationText

from scripts.benchmark_context import QUESTIONS
from src.applications.tillegal.graphs.legal_qa import LegalQA
from src.framework.llm import gateway

CASES = [dict(id=f"X{i + 1:02}", question=q, category="existing_exploratory") for i, q in enumerate(QUESTIONS)] + [
    dict(
        id="N01",
        question="Đối thoại định kỳ tại nơi làm việc được tổ chức ít nhất bao lâu một lần?",
        category="numeric_minimum",
    ),
    dict(id="N02", question="Người lao động có quyền tham gia bảo hiểm xã hội không?", category="explicit_right"),
    dict(
        id="N03",
        question="Làm thêm giờ cần sự đồng ý của người lao động trong trường hợp nào?",
        category="conditions_exceptions",
    ),
    dict(id="N04", question="Làm thêm giờ và nghỉ hằng năm được quy định như thế nào?", category="multiple_provisions"),
    dict(
        id="N05", question="Tôi làm việc ba tháng thì được nghỉ bao nhiêu ngày?", category="incomplete_personal_facts"
    ),
    dict(id="N06", question="Năm 2050 người lao động được nghỉ hằng năm bao nhiêu ngày?", category="future_temporal"),
]


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


async def run(args):
    calls = []
    frozen = []
    original = gateway.LocalChatProvider

    class Recorder(original):
        def _chat(self, messages, options):
            row = {"messages": messages, "options": options}
            calls.append(row)
            start = perf_counter()
            try:
                if args.replay:
                    expected = frozen.pop(0)
                    if expected["messages"] != messages or expected["options"] != options:
                        raise AssertionError("Replay prompt/schema changed")
                    if "error" in expected:
                        raise GenerationError(expected["error"])
                    raw = GenerationText(expected["raw"], expected.get("usage", {}))
                else:
                    raw = super()._chat(messages, options)
                row.update(raw=str(raw), usage=raw.metadata)
                return raw
            except Exception as exc:
                row["error"] = getattr(exc, "code", type(exc).__name__)
                raise
            finally:
                row["elapsed_ms"] = (perf_counter() - start) * 1000

    gateway.LocalChatProvider = Recorder
    root = Path(__file__).resolve().parents[2]
    source = root / "tillegal-ai-main/src"
    selected_cases = [c for c in CASES if not args.cases or c["id"] in args.cases.split(",")]
    report = {
        "classification": "exploratory_not_human_reviewed",
        "execution": "frozen_real_completions_replay" if args.replay else "live_local",
        "python": platform.python_version(),
        "cases": selected_cases,
        "model": "qwen-pilot",
        "weights_sha256": digest(root / ".tmp/quality-llm/qwen.gguf"),
        "model_revision": "91cad51170dc346986eccefdc2dd33a9da36ead9",
        "quantization": "Q4_K_M",
        "index_sha256": digest(root / "data/indexes/labor-pilot-3-t4-bm25/manifest.json"),
        "retrieval": {"mode": "bm25", "top_k": 3},
        "workflow": "semantic",
        "policies": args.policies.split(","),
        "runner_sha256": digest(Path(__file__)),
        "runtime": {
            "context_tokens": 8192,
            "threads": 4,
            "slots": 1,
            "temperature_server": 0,
            "max_completion_tokens": 1024,
            "provider_timeout_seconds": 25,
            "request_timeout_seconds": 60,
        },
        "source_hashes": {str(p.relative_to(source)): digest(p) for p in source.rglob("*.py")},
        "human_quality": None,
        "memory_bytes": None,
        "rows": [],
    }
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "manifest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf8")
    for policy in args.policies.split(","):
        qa = LegalQA(
            {
                "TILLEGAL_ANSWER_PROVIDER": "local",
                "TILLEGAL_ANSWER_MODEL": "qwen-pilot",
                "TILLEGAL_LOCAL_PORT": "18963",
                "TILLEGAL_CONTEXT_POLICY": policy,
            }
        )
        for case in selected_cases:
            calls.clear()
            if args.replay:
                prior = args.replay / (policy + "-" + case["id"] + ".json")
                frozen[:] = json.loads(prior.read_text(encoding="utf8"))["provider_calls"]
            start = perf_counter()
            try:
                result = await qa.answer(case["question"], case["id"] + "-" + policy, 3, "semantic")
            except Exception as exc:
                if args.replay and isinstance(exc, (AssertionError, IndexError)):
                    raise
                result = {"status": "FAILED", "error": getattr(exc, "code", type(exc).__name__)}
            if args.replay and frozen:
                raise AssertionError("Replay did not consume every recorded completion")
            row = {
                **case,
                "policy": policy,
                "elapsed_ms": (perf_counter() - start) * 1000,
                "result": result,
                "provider_calls": list(calls),
                "condition_exception_review": "NOT_EVALUATED",
            }
            (args.output / (policy + "-" + case["id"] + ".json")).write_text(
                json.dumps(row, ensure_ascii=False, indent=2), encoding="utf8"
            )
            print(policy, case["id"], result["status"], result.get("error", ""), round(row["elapsed_ms"]), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--policies", default="legacy,context,context_judge")
    parser.add_argument("--cases", default="")
    parser.add_argument("--replay", type=Path)
    asyncio.run(run(parser.parse_args()))
