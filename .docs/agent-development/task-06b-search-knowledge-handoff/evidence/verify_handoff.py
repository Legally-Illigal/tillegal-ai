"""Offline quality audit for new Task6B documentation; never mutates application files."""

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

from src.applications.tillegal.agents.query.agent import QueryPlan
from src.applications.tillegal.agents.search.agent import SearchOptions, SearchState, search
from src.applications.tillegal.graphs.legal_qa import QuerySearchNodes
from src.applications.tillegal.state.legal_qa_state import JudgeHandoff
from src.query_search_bootstrap import QuerySearch

ROOT = Path.cwd()
OUT = ROOT / ".docs/agent-development/task-06b-search-knowledge-handoff"
EVIDENCE = OUT / "evidence"
RESULT = EVIDENCE / "quality-checks.json"
# Materialize this new artifact before checking links which point to it.
if not RESULT.exists():
    RESULT.touch()
failures = []
base = json.loads((EVIDENCE / "baseline.json").read_text(encoding="utf-8"))
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
    failures.append("baseline_inventory_delta")

markdown = sorted(OUT.glob("*.md"))
expected_names = [
    "00_README.md",
    "01_SEARCH_ARCHITECTURE.md",
    "02_SEARCH_INPUT_CONTRACTS.md",
    "03_QUERYPLAN_VALIDATION.md",
    "04_SUBQUERY_EXECUTION.md",
    "05_RETRIEVAL_REQUEST_CONSTRUCTION.md",
    "06_RETRIEVAL_SERVICE_BOUNDARY.md",
    "07_SEARCH_OUTPUT_AND_EVIDENCE.md",
    "08_LANGGRAPH_SEARCH_NODE.md",
    "09_JUDGE_HANDOFF.md",
    "10_SOURCE_EXECUTION_TRACE.md",
    "11_OBSERVED_RUNTIME_EXAMPLES.md",
    "12_ERROR_AND_FAILURE_MATRIX.md",
    "13_BOOTSTRAP_AND_DEPENDENCIES.md",
    "14_TEST_MATRIX_AND_RESULTS.md",
    "15_RATIONALE_AND_LIMITATIONS.md",
    "16_PEDAGOGICAL_QA_AND_GLOSSARY.md",
    "17_ORAL_EXPLANATIONS.md",
    "18_SOURCE_SYMBOL_INDEX.md",
    "19_OPEN_QUESTIONS.md",
    "20_HANDOFF_FOR_DOCUMENT_AUTHOR.md",
]
if [file.name for file in markdown] != expected_names:
    failures.append("deliverable_names_mismatch")
links = []
broken_links = []
for file in markdown:
    prose = re.sub(r"```[\s\S]*?```|`[^`\n]+`", "", file.read_text(encoding="utf-8"))
    for match in re.finditer(r"(?<!!)\[[^\]\n]+\]\(([^)]+)\)", prose):
        target = match.group(1).strip().strip("<>")
        if "://" in target or target.startswith("#"):
            continue
        links.append((file.name, target))
        path = (file.parent / unquote(target.split("#")[0])).resolve()
        if not path.exists():
            broken_links.append((file.name, target))
if broken_links:
    failures.append("broken_markdown_links")

symbols = json.loads((EVIDENCE / "source-symbols.json").read_text(encoding="utf-8"))
symbol_errors = []
symbol_cache = {}
for row in symbols:
    if row["file"] not in symbol_cache:
        tree = ast.parse((ROOT / row["file"]).read_text(encoding="utf-8-sig"))
        symbol_cache[row["file"]] = {
            (node.name, node.lineno, node.end_lineno)
            for node in ast.walk(tree)
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        }
    if (row["symbol"].split(".")[-1], row["start"], row["end"]) not in symbol_cache[row["file"]]:
        symbol_errors.append(row)
if symbol_errors:
    failures.append("symbol_range_mismatch")
blocks = json.loads((EVIDENCE / "source-trace-blocks.json").read_text(encoding="utf-8"))
walkthrough = (OUT / "10_SOURCE_EXECUTION_TRACE.md").read_text(encoding="utf-8")
block_errors = []
for row in blocks:
    source = (ROOT / row["file"]).read_text(encoding="utf-8").splitlines()
    actual = "\n".join(source[row["start"] - 1 : row["end"]])
    if row["snippet"] != actual or "```python\n" + actual + "\n```" not in walkthrough:
        block_errors.append({key: row[key] for key in ("file", "start", "end")})
if block_errors or len(blocks) != 29:
    failures.append("source_snippet_mismatch")

observed = json.loads((EVIDENCE / "search-traces.json").read_text(encoding="utf-8"))
objects = {
    "search": search,
    "SearchOptions": SearchOptions,
    "QuerySearch.search": QuerySearch.search,
    "QuerySearchNodes.search": QuerySearchNodes.search,
    "JudgeHandoff.from_search": JudgeHandoff.from_search,
    "JudgeHandoff.validate_context": JudgeHandoff.validate_context,
}
signature_errors = [
    name for name, obj in objects.items() if str(inspect.signature(obj)) != observed["signatures"][name]
]
if signature_errors:
    failures.append("function_signature_mismatch")
contracts = {
    "QueryPlan": list(QueryPlan.model_fields),
    "SearchOptions": list(SearchOptions.model_fields),
    "SearchState": list(SearchState.__annotations__),
    "JudgeHandoff": list(JudgeHandoff.model_fields),
}
if contracts["QueryPlan"] != ["original", "intent", "domain", "temporal_scope", "subqueries", "clarification"]:
    failures.append("query_plan_contract")
