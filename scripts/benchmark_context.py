"""A/B/C pilot measurement. Questions are exploratory, never gold or held out."""

import argparse
import asyncio
import hashlib
import json
import platform
from pathlib import Path
from time import perf_counter

from src.applications.tillegal.graphs.legal_qa import LegalQA

QUESTIONS = [
    "Người lao động được nghỉ hằng năm như thế nào?",
    "Thế nào là làm thêm giờ?",
    "Trích dẫn: đối thoại định kỳ",
    "qzzzxxyy qzzzyyyy",
    "Mẫu thỏa thuận có chỗ ghi ngày nghỉ hằng năm không?",
    "Trích dẫn: an toàn lao động",
    "Quy định về đào tạo nghề gồm những nội dung nào?",
    "Trích dẫn: bảo hiểm xã hội",
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


async def run(args):
    config = {"TILLEGAL_ANSWER_PROVIDER": "mock", "TILLEGAL_CONTEXT_POLICY": args.policy}
    qa = LegalQA(config)
    rows = []
    for repeat in range(args.repeats):
        for number, question in enumerate(QUESTIONS):
            started = perf_counter()
            result = await qa.answer(question, f"m4-{repeat}-{number}", 3, "draft")
            context = result.get("context_selection", {})
            rows.append(
                {
                    "case": number,
                    "repeat": repeat,
                    "question": question,
                    "status": result["status"],
                    "elapsed_ms": (perf_counter() - started) * 1000,
                    "selected": result["judgments"][-1]["selected"],
                    "judge": result["judgments"],
                    "context": context,
                    "calls": len(result["retrieval_trace"]),
                    "retrieval_ms": sum(t["elapsed_ms"] for t in result["retrieval_trace"]),
                    "stage_timings": result.get("stage_timings", []),
                    "selected_evidence": [
                        {k: e[k] for k in ("evidence_id", "document_version_id", "chunk_id", "quote_sha256")}
                        for b in result["evidence_bundles"]
                        for e in b["evidence"]
                        if e["evidence_id"] in result["judgments"][-1]["selected"]
                    ],
                    "omitted": sum(
                        len(g["omitted_chunk_ids"]) for b in result["evidence_bundles"] for g in b["groups"]
                    ),
                }
            )
    root = Path(__file__).resolve().parents[2]
    manifest = root / "data/indexes/labor-pilot-3-t4-bm25/manifest.json"
    source = Path(__file__).resolve().parents[1] / "src"
    report = {
        "classification": "exploratory",
        "label_status": "NOT_REVIEWED",
        "policy": args.policy,
        "python": platform.python_version(),
        "dataset_sha256": hashlib.sha256(json.dumps(QUESTIONS, ensure_ascii=False).encode()).hexdigest(),
        "index_manifest_sha256": digest(manifest),
        "model": "mock",
        "model_revision": None,
        "retrieval": {"mode": "bm25", "top_k": 3},
        "workflow": "draft",
        "source_hashes": {str(p.relative_to(source)): digest(p) for p in source.rglob("*.py")},
        "rows": rows,
        "legal_quality_metrics": None,
        "estimated_cost": None,
        "confidence_interval": None,
        "confidence_interval_reason": "Repeated exploratory cases are not independent legal samples",
    }
    with args.output.open("x", encoding="utf8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(args.policy, len(rows), "measurements")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--policy", choices=["legacy", "context", "context_judge"], default="legacy")
    p.add_argument("--repeats", type=int, default=3)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    if args.repeats < 1 or args.output.exists():
        p.error("positive repeats and new output required")
    asyncio.run(run(args))
