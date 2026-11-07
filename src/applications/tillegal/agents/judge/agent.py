"""Conservative evidence triage. Sufficiency is scoped to exact-text lookup."""
import re
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel


class Decision(BaseModel):
    decision: Literal["SUFFICIENT", "INSUFFICIENT", "UNCERTAIN"]
    scope: str
    selected: list[str]
    gaps: list[str]
    jurisdiction: str
    temporal: str
    conflicts: str
    coverage: list[dict]
    outside_reported_period: list[str]
    refinement: list[str]
    stop: str


def outside_period(row, scopes):
    """Only exclude an explicit single date/year wholly outside recorded boundaries."""
    if len(scopes) != 1:
        return False
    scope = scopes[0]
    metadata = row.get("document", {})
    try:
        if scope.isdigit():
            start, end = date(int(scope), 1, 1), date(int(scope), 12, 31)
        else:
            start = end = datetime.strptime(scope, "%d/%m/%Y").date()
        return bool((metadata.get("effective_from") and end < date.fromisoformat(metadata["effective_from"]))
                    or (metadata.get("effective_to") and start > date.fromisoformat(metadata["effective_to"])))
    except (TypeError, ValueError):
        return False


def judge(state, budget, iterations):
    plan = state["plan"]
    evidence = state.get("evidence", {})
    queries = [q["text"].casefold() for q in plan["subqueries"]]
    coverage = [{"query": q, "matches": [key for key, row in evidence.items()
                 if not row["is_heading"] and q in row["quote"].casefold()]} for q in queries]
    relevant = list(dict.fromkeys(key for item in coverage for key in item["matches"]))
    outside = [key for key, row in evidence.items() if outside_period(row, plan["temporal_scope"])]
    relevant = [key for key in relevant if key not in outside]
    foreign = bool(re.search(r"pháp luật (?:mỹ|pháp|nhật bản|hoa kỳ)|tại (?:mỹ|nhật bản|hoa kỳ)\b",
                             plan["original"], re.I))
    versions = {}
    for row in evidence.values():
        versions.setdefault(row["document_id"], set()).add(row["document_version_id"])
    competing_versions = any(len(ids) > 1 for ids in versions.values())
    omitted = any(g["omitted_chunk_ids"] for b in state.get("bundles", []) for g in b["groups"])
    gaps = []
    if foreign:
        gaps.append("OUTSIDE_PILOT_JURISDICTION")
        relevant = []
    if competing_versions:
        gaps.append("COMPETING_DOCUMENT_VERSIONS")
    if plan["clarification"]:
        gaps.append("CLARIFICATION_REQUIRED")
    if not evidence:
        gaps.append("NO_EVIDENCE")
    elif not relevant:
        gaps.append("NO_EXACT_TOPIC_MATCH")
    if omitted:
        gaps.append("OMITTED_CONTEXT")
    if plan["temporal_scope"]:
        gaps.append("APPLICABLE_VERSION_UNCONFIRMED")
    if plan["intent"] != "quote_lookup":
        gaps.append("CONDITIONS_AND_EXCEPTIONS_UNCONFIRMED")
    if re.search(r"ngoại lệ|trừ trường hợp|điều kiện", plan["original"], re.I):
        gaps.append("EXCEPTION_COVERAGE_UNCONFIRMED")
    decision = "SUFFICIENT" if not gaps else "UNCERTAIN" if evidence else "INSUFFICIENT"
    trace = state.get("search_trace", [])
    seen = {t["query"].casefold() for t in trace}
    refinement = [q["text"] + " điều kiện ngoại lệ" for q in plan["subqueries"]
                  if (q["text"] + " điều kiện ngoại lệ").casefold() not in seen and len(q["text"]) <= 9970]
    if plan["clarification"]:
        stop = "CLARIFICATION"
    elif decision == "SUFFICIENT":
        stop = "EXACT_LOOKUP_COVERED"
    elif len(trace) >= budget:
        stop = "RETRIEVAL_BUDGET"
    elif state["iteration"] >= iterations:
        stop = "ITERATION_LIMIT"
    elif state["iteration"] > 1 and not state["new_count"]:
        stop = "NO_NEW_EVIDENCE"
    elif not refinement:
        stop = "NO_NEW_QUERY"
    else:
        stop = "REFINE"
    return Decision(decision=decision, scope=plan["intent"], selected=relevant[:3], gaps=gaps,
                    jurisdiction="OUTSIDE_VN_PILOT" if foreign else "VN_PILOT_CASE_UNCONFIRMED",
                    temporal="REPORTED_PERIOD_MISMATCH" if outside else "UNCONFIRMED", coverage=coverage,
                    outside_reported_period=outside,
                    conflicts="MULTIPLE_VERSIONS" if competing_versions else "NO_SEMANTIC_CHECK",
                    refinement=refinement if stop == "REFINE" else [], stop=stop).model_dump()
