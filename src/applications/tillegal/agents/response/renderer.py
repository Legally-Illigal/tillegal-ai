"""Code-owned native citations; model supplies units, never URLs or source metadata."""

import re
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
    result["display_response"] = render_display_response(result)
    return validate_public_output(result)


def source_location(citation):
    """Display stored structural breadcrumb labels only, never references inside body text."""
    metadata = citation.get("chunk_metadata") or {}
    breadcrumb = metadata.get("breadcrumb")
    if not isinstance(breadcrumb, str):
        return []
    labels = []
    for segment in breadcrumb.split(">"):
        match = re.match(
            r"^\s*(Điều\s+\d+[a-zđ]?|Khoản\s+\d+[a-zđ]?|Điểm\s+[a-zđ]|Phụ lục\s+[IVXLC\d]+)(?=\s|:|$)", segment, re.I
        )
        if match:
            labels.append(match.group(1).strip())
    return list(dict.fromkeys(labels))


def render_display_response(result):
    """Human-readable answer and source list; raw audit fields remain untouched."""
    if result.get("status") == "ERROR":
        return "Chưa thể tạo câu trả lời do lỗi xử lý. Vui lòng thử lại sau."
    lines = [result.get("answer_draft") or "Chưa có đủ căn cứ để tạo câu trả lời."]
    citations = result.get("citations", [])
    if citations:
        lines += ["", "Nguồn tham khảo"]
        for item in citations:
            title = item.get("title") or "Chưa xác định tên văn bản"
            location = source_location(item)
            suffix = "; ".join(location) if location else "chưa xác định điều/khoản/điểm từ dữ liệu nguồn"
            lines.append("[" + item["citation_id"] + "] " + title + " — " + suffix + ".")
    messages = readable_limitations(result)
    raw_limits = result.get("limitations", [])
    if any("TEMPORAL" in x or "APPLICABILITY" in x for x in raw_limits):
        messages.append("Chưa xác minh đầy đủ hiệu lực và khả năng áp dụng tại thời điểm yêu cầu.")
    if any("EXPERIMENTAL_ONLY" in x for x in raw_limits):
        messages.append("Nguồn dữ liệu hiện được sử dụng trong phạm vi thử nghiệm.")
    if any(x in raw_limits for x in ("LEGAL_VERSION_AND_CONTEXT_NOT_VERIFIED", "NATIVE_CHUNK_NOT_VERIFIED_QUOTE")):
        messages.append("Vị trí nêu theo cấu trúc dữ liệu đã lưu; chưa đối chiếu nguyên văn và toàn bộ ngữ cảnh nguồn.")
    lines += ["", "Giới hạn", "• Đây là bản nháp chưa được kiểm chứng claim và trích dẫn (Verify)."]
    lines += ["• " + message for message in dict.fromkeys(messages)]
    return "\n".join(lines)


def readable_limitations(result):
    """Conservative display-only deduplication; preserve distinct issue/context gaps."""
    reports = result.get("issue_reports", [])
    default_scope = reports[0]["issue_id"] if len(reports) == 1 else None
    entries = []
    generic = "Chưa đủ căn cứ để trả lời toàn bộ vấn đề."
    prefix = re.compile(r"^\s*(?:issue_id\s*:\s*)?(I:[0-9a-f]+)\s*[:–—-]\s*", re.I)
    for raw in result.get("limitations", []):
        match = prefix.match(raw)
        scope = match.group(1) if match else default_scope
        text = raw[match.end() :].strip() if match else raw.strip()
        if re.fullmatch(r"[A-Z0-9_:.-]+", text) or re.match(r"^E:[0-9a-f]+:", text):
            continue
        if not text:
            continue
        duplicate = False
        for previous_scope, previous in entries:
            if text == previous and scope == previous_scope:
                duplicate = True
                break
            # Merge only near-duplicate procedural gaps in a known identical issue.
            procedural = all(any(word in s.casefold() for word in ("thủ tục", "trình tự")) for s in (text, previous))
            left, right = (set(re.findall(r"\w+", s.casefold())) for s in (text, previous))
            shared = len(left & right)
            if (
                scope is not None
                and scope == previous_scope
                and procedural
                and shared >= 6
                and shared / min(len(left), len(right)) >= 0.7
            ):
                duplicate = True
                break
        if not duplicate:
            entries.append((scope, text))
    # Unscoped Judge prose may repeat one scoped model gap. Merge only when
    # exactly one issue matches; ambiguous cross-issue gaps stay visible.
    filtered = []
    for scope, text in entries:
        candidates = set()
        if scope is None and any(w in text.casefold() for w in ("thủ tục", "trình tự")):
            left = set(re.findall(r"\w+", text.casefold()))
            for other_scope, other in entries:
                if other_scope is None or not any(w in other.casefold() for w in ("thủ tục", "trình tự")):
                    continue
                right = set(re.findall(r"\w+", other.casefold()))
                if len(left & right) >= 6 and len(left & right) / min(len(left), len(right)) >= 0.7:
                    candidates.add(other_scope)
        if len(candidates) != 1:
            filtered.append((scope, text))
    entries = filtered
    # A scoped generic warning adds nothing when a specific gap for that issue exists.
    return [
        text
        for scope, text in entries
        if not (
            text == generic
            and scope is not None
            and any(other_scope == scope and other != generic for other_scope, other in entries)
        )
    ]
