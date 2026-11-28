"""Pure native Judge carrier projection; no retrieval/model/database access."""

from copy import deepcopy
from dataclasses import asdict

from src.applications.tillegal.agents.judge.adapter import AdaptedJudgeInput, NativeJudgeResult, adapt_search
from src.applications.tillegal.agents.judge.schemas import validate_input as judge_input
from src.applications.tillegal.agents.judge.schemas import validate_output
from src.applications.tillegal.agents.judge.support import canonical_json

from .schemas import SummaryError


def validate_native(value):
    try:
        if set(value) != {
            "schema_version",
            "carrier",
            "request_id",
            "question",
            "query_plan",
            "as_of_date",
            "draft_version",
            "stop_reason",
            "previous_draft",
            "verification_report",
            "judge_result",
        }:
            raise ValueError("fields")
        if value["schema_version"] != "2" or value["draft_version"] != 1 or type(value["draft_version"]) is not int:
            raise ValueError("version")
        if value["previous_draft"] is not None or value["verification_report"] is not None:
            raise ValueError("revision unavailable")
        carrier = value["carrier"]
        if set(carrier) != {"adapted", "judge_result", "telemetry"}:
            raise ValueError("carrier fields")
        original = AdaptedJudgeInput(**carrier["adapted"])
        ji = judge_input(original.judge_input)
        state = original.native_context
        if not state["requests"]:
            raise ValueError("no native options")
        options = {k: state["requests"][0][k] for k in ("mode", "top_k", "as_of_date", "allowed_usage_policies")}
        rebuilt = adapt_search(
            state,
            request_id=ji["request_id"],
            options=options,
            search_rounds_completed=ji["search_rounds_completed"],
            query_history=ji["query_history"],
            query_text_history=ji["query_text_history"],
        )
        if asdict(rebuilt) != carrier["adapted"]:
            raise ValueError("carrier mismatch")
        validate_output(carrier["judge_result"], ji)
        if value["judge_result"] != carrier["judge_result"]:
            raise ValueError("judge result mismatch")
        for key in ("request_id", "question", "query_plan", "as_of_date"):
            if value[key] != ji[key]:
                raise ValueError("context mismatch")
        if not isinstance(value["stop_reason"], str) or not 1 <= len(value["stop_reason"]) <= 256:
            raise ValueError("stop reason")
        projected = deepcopy(ji)
        return deepcopy(value), projected
    except SummaryError:
        raise
    except (ValueError, TypeError, KeyError, AttributeError):
        raise SummaryError("SUMMARY_INVALID_NATIVE_CARRIER") from None


def adapt_judge(result: NativeJudgeResult, *, stop_reason="single_pass_completed", draft_version=1):
    ji = result.adapted.judge_input
    value = {
        "schema_version": "2",
        "carrier": asdict(result),
        **{k: deepcopy(ji[k]) for k in ("request_id", "question", "query_plan", "as_of_date")},
        "draft_version": draft_version,
        "stop_reason": stop_reason,
        "previous_draft": None,
        "verification_report": None,
        "judge_result": deepcopy(result.judge_result),
    }
    from .schemas import SummaryLimits

    if len(canonical_json(value)) > SummaryLimits().max_request_bytes:
        raise SummaryError("SUMMARY_REQUEST_LIMIT")
    return validate_native(value)[0]


def select_context(value, projected):
    allowed = set(value["carrier"]["judge_result"]["usable_evidence_ids"])
    selected = [deepcopy(e) for e in projected["evidence"] if e["evidence_id"] in allowed]
    # Query associations are intent only; claim validation uses Judge issue_checks.
    context = {
        "representation": "retrieval_chunk_content",
        "context_gaps": [],
        "limitations": deepcopy(projected["context"]["limitations"]),
        "warnings": deepcopy(projected["context"]["native_search"]["warnings"]),
    }
    return selected, context, []


def collect_limitations(value, selected):
    judge = value["carrier"]["judge_result"]
    limits = [
        "DRAFT_NOT_VERIFIED",
        "CITATION_MAPPING_IS_STRUCTURAL_NOT_SEMANTIC",
        "NATIVE_CHUNK_NOT_VERIFIED_QUOTE",
        "LEGAL_VERSION_AND_CONTEXT_NOT_VERIFIED",
    ]
    if judge["status"] == "INSUFFICIENT":
        limits.append("JUDGE_INSUFFICIENT")
    limits += judge["missing_items"]
    limits += value["carrier"]["adapted"]["judge_input"]["context"]["native_search"]["warnings"]
    for check in judge["issue_checks"]:
        if check["coverage"] != "full":
            limits.append(check["issue_id"] + ": Chưa đủ căn cứ để trả lời toàn bộ vấn đề.")
    for item in selected:
        limits.extend(item.get("warnings", []))
        limits.append("USAGE_POLICY:" + item.get("usage_policy", "UNKNOWN"))
        if item.get("temporal_status") == "UNKNOWN":
            limits.append(item["evidence_id"] + ":APPLICABILITY_AT_AS_OF_DATE_NOT_VERIFIED")
    return list(dict.fromkeys(limits))
