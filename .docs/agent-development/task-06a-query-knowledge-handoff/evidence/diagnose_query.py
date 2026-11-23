"""Read-only synthetic Query diagnostics; trace locals without changing application code."""

import asyncio
import inspect
import json
import re
import sys
import unicodedata
from pathlib import Path

from langsmith import tracing_context
from pydantic import ValidationError

from src.applications.tillegal.agents.query.agent import QueryInputError, QueryPlan, Subquery, understand
from tests.graph.test_query_search_workflow import FakeRetrieval, context, workflow

OUT = Path(".docs/agent-development/task-06a-query-knowledge-handoff/evidence")
SOURCE = Path(inspect.getsourcefile(understand))
LINES = SOURCE.read_text(encoding="utf-8").splitlines()
NORM_LINE = next(i for i, line in enumerate(LINES, 1) if "text = unicodedata.normalize" in line)
DATE_LINE = next(i for i, line in enumerate(LINES, 1) if "mention = match.group()" in line)
TOPIC_LINE = next(i for i, line in enumerate(LINES, 1) if "topic_text = match.group()" in line)
BASE = "  Người lao động được nghỉ phép bao nhiêu ngày?  "
CASES = [
    ("ordinary", "Người lao động được nghỉ phép bao nhiêu ngày?"),
    ("lookup", "Trích dẫn: đối thoại"),
    ("ambiguous", "Có được không?"),
    ("invalid_date", "Quy định ngày 31/02/2024"),
    ("leap_date", "Quy định ngày 29/02/2024"),
    ("year", "Quy định năm 2024"),
    ("nfc", BASE),
    ("nfd", unicodedata.normalize("NFD", BASE)),
    ("multiple", "Đối thoại định kỳ? Nghỉ phép; Tiền lương"),
    ("multi_rule", "Trích dẫn: tiền lương ngày 31/02/2024"),
    ("too_many", "thuế; nghỉ phép; tiền lương; làm thêm giờ; hợp đồng"),
    ("override", "thuế; nghỉ phép; tiền lương; điều kiện; 31/02/2024"),
    ("prefix_empty", "Trích dẫn:"),
    ("single_word", "thuế"),
    ("bare_prefix", "Trích dẫn"),
    ("relative", "Quy định HIỆN NAY"),
    ("unsupported_relative", "Quy định ngày mai"),
    ("partial_month", "Quy định tháng 02/2024"),
    ("partial_day", "Quy định ngày 29/02"),
    ("iso_date", "Quy định ngày 2024-02-29"),
    ("repeated_year", "Năm 2024 và năm 2024 áp dụng thế nào?"),
    ("base_duplicates", "nghỉ phép; nghỉ phép"),
    ("guarded_and", "Tôi nghỉ phép và thủ tục xin nghỉ như thế nào?"),
    ("plain_and", "Nghỉ phép và tiền lương được tính thế nào?"),
    ("topic_cap", "Tôi hỏi tiền lương, nghỉ phép, làm thêm giờ, đối thoại định kỳ và thời giờ làm việc?"),
    ("punctuation", "? ;"),
    ("tab_part", "Quy định thuế; " + chr(9) + " ;nghỉ phép"),
    ("negated_domain", "Tôi không hỏi về lao động, chỉ hỏi thuế"),
    ("domain_miss", "Bảo hiểm xã hội có bắt buộc không?"),
    ("law_number", "Điều 3 luật 45/2019/QH14 quy định gì?"),
    ("lookup_multi", "Trích dẫn: đối thoại? nghỉ phép?"),
    ("extra_space_prefix", "Trích  dẫn: đối thoại"),
    ("quoted_lookup", "Trích nguyên văn: “Điều 1.”"),
    ("old_leap_invalid", "Quy định ngày 29/02/1900"),
    ("relative_current", "Quy định hiện hành"),
    ("zero_width", chr(0x200B)),
    ("empty", ""),
    ("whitespace", " " + chr(9) + chr(10) + chr(13)),
    ("non_string", None),
    ("length", "x" * 10001),
    ("control", "nghỉ phép" + chr(0)),
    ("surrogate", "nghỉ phép" + chr(0xD800)),
]


def encode(value):
    if isinstance(value, re.Match):
        return {"group": value.group(), "span": list(value.span())}
    if isinstance(value, set):
        return sorted(value)
    if isinstance(value, (list, tuple)):
        return [encode(v) for v in value]
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value


