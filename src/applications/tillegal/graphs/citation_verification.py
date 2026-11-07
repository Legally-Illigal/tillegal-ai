"""Deterministic citation checks against a trusted request-local evidence bundle."""
from ai_core.data_contracts import content_hash


def check_candidates(bundle, candidates):
    """The caller supplies the EvidenceBuilder bundle for this run."""
    evidence = {row["evidence_id"]: row for row in bundle["evidence"]}
    checks = []
    for citation in candidates:
        reference = evidence.get(citation.get("evidence_id"))
        identity = reference is not None and all(
            citation.get(key) == reference[key] for key in ("document_id", "document_version_id", "chunk_id")
        )
        quote = citation.get("quote")
        integrity = identity and isinstance(quote, str) and (
            quote == reference["quote"] and content_hash(quote) == reference["quote_sha256"] == citation.get("quote_sha256")
        )
        checks.append({
            "evidence_id": citation.get("evidence_id"),
            "bundle_identity": "MATCH" if identity else "MISMATCH",
            "normalized_quote_against_bundle": "MATCH" if integrity else "UNCONFIRMED",
            "claim_support": "NOT_EVALUATED",
            "temporal_applicability": "NOT_EVALUATED",
            "source_reachability": "NOT_CHECKED",
        })
    return checks


def verify_claims(evidence, selected, proposals):
    """Only verbatim claims from the selected, run-local versions can be published."""
    checks, accepted, citations = [], [], {}
    for claim in proposals:
        key = claim["evidence_id"]
        row = evidence.get(key) if key in selected else None
        citation = dict(row, citation_status="CANDIDATE_UNVERIFIED") if row else {"evidence_id": key}
        check = check_candidates({"evidence": [row] if row else []}, [citation])[0]
        matches = check["normalized_quote_against_bundle"] == "MATCH" and claim["text"] == row["quote"]
        check["source_version_in_bundle"] = row["document_version_id"] if row else None
        check["claim_index"] = len(checks)
        check["claim_text_check"] = "EXACT_QUOTE" if matches else "REJECTED"
        checks.append(check)
        if matches:
            accepted.append(claim)
            citations[key] = citation
    return checks, accepted, list(citations.values())
