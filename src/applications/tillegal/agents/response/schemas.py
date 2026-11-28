"""Representation-aware native Summary contracts; no legacy EvidenceBuilder assumptions."""

import re
from copy import deepcopy
from dataclasses import dataclass
from datetime import date

from src.applications.tillegal.agents.judge.support import ContractError, canonical_json


class SummaryError(ContractError):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def text(limit=4000, nullable=False):
    return {"type": ["string", "null"] if nullable else "string", "minLength": 1, "maxLength": limit, "pattern": r"\S"}


def array(item, limit=128, minimum=0, unique=False):
    return {"type": "array", "items": item, "minItems": minimum, "maxItems": limit, "uniqueItems": unique}


def obj(properties, required=None, additional=False):
    return {
        "type": "object",
        "properties": properties,
        "additionalProperties": additional,
        "required": list(properties) if required is None else required,
    }


ID = text(256)
DATE = {**text(10, True), "format": "date"}
STRINGS = array(text(), 1024, unique=True)
OPAQUE = {"type": "object"}  # Preserved metadata; independently checked against actual bundle below.
NULL_OBJECT = {"type": ["object", "null"]}
VERSION = {"type": "integer", "minimum": 1}
UNIT_SCHEMA = obj(
    {
        "text": text(6000),
        "issue_ids": array(ID, 64, 1, True),
        "evidence_ids": array(ID, 32, 1, True),
        "statement_type": {"enum": ["source_statement", "application"]},
    },
    required=["text", "issue_ids", "evidence_ids"],
)
LLM_OUTPUT_SCHEMA = obj(
    {"units": array(UNIT_SCHEMA, 64), "limitations": array(text(), 64, unique=True), "abstain": {"type": "boolean"}}
)
CLAIM_SCHEMA = obj(
    {
        "claim_id": ID,
        "text": text(6000),
        "issue_ids": array(ID, 64, 1, True),
        "citation_ids": array(ID, 32, 1, True),
        "origin": {"enum": ["draft"]},
        "statement_type": {"enum": ["source_statement", "application"]},
    },
    required=["claim_id", "text", "issue_ids", "citation_ids", "origin"],
)
CONTEXT_GAP_SCHEMA = obj(
    {
        "gap_id": ID,
        "group_id": ID,
        "kind": {"enum": ["OMITTED_CHUNKS", "NON_USABLE_MEMBERS", "SEED_NOT_INCLUDED"]},
        "issue_ids": array(ID, 64, unique=True),
        "evidence_ids": array(ID, 128, unique=True),
        "related_evidence_ids": array(ID, 128, unique=True),
        "omitted_chunk_ids": array(ID, 1024, unique=True),
        "non_usable_evidence_ids": array(ID, 128, unique=True),
        "seed_chunk_id": ID,
        "scope_status": {"enum": ["MAPPED", "GROUP_ONLY_UNKNOWN_ISSUES"]},
        "statement_policy": {"enum": ["SOURCE_STATEMENTS_ONLY_SEMANTIC_EFFECT_UNKNOWN"]},
    }
)
ISSUE_REPORT_SCHEMA = obj(
    {
        "issue_id": ID,
        "issue_text": text(),
        "judge_coverage": {"enum": ["full", "partial", "none", "not_evaluated"]},
        "summary_status": {"enum": ["HAS_DRAFT_CLAIMS", "NO_DRAFT_CLAIMS"]},
        "claim_ids": array(ID, 64, unique=True),
        "context_gap_ids": array(ID, 300, unique=True),
        "limitations": STRINGS,
    }
)


@dataclass(frozen=True)
class SummaryLimits:
    max_input_bytes: int = 100000
    max_output_chars: int = 24000
    max_request_bytes: int = 2000000

    def __post_init__(self):
        if (
            type(self.max_input_bytes) is not int
            or not 1024 <= self.max_input_bytes <= 120000
            or type(self.max_output_chars) is not int
            or not 128 <= self.max_output_chars <= 65536
            or type(self.max_request_bytes) is not int
            or not 1024 <= self.max_request_bytes <= 4000000
        ):
            raise SummaryError("SUMMARY_CONFIGURATION_ERROR")


def check_shape(value, schema):
    """Small JSON Schema subset used here; public schemas also describe wire shape."""
    types = schema.get("type")
    if types:
        types = [types] if isinstance(types, str) else types
        actual = (
            "null"
            if value is None
            else "boolean"
            if type(value) is bool
            else "integer"
            if type(value) is int
            else "string"
            if isinstance(value, str)
            else "array"
            if isinstance(value, list)
            else "object"
            if isinstance(value, dict)
            else None
        )
        if actual not in types:
            raise ValueError("type")
    if "enum" in schema and not any(type(value) is type(v) and value == v for v in schema["enum"]):
        raise ValueError("enum")
    if value is None:
        return
    if isinstance(value, dict):
        props = schema.get("properties", {})
        if not set(schema.get("required", [])) <= set(value) or (
            schema.get("additionalProperties") is False and set(value) - set(props)
        ):
            raise ValueError("fields")
        for key, val in value.items():
            if key in props:
                check_shape(val, props[key])
    elif isinstance(value, list):
        if not schema.get("minItems", 0) <= len(value) <= schema.get("maxItems", len(value)):
            raise ValueError("array length")
        if schema.get("uniqueItems") and len({canonical_json(v) for v in value}) != len(value):
            raise ValueError("duplicates")
        for val in value:
            check_shape(val, schema.get("items", {}))
    elif isinstance(value, str):
        if not schema.get("minLength", 0) <= len(value) <= schema.get("maxLength", len(value)) or (
            "pattern" in schema and not re.search(schema["pattern"], value)
        ):
            raise ValueError("text")
        if schema.get("format") == "date":
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                raise ValueError("date")
            date.fromisoformat(value)
    elif type(value) is int and value < schema.get("minimum", value):
        raise ValueError("minimum")


