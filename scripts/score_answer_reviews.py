"""Score independent human review of a saved comparison. Refuse incomplete panels."""
import argparse
import hashlib
import json
from pathlib import Path
from statistics import mean


def score(report_path, annotations):
    data = report_path.read_bytes()
    report = json.loads(data)
    if (annotations["report_sha256"] != hashlib.sha256(data).hexdigest()
            or annotations.get("reviewer_type") != "human" or not annotations.get("reviewer_id")):
        raise ValueError("Matching artifact and human review attestation required")
    expected = {(r["case"], r["mode"]): r for r in report["rows"]
                if r["status"] not in {"FAILED", "ABSTAINED", "NO_EVIDENCE", "ABSTAINED_UNVERIFIED"}}
    seen = set()
    groups = {}
    for row in annotations["answers"]:
        key = row["case"], row["mode"]
        if (key not in expected or key in seen or type(row["relevant"]) is not bool or not row["claims"]
                or row.get("all_material_claims_reviewed") is not True):
            raise ValueError("Invalid or duplicate answer review")
        seen.add(key)
        g = groups.setdefault(key[1], {"relevance":[], "support":[], "citation":[]})
        g["relevance"].append(row["relevant"])
        claim_texts = set()
        for claim in row["claims"]:
            if (not claim["text"].strip() or claim["text"] not in expected[key]["answer"]
                    or claim["verdict"] not in {"SUPPORTED","CONTRADICTED","INSUFFICIENT_EVIDENCE"}
                    or claim["text"] in claim_texts or type(claim["citations_correct"]) is not bool):
                raise ValueError("Incomplete claim adjudication")
            claim_texts.add(claim["text"])
            g["support"].append(claim["verdict"] == "SUPPORTED")
            g["citation"].append(claim["citations_correct"])
    if seen != set(expected):
        raise ValueError("Review every published answer before scoring")
    return {mode: {"answers":len(g["relevance"]), "claims":len(g["support"]),
                   "groundedness":mean(g["support"]), "unsupported_claim_rate":1-mean(g["support"]),
                   "answer_relevance":mean(g["relevance"]), "citation_correctness":mean(g["citation"])}
            for mode,g in groups.items()}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("annotations", type=Path)
    args = parser.parse_args()
    print(json.dumps(score(args.report, json.loads(args.annotations.read_text(encoding="utf-8")))))
