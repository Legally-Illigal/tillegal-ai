"""Run the insurance regression against a running local semantic HTTP workflow."""
import argparse
import hashlib
import json
from http.client import HTTPConnection
from uuid import uuid4


def smoke(port):
    rid = str(uuid4())
    body = dict(question="Người lao động có quyền tham gia bảo hiểm xã hội không?", workflow="semantic", top_k=3)
    conn = HTTPConnection("127.0.0.1", port, timeout=75)
    try:
        conn.request("POST", "/pilot/legal-qa", json.dumps(body), {"Content-Type": "application/json", "X-Request-ID": rid})
        response = conn.getresponse()
        result = json.load(response)
        if response.status != 200:
            raise RuntimeError((response.status, result))
    finally:
        conn.close()
    if (result["status"], result["provider"], result["request_id"]) != ("DRAFT", "local", rid) or not result["claims"]:
        raise ValueError("Expected a request-local draft from the real provider")
    evidence = {}
    for bundle in result["evidence_bundles"]:
        if bundle["request_id"] != rid:
            raise ValueError("Cross-request evidence")
        evidence.update({e["evidence_id"]: e for e in bundle["evidence"]})
    citations = {c["evidence_id"]: c for c in result["candidate_citations"]}
    for claim in result["claims"]:
        key = claim["evidence_id"]
        row = evidence[key]
        for field in ("document_version_id", "document_id", "chunk_id", "source_locator", "normalized_locator", "quote_sha256", "quote"):
            if not row[field] or citations[key][field] != row[field]:
                raise ValueError(f"Invalid citation {field}")
        if hashlib.sha256(row["quote"].encode()).hexdigest() != row["quote_sha256"]:
            raise ValueError("Quote hash mismatch")
        check, = [c for c in result["citation_checks"] if (c["claim_id"], c["evidence_id"]) == (claim["claim_id"], key)]
        span = check["evidence_span"]
        if (check["claim_support"] != "SUPPORTED" or check["publication_blocker"] or not span["text"]
                or not 0 <= span["start"] < span["end"] <= len(row["quote"])
                or row["quote"][span["start"]:span["end"]] != span["text"]):
            raise ValueError("Published claim failed evidence check")
    print(json.dumps(dict(run_id=result["run_id"], answer=result["answer"], citations=list(citations))))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    smoke(parser.parse_args().port)
