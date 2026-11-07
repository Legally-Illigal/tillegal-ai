"""Select complete assembled article windows without rewriting canonical evidence."""

import re
from time import perf_counter

from ai_core.data_contracts import content_hash

from src.framework.tools.error_handling import ToolExecutionError

VERSION = "context-v2"
STOP = set(
    (
        "người được như thế nào trong theo các của và là có về quy định điều luật bộ những nội dung gồm trích dẫn không"
    ).split()
)


def tokens(text):
    return set(re.findall(r"[^\W\d_]+", text.casefold(), flags=re.UNICODE)) - STOP


def window_key(row):
    chunk = row["chunk"]
    boundaries = tuple(n["node_id"] for n in row["ancestry"] if n["kind"] in ("form", "appendix"))
    return row["document_version_id"], row["article_id"], chunk["scope"], boundaries


def select_context(state, max_chars=24000):
    started = perf_counter()
    evidence = state.get("evidence", {})
    form_intent = bool(re.search(r"biểu mẫu|\bmẫu\b|điền vào|điền đơn", state["question"], re.I))
    query_terms = tokens(state["question"])
    windows = {}
    for key, row in evidence.items():
        if (
            key != row["evidence_id"]
            or content_hash(row["quote"]) != row["quote_sha256"]
            or row["document_version_id"] != row["chunk"].get("document_version_id")
            or row["document_version_id"] != row["document"].get("document_version_id")
            or row["quote"] != row["chunk"].get("text")
            or row["quote_sha256"] != row["chunk"].get("text_sha256")
        ):
            raise ToolExecutionError("CONTEXT_EVIDENCE_INTEGRITY")
        windows.setdefault(window_key(row), []).append(key)
    candidates = []
    for identity, ids in windows.items():
        rows = [evidence[key] for key in ids]
        reasons = []
        scope = identity[2]
        form = scope == "form" or any(n["kind"] == "form" for r in rows for n in r["ancestry"])
        if form and not form_intent:
            reasons.append("FORM_OUTSIDE_INTENT")
        if scope == "quoted":
            reasons.append("QUOTED_SCOPE")
        if not identity[1] and not (form and form_intent and identity[3]):
            reasons.append("NO_ARTICLE_IDENTITY")
        body = [r for r in rows if not r["is_heading"]]
        if not body:
            reasons.append("HEADING_ONLY")
        if any(
            r["attachment_status"] == "REVIEW_REQUIRED"
            or "SOURCE_TEXT_POSSIBLY_INCOMPLETE" in r["chunk"].get("issues", [])
            for r in rows
        ):
            reasons.append("UNRESOLVED_SOURCE")
        blank = any(re.search(r"\.{5,}|…{2,}", r["quote"]) for r in body)
        if blank and not form_intent:
            reasons.append("PLACEHOLDER")
        covered = max((len(tokens(r["quote"]) & query_terms) for r in rows), default=0)
        relevance = covered / max(len(query_terms), 1)
        if not query_terms or covered < min(2, len(query_terms)) or relevance < 0.35:
            reasons.append("LOW_LEXICAL_COVERAGE")
        # Omission pertains to this version/window only; another article cannot fill the gap.
        ids_set = set(ids)
        omissions = set()
        for bundle in state.get("bundles", []):
            for group in bundle["groups"]:
                if any(m["evidence_id"] in ids_set for m in group["members"]):
                    omissions.update(group["omitted_chunk_ids"])
        known_chunks = {r["chunk_id"] for r in rows}
        omissions -= known_chunks
        if omissions:
            reasons.append("OMITTED_CONTEXT")
        for row in body:
            if row["quote"].rstrip().endswith(":"):
                followers = [
                    other
                    for other in body
                    if row["chunk_id"] != other["chunk_id"]
                    and row["chunk"]["node_id"] in other["chunk"]["ancestor_ids"]
                    and (other["source_locator"]["block_source_start"], other["normalized_locator"]["start"])
                    > (row["source_locator"]["block_source_start"], row["normalized_locator"]["start"])
                ]
                if not followers:
                    reasons.append("INTRO_WITHOUT_DESCENDANTS")
        chars = sum(len(r["quote"]) for r in rows)
        if chars > max_chars:
            reasons.append("CONTEXT_BUDGET")
        candidates.append(
            {
                "identity": list(identity),
                "evidence_ids": ids,
                "relevance": relevance,
                "missing_chunk_ids": sorted(omissions),
                "reasons": sorted(set(reasons)),
                "chars": chars,
                "form": form,
            }
        )
    eligible = [c for c in candidates if not c["reasons"]]
    eligible.sort(key=lambda c: (-c["relevance"], c["chars"], str(c["identity"])))
    selected = eligible[0]["evidence_ids"] if eligible else []
    selected = sorted(
        selected,
        key=lambda key: (
            evidence[key]["source_locator"]["block_source_start"],
            evidence[key]["normalized_locator"]["start"],
            key,
        ),
    )
    # Keep every row in the chosen window, including headings, conditions and exceptions.
    return {
        "version": VERSION,
        "selected": selected,
        "candidates": candidates,
        "status": "ASSEMBLED_UNVERIFIED" if selected else "ABSTAIN",
        "form_intent": form_intent,
        "elapsed_ms": (perf_counter() - started) * 1000,
        "omitted_candidate_windows": max(len(eligible) - 1, 0),
    }


