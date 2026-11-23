"""Read-only verification of A/B inputs and audit artifacts; writes only final evidence."""

import ast
import hashlib
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from dotenv import dotenv_values

A = Path.cwd()
OUT = A / ".docs/agent-development/task-06c-query-implementation-selection"
EVIDENCE = OUT / "evidence"
BASE = json.loads((EVIDENCE / "baseline.json").read_text(encoding="utf-8"))
RESULT = EVIDENCE / "final-verification.json"
if not RESULT.exists():
    RESULT.touch()
roots = {label: Path(root) for label, root in BASE["roots"].items()}
deltas = {}
for label, root in roots.items():
    expected = BASE["files"][label]
    changed = [
        name
        for name, digest in expected.items()
        if not (root / name).is_file() or hashlib.sha256((root / name).read_bytes()).hexdigest() != digest
    ]
    inventory = set()
    for directory in ("src", "tests", "configs", ".docs/agent-development", ".docs/development/query-search-design"):
        for file in (root / directory).rglob("*"):
            if file.is_file() and "__pycache__" not in file.parts and file.suffix != ".pyc" and OUT not in file.parents:
                inventory.add(file.relative_to(root).as_posix())
    inventory.update(name for name in ("pyproject.toml", "uv.lock") if (root / name).is_file())
    deltas[label] = {
        "baseline_files": len(expected),
        "changed": changed,
        "added_outside_audit": sorted(inventory - set(expected)),
        "missing": sorted(set(expected) - inventory),
    }

env = {**os.environ, "GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0"}
B = roots["B"]
git_after = {}
for args in [
    ("rev-parse", "HEAD"),
    ("branch", "--show-current"),
    ("status", "--porcelain=v1", "--untracked-files=all"),
    ("diff", "--cached", "--name-only"),
]:
    result = subprocess.run(
        ["git", "--no-optional-locks", "-C", str(B), *args], env=env, capture_output=True, timeout=20
    )
    git_after[" ".join(args)] = result.stdout.decode("utf-8", errors="replace")
git_unchanged = git_after == BASE["B_git_before"]
links = []
broken = []
for file in OUT.glob("*.md"):
    prose = re.sub(r"```[\s\S]*?```|`[^`\n]+`", "", file.read_text(encoding="utf-8"))
    for match in re.finditer(r"\[[^\]\n]+\]\(([^)]+)\)", prose):
        target = match.group(1).strip().strip("<>")
        if "://" in target or target.startswith("#"):
            continue
        links.append((file.name, target))
        if not (file.parent / target).resolve().exists():
            broken.append((file.name, target))
symbols = json.loads((EVIDENCE / "source-symbols.json").read_text(encoding="utf-8"))
cache = {}
symbol_errors = []
for row in symbols:
    key = (row["implementation"], row["file"])
    if key not in cache:
        tree = ast.parse((roots[key[0]] / key[1]).read_text(encoding="utf-8"))
        cache[key] = {
            (node.name, node.lineno, node.end_lineno)
            for node in ast.walk(tree)
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        }
    if (row["symbol"], row["start"], row["end"]) not in cache[key]:
        symbol_errors.append(row)
counts = {}
for label, file in [("A", "A-regression.xml"), ("B", "B-query-unit.xml")]:
    tree = ET.parse(EVIDENCE / file).getroot()
    counts[label] = {
        key: sum(int(node.get(key, "0")) for node in tree.iter("testsuite"))
        for key in ("tests", "failures", "errors", "skipped")
    }
obs = json.loads((EVIDENCE / "comparison-observations.json").read_text(encoding="utf-8"))
manifest = json.loads((EVIDENCE / "publication-manifest.json").read_text(encoding="utf-8"))
manifest_errors = [
    row["path"]
    for row in manifest["files"]
    if hashlib.sha256((A / row["path"]).read_bytes()).hexdigest() != row["source_sha256"]
]
secret_values = set()
for root in roots.values():
    if (root / ".env").is_file():
        for key, value in dotenv_values(root / ".env").items():
            if value and len(value) >= 12 and re.search(r"KEY|TOKEN|SECRET|PASSWORD", key, re.I):
                secret_values.add(value)
secret_hits = []
for file in OUT.rglob("*"):
    if file.is_file() and file.suffix in {".md", ".json", ".py", ".xml"}:
        content = file.read_text(encoding="utf-8", errors="replace")
        if any(value in content for value in secret_values):
            secret_hits.append(file.relative_to(OUT).as_posix())
checks = {
    "source_and_prior_reports_unchanged": all(
        not d["changed"] and not d["added_outside_audit"] and not d["missing"] for d in deltas.values()
    ),
    "B_head_branch_status_index_unchanged": git_unchanged,
    "all_links_resolve": not broken,
    "all_symbol_ranges_match": not symbol_errors,
    "A_320_pass": counts["A"] == {"tests": 320, "failures": 0, "errors": 0, "skipped": 0},
    "B_27_pass": counts["B"] == {"tests": 27, "failures": 0, "errors": 0, "skipped": 0},
    "A_six_fields_B_twenty_two": len(obs["A_fields"]) == 6 and len(obs["B_fields"]) == 22,
    "B_rejected_before_retrieval": obs["compatibility"]["B_dump_to_A_Search"]["accepted"] is False
    and obs["compatibility"]["B_dump_to_A_Search"]["retrieval_calls"] == 0,
    "A_clarification_zero_calls": obs["compatibility"]["A_clarification_Search"]["retrieval_calls"] == 0,
    "twelve_publication_files_unchanged": len(manifest["files"]) == 12 and not manifest_errors,
    "no_known_configured_secrets_found": not secret_hits,
}
report = {
    "selected": "A",
    "date_local": "2026-11-22",
    "timezone": "Asia/Saigon",
    "passed": all(checks.values()),
    "checks": checks,
    "inventory_deltas": deltas,
    "B_git_after": git_after,
    "local_links_checked": len(links),
    "broken_links": broken,
    "symbols_verified": len(symbols),
    "symbol_errors": symbol_errors,
    "tests": counts,
    "paired_cases": len(obs["cases"]),
    "B_control_cases": len(obs["B_control_cases"]),
    "publication_manifest_errors": manifest_errors,
    "configured_secret_hit_files": secret_hits,
    "limits": [
        "Secret check uses exact configured key/token/secret/password values >=12 chars, not universal detection",
        "No live DB/model execution; no Git write, transfer or implementation changes",
        "Inventory excludes cache/bytecode and new audit outputs",
    ],
}
RESULT.write_text(json.dumps(report, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, ensure_ascii=True, indent=2))
sys.exit(not report["passed"])
