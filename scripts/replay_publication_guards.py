"""Apply deterministic guards to previously published real claims; no LLM resampling."""

import argparse
import json
from collections import Counter
from pathlib import Path
from threading import Lock

from src.applications.tillegal.graphs.semantic import assess

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    rows = []
    for path in sorted(args.input.glob("*.json")):
        if path.name == "manifest.json":
            continue
        case = json.loads(path.read_text(encoding="utf8"))
        result = case["result"]
        evidence = {e["evidence_id"]: e for b in result.get("evidence_bundles", []) for e in b["evidence"]}
        for claim in result.get("claims", []):
            check = assess(claim, evidence, None, Lock())
            rows.append(
                {
                    "case": case["id"],
                    "policy": case["policy"],
                    "claim": claim,
                    "source": evidence[claim["evidence_id"]]["quote"],
                    "current_publication_blocker": check.get("publication_blocker"),
                    "interpretation": "Deterministic regression diagnostic, not a legal verdict",
                }
            )
    with args.output.open("x", encoding="utf8") as f:
        json.dump(
            {
                "published_before": len(rows),
                "blocked_by_current_guard": dict(
                    Counter(r["current_publication_blocker"] for r in rows if r["current_publication_blocker"])
                ),
                "rows": rows,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