def context_judge(state, legacy_decision, budget, rounds):
    decision = dict(legacy_decision)
    context = state["context_selection"]
    selected = list(context["selected"])
    if decision["jurisdiction"] == "OUTSIDE_VN_PILOT" or decision["outside_reported_period"]:
        selected = [key for key in selected if key not in decision["outside_reported_period"]]
        # A partial window would lose conditions, so reject it as a whole.
        if len(selected) != len(context["selected"]) or decision["jurisdiction"] == "OUTSIDE_VN_PILOT":
            selected = []
    if "COMPETING_DOCUMENT_VERSIONS" in decision["gaps"]:
        selected = []
    decision.update(
        selected=selected,
        decision="UNCERTAIN" if selected else "INSUFFICIENT",
        answerability="UNKNOWN",
        evidence_sufficiency="NOT_LEGALLY_EVALUATED",
        missing_conditions="UNCONFIRMED",
        missing_exceptions="UNCONFIRMED",
        retrieval_relevance="LEXICAL_MATCH" if selected else "NO_USABLE_CONTEXT",
        context_status=context["status"],
    )
    seen = {row["query"].strip().casefold() for row in state["search_trace"]}
    ranked_refinements = []
    query_terms = tokens(state["question"])
    # A source-derived heading is a concrete retrieval target; no invented legal concepts.
    for candidate in context["candidates"]:
        if candidate["relevance"] < 0.35 or candidate["form"] or "QUOTED_SCOPE" in candidate["reasons"]:
            continue
        for key in candidate["evidence_ids"]:
            row = state["evidence"][key]
            if row["is_heading"]:
                query = re.sub(r"^Điều\s+\d+[a-z]?\.?\s*", "", row["quote"], flags=re.I).strip()
                overlap = len(tokens(query) & query_terms)
                # A relevant article can contain generic chapter headings. Do not spend
                # the bounded search budget on them or on unrelated inherited headings.
                if (query and len(query) <= 300 and overlap >= min(2, len(query_terms))
                        and query_terms and query.casefold() not in seen):
                    ranked_refinements.append((overlap / max(len(tokens(query)), 1), overlap, query))
                    seen.add(query.casefold())
    ranked_refinements.sort(key=lambda item: (-item[0], -item[1], len(item[2]), item[2]))
    refinements = [item[2] for item in ranked_refinements[:max(0, budget-len(state["search_trace"]))]]
    # Topic lookups can retrieve lists of contract fields instead of the rule for
    # a participant. Expand only with a participant literally present in evidence.
    if not selected and state["plan"].get("intent") == "quote_lookup":
        topic = state["plan"]["subqueries"][0]["text"]
        for subject in ("người lao động", "người sử dụng lao động"):
            if subject not in topic.casefold() and any(
                subject in row["quote"].casefold() for row in state["evidence"].values()
            ):
                query = topic + " " + subject
                if query.casefold() not in seen:
                    refinements.insert(0, query)
                    break
        refinements = refinements[:max(0, budget-len(state["search_trace"]))]
    if state["plan"]["clarification"]:
        stop = "CLARIFICATION"
        decision["selected"] = []
    elif selected:
        stop = "CONTEXT_READY_UNVERIFIED"
    elif len(state["search_trace"]) >= budget:
        stop = "RETRIEVAL_BUDGET"
    elif state["iteration"] > 1 and not state["new_count"]:
        stop = "NO_NEW_EVIDENCE"
    elif state["iteration"] >= rounds:
        stop = "ITERATION_LIMIT"
    elif not refinements:
        stop = "NO_SOURCE_GROUNDED_REFINEMENT"
    else:
        stop = "REFINE"
    decision.update(stop=stop, refinement=refinements if stop == "REFINE" else [])
    return decision
