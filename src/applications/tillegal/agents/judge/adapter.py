"""Pure native SearchState boundary; no graph, retrieval or model I/O."""

from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256

from pydantic import TypeAdapter

from src.applications.tillegal.agents.query.agent import QueryPlan
from src.applications.tillegal.agents.search.agent import SearchOptions, SearchState, _finish

from .schemas import JudgeError, validate_input
from .support import canonical_json


class JudgeAdapterError(JudgeError):
    def __init__(self, code, native_context):
        super().__init__(code)
        self.native_context = deepcopy(native_context)


@dataclass(frozen=True)
class AdaptedJudgeInput:
    judge_input: dict
    issue_map: dict
    evidence_map: dict
    native_context: dict


@dataclass(frozen=True)
class NativeJudgeResult:
    adapted: AdaptedJudgeInput
    judge_result: dict
    telemetry: dict


def _id(request_id, kind, payload):
    return kind + ":" + sha256(canonical_json([request_id, payload])).hexdigest()


def adapt_search(state, *, request_id, options, search_rounds_completed, query_history, query_text_history):
    """Accept native SearchState plus trusted options and explicit caller history.

    COMPLETE (including NO_MATCH) only. FAILED/PARTIAL/clarification are rejected
    with a detached native_context on JudgeAdapterError, never legal conclusions.
    IDs are deterministic for the same request and exact issue/source payload.
    This does not certify grounding of an externally constructed QueryPlan.
    """
    native = deepcopy(TypeAdapter(SearchState).dump_python(state, mode="json", serialize_as_any=True))

    def reject(code):
        raise JudgeAdapterError(code, native)

    if not isinstance(request_id, str) or not request_id.strip():
        reject("JUDGE_REQUEST_ID_REQUIRED")
    try:
        options = SearchOptions.model_validate(options)
        plan = QueryPlan.model_validate(state["plan"])
        # Rehydrate response subtypes, preserving reranking/fusion extensions.
        from src.applications.tillegal.agents.contract_v2 import SearchEnvelopeV2

        restored = SearchEnvelopeV2.restore_subtypes(state)
        parsed = TypeAdapter(SearchState).validate_python(restored)
        for request, response in zip(parsed["requests"], parsed["responses"], strict=True):
            if any(getattr(request, k) != v or getattr(response, k) != v for k, v in options.model_dump().items()):
                reject("JUDGE_OPTIONS_MISMATCH")
        for index, request in enumerate(parsed["requests"]):
            if request.query != plan.subqueries[index].text or parsed["responses"][index].query != request.query:
                reject("JUDGE_QUERY_MISMATCH")
        rebuilt = _finish(
            parsed["plan"],
            parsed["requests"],
            parsed["responses"],
            total=len(plan.subqueries),
            calls=parsed["executed_searches"],
            clarification=bool(plan.clarification),
        )
        actual = TypeAdapter(SearchState).dump_python(parsed, mode="json", serialize_as_any=True)
        expected = TypeAdapter(SearchState).dump_python(rebuilt, mode="json", serialize_as_any=True)
        if actual != expected:
            reject("JUDGE_SEARCH_STATE_INCONSISTENT")
    except JudgeAdapterError:
        raise
    except (ValueError, TypeError, KeyError, IndexError):
        reject("JUDGE_INVALID_SEARCH_STATE")
    if parsed["completeness"] != "COMPLETE" or parsed["status"] != "COMPLETED":
        reject("JUDGE_SEARCH_NOT_COMPLETE")
    if len(parsed["responses"]) != len(plan.subqueries):
        reject("JUDGE_SEARCH_STATE_INCONSISTENT")
    if not plan.issues:
        reject("JUDGE_ISSUES_REQUIRED")
    issue_map, evidence_map, issues, evidence = {}, {}, [], []
    for index, text in enumerate(plan.issues):
        iid = _id(request_id, "I", [index, text])
        issue_map[iid] = {"issue_index": index, "text": text}
        issues.append({"issue_id": iid, "text": text})
    index_ids = {v["issue_index"]: k for k, v in issue_map.items()}
    for group_index, group in enumerate(parsed["evidence"]):
        item = group.evidence
        payload = item.model_dump(mode="json", exclude={"rank", "raw_score", "score_kind", "retrieval_method"})
        eid = _id(request_id, "E", payload)
        occurrences = [o.model_dump(mode="json") for o in group.occurrences]
        for occurrence in occurrences:
            if any(i not in index_ids for i in occurrence["issue_indices"]):
                reject("JUDGE_INVALID_ISSUE_LINK")
            occurrence["issue_ids"] = [index_ids[i] for i in occurrence["issue_indices"]]
        evidence_map[eid] = {"group_index": group_index, "native": payload, "occurrences": occurrences}
        evidence.append(
            {
                "evidence_id": eid,
                "content": item.content,
                "document_id": str(item.source_document_id),
                "chunk_id": str(item.retrieval_chunk_id),
                "document_version_id": None,
                "title": item.title,
                "source_url": item.source_url,
                "issued_on": item.issued_on.isoformat() if item.issued_on else None,
                "effective_from": item.effective_from.isoformat() if item.effective_from else None,
                "effective_to": item.effective_to.isoformat() if item.effective_to else None,
                "effect_status_reported": item.effect_status_reported,
                "usage_policy": item.usage_policy,
                "quote_representation": "retrieval_chunk_content",
                "exact_citation_verified": None,
                "temporal_status": "UNKNOWN",
                "warnings": ["NATIVE_CHUNK_NOT_VERIFIED_QUOTE"],
            }
        )
    value = validate_input(
        {
            "request_id": request_id,
            "question": plan.original,
            "query_plan": {"issues": issues},
            "evidence": evidence,
            "as_of_date": options.as_of_date.isoformat(),
            "search_rounds_completed": search_rounds_completed,
            "query_history": deepcopy(query_history),
            "query_text_history": deepcopy(query_text_history),
            "context": {
                "bundle_status": "NOT_PROVIDED",
                "groups": [],
                "limitations": ["NATIVE_CHUNKS_NOT_VERIFIED_QUOTES", "LEGAL_VERSION_AND_CONTEXT_NOT_VERIFIED"],
                "native_search": {
                    "links": [
                        {
                            "evidence_id": eid,
                            "query": o["query"],
                            "subquery_index": o["subquery_index"],
                            "issue_ids": o["issue_ids"],
                        }
                        for eid, entry in evidence_map.items()
                        for o in entry["occurrences"]
                    ],
                    "representation": "retrieval_chunk_content",
                    "completeness": "COMPLETE",
                    "warnings": list(parsed["warnings"]),
                    "executed_searches": parsed["executed_searches"],
                    "skipped_subqueries": list(parsed["skipped_subqueries"]),
                },
            },
        }
    )
    return AdaptedJudgeInput(value, issue_map, evidence_map, native)


def evaluate_search(state, *, judge, **context):
    """Adapt once and evaluate independently. Carrier is separate from Judge output."""
    adapted = adapt_search(state, **context)
    telemetry = {}
    result = judge.evaluate(deepcopy(adapted.judge_input), telemetry=telemetry)
    return NativeJudgeResult(adapted, result, telemetry)