def diagnose(question):
    result = {"label": "OBSERVED", "visited_lines": [], "raw_temporal_matches": [], "raw_topic_matches": []}

    def tracer(frame, event, arg):
        if frame.f_code is not understand.__code__:
            return None
        if event == "line":
            result["visited_lines"].append(frame.f_lineno)
            if frame.f_lineno == NORM_LINE:
                result["post_validation"] = question
            if frame.f_lineno == NORM_LINE + 1:
                result["post_normalization"] = frame.f_locals["text"]
            if frame.f_lineno == DATE_LINE:
                result["raw_temporal_matches"].append(encode(frame.f_locals["match"]))
            if frame.f_lineno == TOPIC_LINE:
                result["raw_topic_matches"].append(encode(frame.f_locals["match"]))
        if event == "return":
            result["final_locals"] = {
                key: encode(frame.f_locals[key])
                for key in [
                    "text",
                    "parts",
                    "prefix",
                    "topic",
                    "quote_only",
                    "queries",
                    "dates",
                    "invalid_date",
                    "clarification",
                    "subqueries",
                    "seen",
                ]
                if key in frame.f_locals
            }
        return tracer

    previous = sys.gettrace()
    sys.settrace(tracer)
    try:
        result["plan"] = understand(question)
    except Exception as error:
        result["exception_type"] = type(error).__name__
        result["error_code"] = str(error) if isinstance(error, QueryInputError) else None
    finally:
        sys.settrace(previous)
    result["visited_lines"] = sorted(set(result["visited_lines"]))
    return result


async def graph_probe(question):
    service = FakeRetrieval()
    with tracing_context(enabled=False):
        try:
            state = await workflow(service).execute(question, context("diagnostic", "synthetic"), timeout_seconds=2)
            return {
                "label": "OBSERVED_WITH_FAKE_RETRIEVAL",
                "status": state["status"],
                "plan": state["plan"],
                "retrieval_calls": len(service.requests),
                "handoff_status": state["handoff"].status if state["handoff"] else None,
            }
        except Exception as error:
            return {
                "label": "OBSERVED_WITH_FAKE_RETRIEVAL",
                "exception_type": type(error).__name__,
                "error_code": str(error) if isinstance(error, QueryInputError) else None,
                "retrieval_calls": len(service.requests),
            }


def schema_checks():
    plan = understand("Trích dẫn: đối thoại")
    results = {}
    for name, changes in [
        ("missing_clarification", {k: v for k, v in plan.items() if k != "clarification"}),
        ("extra_ignored", {**plan, "confidence": 0.99}),
        ("unsupported_intent", {**plan, "intent": "summarize"}),
        ("empty_subqueries", {**plan, "subqueries": []}),
        ("schema_accepts_invalid_date_string", {**plan, "temporal_scope": ["31/02/2024"]}),
    ]:
        try:
            results[name] = {"status": "ACCEPTED", "output": QueryPlan.model_validate(changes).model_dump()}
        except ValidationError as error:
            results[name] = {
                "status": "REJECTED",
                "errors": [{"type": e["type"], "loc": e["loc"]} for e in error.errors()],
            }
    results["subquery_whitespace"] = Subquery(text=" ", purpose="topic").model_dump()
    return results


if __name__ == "__main__":
    traces = []
    for name, question in CASES:
        result = diagnose(question)
        if name == "length":
            result["input"] = {"construction": "'x' * 10001", "observed_length": len(question)}
        else:
            result["input"] = question
        result["id"] = name
        result["graph"] = asyncio.run(graph_probe(question))
        traces.append(result)
    by_id = {row["id"]: row for row in traces}
    assert by_id["lookup"]["plan"]["subqueries"] == [{"text": "đối thoại", "purpose": "lookup"}]
    assert by_id["invalid_date"]["plan"]["temporal_scope"] == []
    assert by_id["leap_date"]["plan"]["temporal_scope"] == ["29/02/2024"]
    assert by_id["iso_date"]["plan"]["temporal_scope"] == ["2024"]
    assert by_id["base_duplicates"]["plan"]["subqueries"] == [{"text": "nghỉ phép", "purpose": "question_part"}] * 2
    assert by_id["tab_part"]["graph"]["exception_type"] == "ValidationError"
    assert by_id["tab_part"]["graph"]["retrieval_calls"] == 0
    first = {k: v for k, v in by_id["nfc"]["plan"].items() if k != "original"}
    second = {k: v for k, v in by_id["nfd"]["plan"].items() if k != "original"}
    assert first == second
    for row in traces:
        if "plan" in row and row["plan"]["clarification"]:
            assert row["graph"]["status"] == "CLARIFICATION_REQUIRED" and row["graph"]["retrieval_calls"] == 0
    coverage = sorted({line for row in traces for line in row["visited_lines"]})
    payload = {
        "understand_signature": str(inspect.signature(understand)),
        "case_count": len(traces),
        "traces": traces,
        "visited_understand_lines": coverage,
        "schema_probes": schema_checks(),
    }
    (OUT / "query-traces.json").write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    print("DIAGNOSTIC_CASES", len(traces), "EXECUTED_LINES", coverage)
    for name in ["punctuation", "tab_part", "bare_prefix", "iso_date", "zero_width", "multi_rule"]:
        row = by_id[name]
        print(json.dumps({"case": name, "plan": row.get("plan"), "graph": row["graph"]}, ensure_ascii=True))
