"""Isolated, constructed textual-entailment probes. These examples are not legal gold."""
import argparse
import json
from pathlib import Path
from threading import Lock

from ai_core.data_contracts import content_hash
from src.applications.tillegal.graphs.semantic import assess
from src.framework.llm.gateway import LocalChatProvider


def run(port, model):
    quote = "Theo quy ước thử nghiệm, hồ sơ màu xanh được giữ trong 12 ngày."
    evidence = {"E1":{"document_version_id":"synthetic-v1", "chunk_id":"synthetic-c1",
                      "quote":quote, "quote_sha256":content_hash(quote)}}
    fixtures = [("SUPPORTED", "Thời gian lưu hồ sơ màu xanh là 12 ngày."),
                ("CONTRADICTED", "Hồ sơ màu xanh chỉ được lưu trong 3 ngày."),
                ("INSUFFICIENT_EVIDENCE", "Hồ sơ màu đỏ được lưu trong 5 ngày.")]
    provider = LocalChatProvider(model, port)
    rows = []
    for i, (target, text) in enumerate(fixtures, 1):
        result = assess({"claim_id": f"C{i}", "text":text, "evidence_id":"E1"}, evidence, provider, Lock())
        rows.append({"constructed_target":target, "result":result})
    return {"dataset":"synthetic-nonlegal-v1", "source":quote, "rows":rows}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=8080)
    p.add_argument("--model", required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    with a.output.open("x", encoding="utf-8") as stream:
        json.dump(run(a.port, a.model), stream, ensure_ascii=False, indent=2)