def _unique(items, field):
    values = [i[field] for i in items]
    if len(values) != len(set(values)):
        raise SummaryError("SUMMARY_DUPLICATE_ID")
    return set(values)


def validate_llm_output(value, summary_input, allowed_ids, context_gaps=None):
    try:
        check_shape(value, LLM_OUTPUT_SCHEMA)
        if value["abstain"] != (not value["units"]) or (value["abstain"] and not value["limitations"]):
            raise SummaryError("SUMMARY_INVALID_ABSTENTION")
        issues = {i["issue_id"] for i in summary_input["query_plan"]["issues"]}
        checks = {c["issue_id"]: set(c["evidence_ids"]) for c in summary_input["judge_result"]["issue_checks"]}
        partial = {c["issue_id"] for c in summary_input["judge_result"]["issue_checks"] if c["coverage"] != "full"}
        affected = {eid for g in context_gaps or [] for eid in g["evidence_ids"]}
        for unit in value["units"]:
            if "[" in unit["text"] or "]" in unit["text"]:
                raise SummaryError("SUMMARY_MODEL_CITATION_MARKER")
            if re.search(r"https?://|www\.", unit["text"], re.IGNORECASE):
                raise SummaryError("SUMMARY_MODEL_SOURCE_URL")
            if not set(unit["issue_ids"]) <= issues or not set(unit["evidence_ids"]) <= set(allowed_ids):
                raise SummaryError("SUMMARY_INVALID_OUTPUT_REFERENCE")
            if any(not set(unit["evidence_ids"]).intersection(checks[i]) for i in unit["issue_ids"]):
                raise SummaryError("SUMMARY_ISSUE_EVIDENCE_MAPPING_MISMATCH")
            if (
                set(unit["issue_ids"]).intersection(partial) or set(unit["evidence_ids"]).intersection(affected)
            ) and unit.get("statement_type") != "source_statement":
                raise SummaryError("SUMMARY_CONTEXT_SCOPE_REQUIRED")
        return deepcopy(value)
    except SummaryError:
        raise
    except (ValueError, TypeError, KeyError, RecursionError):
        raise SummaryError("SUMMARY_INVALID_OUTPUT_SCHEMA") from None


def empty_result(value, *, code=None, stage="input", limitations=None):
    value = value if isinstance(value, dict) else {}

    def valid_text(v, n):
        return v if isinstance(v, str) and v.strip() and len(v) <= n else None

    version = value.get("draft_version")
    as_of = value.get("as_of_date")
    try:
        check_shape(as_of, DATE)
    except (ValueError, TypeError):
        as_of = None
    return {
        "schema_version": "2",
        "request_id": valid_text(value.get("request_id"), 256),
        "as_of_date": as_of,
        "stop_reason": valid_text(value.get("stop_reason"), 256),
        "status": "ERROR" if code else "ABSTAINED_UNVERIFIED",
        "draft_version": version if type(version) is int and version >= 1 else None,
        "answer_draft": None,
        "claims": [],
        "citations": [],
        "limitations": list(dict.fromkeys(limitations or ["DRAFT_NOT_VERIFIED"])),
        "error": {"code": code, "stage": stage} if code else None,
    }


def validate_input(value, limits=None):
    from .adapter import validate_native

    limits = limits or SummaryLimits()
    if len(canonical_json(value)) > limits.max_request_bytes:
        raise SummaryError("SUMMARY_REQUEST_LIMIT")
    return validate_native(value)


def validate_public_output(result):
    # Top-level legacy names/status preserved; native citation representation is version 2.
    if result["schema_version"] != "2" or result["status"] not in {"DRAFT_UNVERIFIED", "ABSTAINED_UNVERIFIED", "ERROR"}:
        raise SummaryError("SUMMARY_INVALID_PUBLIC_OUTPUT")
    check_shape(result["claims"], array(CLAIM_SCHEMA, 64))
    _unique(result["claims"], "claim_id")
    rids = _unique(result["citations"], "citation_id")
    if any(not set(c["citation_ids"]) <= rids for c in result["claims"]):
        raise SummaryError("SUMMARY_INVALID_PUBLIC_REFERENCE")
    for citation in result["citations"]:
        if (
            citation["content_representation"] != "retrieval_chunk_content"
            or citation["document_version_id"] is not None
            or citation["exact_citation_verified"] is not None
            or citation["citation_status"] != "CANDIDATE_UNVERIFIED"
        ):
            raise SummaryError("SUMMARY_INVALID_NATIVE_CITATION")
    draft = result["status"] == "DRAFT_UNVERIFIED"
    if draft != bool(result["claims"]) or (not draft and result["citations"]):
        raise SummaryError("SUMMARY_INVALID_PUBLIC_CONSISTENCY")
    expected = (
        "\n\n".join(c["text"] + " " + " ".join("[" + r + "]" for r in c["citation_ids"]) for c in result["claims"])
        if draft
        else None
    )
    if result["answer_draft"] != expected:
        raise SummaryError("SUMMARY_INVALID_PUBLIC_RENDER")
    return result
