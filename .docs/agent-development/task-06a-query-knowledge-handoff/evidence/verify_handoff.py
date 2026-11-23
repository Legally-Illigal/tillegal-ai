"""Verify new handoff artifacts and unchanged authoritative checkout; offline only."""

import ast
import hashlib
import inspect
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import unquote

from dotenv import dotenv_values

from src.applications.tillegal.agents.query.agent import QueryPlan, Subquery, understand

ROOT = Path.cwd()
OUT = ROOT / ".docs/agent-development/task-06a-query-knowledge-handoff"
EVIDENCE = OUT / "evidence"
failures = []
base = json.loads((EVIDENCE / "baseline.json").read_text(encoding="utf-8-sig"))
changed = [
    name
    for name, digest in base.items()
    if not (ROOT / name).is_file() or hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest
]
current = set()
for directory in ("src", "tests", "configs", ".docs/agent-development"):
    for file in (ROOT / directory).rglob("*"):
        if file.is_file() and "__pycache__" not in file.parts and file.suffix != ".pyc" and OUT not in file.parents:
            current.add(file.relative_to(ROOT).as_posix())
current.update(("pyproject.toml", "uv.lock"))
added = sorted(current - set(base))
missing = sorted(set(base) - current)
if changed or added or missing:
    failures.append("baseline_delta")

markdown = sorted(OUT.glob("*.md"))
links = []
broken = []
for file in markdown:
    for match in re.finditer(r"(?<!!)\[[^\]\n]+\]\(([^)]+)\)", file.read_text(encoding="utf-8")):
        target = match.group(1).strip().strip("<>")
        if "://" in target or target.startswith("#"):
            continue
        path = (file.parent / unquote(target.split("#")[0])).resolve()
        links.append((file.name, target))
        if not path.exists():
            broken.append((file.name, target))
if broken:
    failures.append("broken_markdown_links")

symbols = json.loads((EVIDENCE / "source-symbols.json").read_text(encoding="utf-8"))
symbol_errors = []
for row in symbols:
    file = ROOT / row["file"]
    tree = ast.parse(file.read_text(encoding="utf-8-sig"))
    found = any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        and node.name == row["symbol"].split(".")[-1]
        and node.lineno == row["start"]
        and node.end_lineno == row["end"]
        for node in ast.walk(tree)
    )
    if not found:
        symbol_errors.append(row)
if symbol_errors:
    failures.append("ast_symbol_range_mismatch")

source_lines = inspect.getsource(understand).splitlines()
whole_source = (ROOT / "src/applications/tillegal/agents/query/agent.py").read_text(encoding="utf-8").splitlines()
trace_text = (OUT / "07_SOURCE_EXECUTION_TRACE.md").read_text(encoding="utf-8")
blocks = re.findall(r"## Dòng(\d+)–(\d+)\s+```python\n(.*?)\n```", trace_text, re.S)
block_errors = []
for start, end, snippet in blocks:
    expected = "\n".join(whole_source[int(start) - 1 : int(end)])
    if expected != snippet:
        block_errors.append((start, end))
if block_errors or len(blocks) != 12:
    failures.append("source_trace_snippet_mismatch")

signature = str(inspect.signature(understand))
plan_fields = list(QueryPlan.model_fields)
required_fields = {name: field.is_required() for name, field in QueryPlan.model_fields.items()}
if (
    signature != "(question: str) -> dict"
    or plan_fields != ["original", "intent", "domain", "temporal_scope", "subqueries", "clarification"]
    or not all(required_fields.values())
):
    failures.append("query_contract_mismatch")
traces = json.loads((EVIDENCE / "query-traces-complete.json").read_text(encoding="utf-8"))
ids = [row["id"] for row in traces["traces"]]
if len(ids) != 52 or len(set(ids)) != 52 or not traces["all_seven_topic_rules_observed"]:
    failures.append("trace_inventory_mismatch")
qa_text = (OUT / "13_PEDAGOGICAL_QA_AND_GLOSSARY.md").read_text(encoding="utf-8")
qa_count = len(re.findall(r"^## \d+\.", qa_text, re.M))
if len(markdown) != 18 or qa_count < 40:
    failures.append("documentation_count_mismatch")

junit = ET.parse(EVIDENCE / "focused-junit.xml").getroot()
suites = list(junit.iter("testsuite"))
test_counts = {
    key: sum(int(suite.get(key, "0")) for suite in suites) for key in ("tests", "failures", "errors", "skipped")
}
if test_counts != {"tests": 120, "failures": 0, "errors": 0, "skipped": 0}:
    failures.append("junit_mismatch")

# Check exact configured secrets in memory, without printing names or values.
secret_values = set()
for env_file in (ROOT / ".env",):
    if env_file.is_file():
        for key, value in dotenv_values(env_file).items():
            if value and len(value) >= 12 and re.search(r"KEY|TOKEN|SECRET|PASSWORD", key, re.I):
                secret_values.add(value)
secret_hit_files = []
for file in OUT.rglob("*"):
    if not file.is_file() or file.suffix not in {".md", ".json", ".py", ".xml"}:
        continue
    content = file.read_text(encoding="utf-8", errors="replace")
    if any(value in content for value in secret_values):
        secret_hit_files.append(file.relative_to(OUT).as_posix())
if secret_hit_files:
    failures.append("configured_secret_present")

result = {
    "authority": str(ROOT),
    "git_metadata_present": (ROOT / ".git").exists(),
    "baseline_files": len(base),
    "baseline_changed": changed,
    "baseline_added_in_monitored_scopes": added,
    "baseline_missing": missing,
    "markdown_files": len(markdown),
    "local_links_checked": len(links),
    "broken_links": broken,
    "ast_symbols_verified": len(symbols),
    "symbol_errors": symbol_errors,
    "exact_source_blocks_verified": len(blocks),
    "source_block_errors": block_errors,
    "understand_signature": signature,
    "query_plan_fields": plan_fields,
    "query_plan_required_fields": required_fields,
    "subquery_fields": list(Subquery.model_fields),
    "unique_diagnostic_cases": len(set(ids)),
    "all_seven_topics_observed": traces["all_seven_topic_rules_observed"],
    "qa_count": qa_count,
    "focused_junit": test_counts,
    "configured_secret_scan_hit_files": secret_hit_files,
    "configured_secret_scan_scope": (
        "Exact .env key/token/secret/password values with length >= 12; not universal secret detection"
    ),
    "failures": failures,
    "passed": not failures,
    "limits": [
        "Inventory excludes caches/bytecode and new Task6a artifacts; not a full disk inventory",
        "Source line visits are not formal branch coverage",
        "No live database/model/API execution; graph probes use FakeRetrieval",
        "No Git commands invoked to initialize, commit or push",
    ],
}
(EVIDENCE / "quality-checks.json").write_text(json.dumps(result, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result, ensure_ascii=True, indent=2))
sys.exit(bool(failures))