if contracts["SearchState"] != ["plan", "requests", "responses", "status"]:
    failures.append("search_state_contract")
if not all(field.is_required() for field in SearchOptions.model_fields.values()):
    failures.append("search_options_required_contract")

cases = {row["id"]: row for row in observed["search_traces"]}
graphs = {row["id"]: row for row in observed["graph_traces"]}
checks = {
    "search_cases_35": len(cases) == len(observed["search_traces"]) == 35,
    "graph_invocations_9": len(graphs) == len(observed["graph_traces"]) == 9,
    "tab_prebuild_zero_calls": cases["tab_second"]["requests_observed"] == [],
    "clarification_zero_calls": cases["clarification"]["requests_observed"] == [],
    "duplicate_calls_two": len(cases["duplicate_calls"]["requests_observed"]) == 2,
    "multi_sequential": cases["multi_success"]["max_active_calls"] == 1,
    "partial_failure_prefix_two": len(cases["partial_failure"]["search_state"]["requests"]) == 2,
    "partial_failure_preserves_evidence": len(cases["partial_failure"]["search_state"]["responses"][0]["evidence"])
    == 2,
    "unexpected_exception_no_search_state": "search_state" not in cases["exception_second"],
    "direct_context_mismatch_packet_reject": cases["context_mismatch"]["handoff_exception"]["type"]
    == "ValidationError",
    "graph_context_mismatch_exception": graphs["graph_context_mismatch"]["exception"]["type"] == "ValidationError",
    "classified_failure_lifecycle_success": graphs["graph_failure"]["lifecycle"] == "succeeded",
    "graph_exception_lifecycle_failed": graphs["graph_exception"]["lifecycle"] == "failed",
    "all_profiles_roundtrip": all(
        graphs["graph_" + mode]["handoff_roundtrip_equal"] for mode in ("bm25", "dense", "hybrid", "rerank")
    ),
    "native_identity_all_returned": all(row.get("response_identity_preserved", True) for row in cases.values()),
    "plan_unchanged_all_cases": all(row["plan_unchanged"] for row in cases.values()),
}
if not all(checks.values()):
    failures.append("runtime_observation_inconsistent")
qa = (OUT / "16_PEDAGOGICAL_QA_AND_GLOSSARY.md").read_text(encoding="utf-8")
qa_count = len(re.findall(r"^### \d+\.", qa, re.M))
glossary_section = qa.split("## Glossary", 1)[1]
glossary_count = sum(line.startswith("|") for line in glossary_section.splitlines()) - 2
if qa_count < 45 or glossary_count < 30:
    failures.append("pedagogy_count")
junit = ET.parse(EVIDENCE / "focused-junit.xml").getroot()
suites = list(junit.iter("testsuite"))
test_counts = {
    key: sum(int(suite.get(key, "0")) for suite in suites) for key in ("tests", "failures", "errors", "skipped")
}
if test_counts != {"tests": 320, "failures": 0, "errors": 0, "skipped": 0}:
    failures.append("junit_count_mismatch")

# Compare exact known configured secret values in memory; do not print values or variable names.
secret_values = set()
if (ROOT / ".env").is_file():
    for key, value in dotenv_values(ROOT / ".env").items():
        if value and len(value) >= 12 and re.search(r"KEY|TOKEN|SECRET|PASSWORD", key, re.I):
            secret_values.add(value)
secret_hits = []
for file in OUT.rglob("*"):
    if file.is_file() and file.suffix in {".md", ".json", ".py", ".xml"}:
        content = file.read_text(encoding="utf-8", errors="replace")
        if any(value in content for value in secret_values):
            secret_hits.append(file.relative_to(OUT).as_posix())
if secret_hits:
    failures.append("configured_secret_found")

result = {
    "authority": str(ROOT),
    "completion_date_local": "2026-11-22",
    "timezone": "Asia/Saigon",
    "git_metadata_present": (ROOT / ".git").exists(),
    "baseline_files": len(base),
    "baseline_changed": changed,
    "baseline_added_in_monitored_scopes": added,
    "baseline_missing": missing,
    "baseline_sha256": hashlib.sha256((EVIDENCE / "baseline.json").read_bytes()).hexdigest(),
    "markdown_files": len(markdown),
    "local_links_checked": len(links),
    "broken_links": broken_links,
    "ast_symbols_verified": len(symbols),
    "symbol_errors": symbol_errors,
    "exact_source_blocks_verified": len(blocks),
    "source_block_errors": block_errors,
    "runtime_signatures_verified": len(objects),
    "signature_errors": signature_errors,
    "contracts": contracts,
    "runtime_observation_checks": checks,
    "qa_count": qa_count,
    "glossary_count": glossary_count,
    "focused_junit": test_counts,
    "configured_secret_scan_hit_files": secret_hits,
    "configured_secret_scan_scope": (
        "Exact configured .env key/token/secret/password values length >= 12; not universal secret detection"
    ),
    "failures": failures,
    "passed": not failures,
    "limits": [
        "Inventory excludes caches/bytecode and new Task6B outputs; not a full disk inventory",
        "Source/diagnostic branches inspected are not formal 100% coverage",
        "No Task6B live Supabase or real model inference; historical evidence labeled separately",
        "No Git init/commit/push commands invoked",
    ],
}
RESULT.write_text(json.dumps(result, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result, ensure_ascii=True, indent=2))
sys.exit(bool(failures))
