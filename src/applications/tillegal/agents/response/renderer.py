"""Code-owned native citations; model supplies units, never URLs or source metadata."""

from copy import deepcopy

from .schemas import empty_result, validate_public_output


def render_draft(value, model_output, limitations, context_gaps=None):
    result = empty_result(value, limitations=list(dict.fromkeys(limitations + model_output["limitations"])))
    result["schema_version"] = "2"
    evidence = value["carrier"]["adapted"]["evidence_map"]
    refs = {}
    for unit in model_output["units"]:
        ids = []
        for eid in unit["evidence_ids"]:
            if eid not in refs:
                rid = refs[eid] = "R" + str(len(refs) + 1)
                native = evidence[eid]["native"]
                result["citations"].append(
                    {
                        "citation_id": rid,
                        "evidence_id": eid,
                        "document_id": native["source_document_id"],
                        "chunk_id": native["retrieval_chunk_id"],
                        "document_version_id": None,
                        "source_url": native["source_url"],
                        "title": native["title"],
                        "issued_on": native["issued_on"],
                        "effective_from": native["effective_from"],
                        "effective_to": native["effective_to"],
                        "temporal_status": "UNKNOWN",
                        "content": native["content"],
                        "content_sha256": native["content_sha256"],
                        "content_representation": "retrieval_chunk_content",
                        "source_metadata": deepcopy(native["source_metadata"]),
                        "chunk_metadata": deepcopy(native["chunk_metadata"]),
                        "exact_citation_verified": None,
                        "citation_status": "CANDIDATE_UNVERIFIED",
                    }
                )
            ids.append(refs[eid])
        result["claims"].append(
            {
                "claim_id": "C" + str(len(result["claims"]) + 1),
                "text": unit["text"],
                "issue_ids": deepcopy(unit["issue_ids"]),
                "citation_ids": ids,
                "origin": "draft",
                **({"statement_type": unit["statement_type"]} if "statement_type" in unit else {}),
            }
        )
    if result["claims"]:
        result["status"] = "DRAFT_UNVERIFIED"
        result["answer_draft"] = "\n\n".join(
            c["text"] + " " + " ".join("[" + r + "]" for r in c["citation_ids"]) for c in result["claims"]
        )
    result["issue_reports"] = [
        {
            "issue_id": i["issue_id"],
            "issue_text": i["text"],
            "judge_coverage": next(
                (c["coverage"] for c in value["judge_result"]["issue_checks"] if c["issue_id"] == i["issue_id"]),
                "not_evaluated",
            ),
            "claim_ids": [c["claim_id"] for c in result["claims"] if i["issue_id"] in c["issue_ids"]],
        }
        for i in value["query_plan"]["issues"]
    ]
    result["display_response"] = (
        (result["answer_draft"] or "Chưa có đủ căn cứ để tạo câu trả lời.")
        + "\n\nBản nháp chưa được Verify.\n"
        + "\n".join(result["limitations"])
    )
    return validate_public_output(result)
