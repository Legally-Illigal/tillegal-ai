"""Complete rule coverage using the existing read-only diagnostic functions."""

import asyncio
import json
import runpy
from pathlib import Path

ROOT = Path(".docs/agent-development/task-06a-query-knowledge-handoff/evidence")
ns = runpy.run_path(str(ROOT / "diagnose_query.py"))
payload = json.loads((ROOT / "query-traces.json").read_text(encoding="utf-8"))
extra_cases = [
    ("annual_leave", "Quy định nghỉ hằng năm ra sao?"),
    ("termination", "Tôi cần biết về chấm dứt hợp đồng lao động?"),
    ("lookup_find", "Tìm đoạn: thời giờ làm việc"),
    ("ambiguous_ref", "Như vậy đúng không?"),
    ("ambiguous_case", "Trường hợp này"),
    ("year_1999", "Quy định năm 1999"),
    ("future_year", "Quy định năm 2100"),
    ("newline_parts", "Quy định thuế" + chr(10) + "Quy định nghỉ phép"),
    ("invalid_and_year", "Quy định ngày 31/02/2024 và năm 2020"),
    ("single_lookup", "Trích dẫn: thuế"),
]
for name, question in extra_cases:
    row = ns["diagnose"](question)
    row.update(id=name, input=question, graph=asyncio.run(ns["graph_probe"](question)))
    payload["traces"].append(row)
payload["case_count"] = len(payload["traces"])
payload["visited_understand_lines"] = sorted({line for row in payload["traces"] for line in row["visited_lines"]})
observed_topics = {match["group"].casefold() for row in payload["traces"] for match in row["raw_topic_matches"]}
expected_topics = {
    "đối thoại định kỳ",
    "nghỉ hằng năm",
    "nghỉ phép",
    "thời giờ làm việc",
    "chấm dứt hợp đồng lao động",
    "tiền lương",
    "làm thêm giờ",
}
assert expected_topics <= observed_topics
payload["all_seven_topic_rules_observed"] = True
out = ROOT / "query-traces-complete.json"
assert not out.exists()
out.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
print("COMPLETE_CASES", payload["case_count"], "SEVEN_TOPICS_OBSERVED", True)
