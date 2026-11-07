"""A verifier-only paired comparison on the exact drafts from a saved local experiment."""
import argparse
import hashlib
import json
from pathlib import Path
from threading import Lock

from src.applications.tillegal.graphs.semantic import assess
from src.framework.llm.gateway import LocalChatProvider


def replay(path, provider):
    data = path.read_bytes()
    report = json.loads(data)
    if report["provider"] != "local" or report["model"] != provider.model:
        raise ValueError("Require the same declared local model as the saved draft")
    rows = []
    for row in report["rows"]:
        if row["mode"] == "draft":
            checks = [assess(c, row["sources"], provider, Lock()) for c in row["claims"] or []]
            rows.append({"case": row["case"], "before": row["status"], "checks": checks,
                         "retained": [c["claim_id"] for c in checks if c["claim_support"] == "SUPPORTED"
                                      and not c.get("publication_blocker")]})
    return {"input_sha256": hashlib.sha256(data).hexdigest(), "rows": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--model", required=True)
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(replay(args.report, LocalChatProvider(args.model,args.port)), stream, ensure_ascii=False, indent=2)
