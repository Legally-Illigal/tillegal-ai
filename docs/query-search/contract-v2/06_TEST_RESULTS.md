# Acceptance test results

Executed 2026-11-27. **43 V2 cases PASS**: the original 34 cases plus nine acceptance cases. No production blocker was demonstrated; both production modules remain byte-identical to the reviewed foundation. No old assertions, V1 production, prompts or Retrieval algorithms changed.

The publication candidate is an isolated worktree based on `origin/main` at `9517bb597bad5eca56eb211b7bf59cf2493d48f8`. Tests execute its own source paths using the existing development virtualenv.

|Check|Clean publication candidate|Original development directory|
|---|---|---|
|V2|43 passed|43 passed|
|Query/Search + graph|648 passed|621 passed|
|Full pytest|754 passed|710 passed|
|Ruff lint|All repository files PASS|Only changed V2 files checked separately|
|Ruff format|Three changed Python files PASS|Three changed Python files PASS|
|Imports|V1 bootstrap, V2 and graph PASS; candidate source paths asserted|PASS|
|Dependencies|All 13 declared runtime/dev requirements satisfied; pyproject.toml and uv.lock unchanged|Existing environment reused|

Test denominators differ because the development directory remains on its older feature baseline with unrelated local work. Historical 701/711 counts are not used as current publication evidence. No hosted Gemini requests, Supabase writes, model downloads or dependency installation were performed. All provider calls are mocked; retrieval uses controlled in-memory ports.

## Focused evidence

- Gemini factory call arguments compare exactly: model, messages, structured schema, token/timeout/retry/log parameters and call count. V1 and V2 return the same QueryPlan.
- Controlled native responses enable exact equality of every SearchState field and RetrievalRequest sequence for success, no-match, classified partial failure and timeout, including warnings/errors, native scores, provenance and skipped queries. Only clocks/UUIDs for synthetic timeout outcomes are fixed to make independent runs comparable.
- Actual Gemini adapter timeout/provider/invalid-schema failure paths have identical safe error types/messages, one call, no deterministic fallback and no retrieval.
- Explicit graph seam regression proves QuerySearchNodes.query still uses deterministic understand even when a semantic agent is present.
- Explicit `Trích dẫn: thuế` regression retains V1 lookup while V2 labels retrieval find_support/unresolved; no exact resolver result is fabricated.
- Original cases cover scoped/unissued/dangling references, grounded spans, date/policy checks before I/O, immutable identity bindings, multiple targets/purposes, duplicate-query provenance, conflicting versions, partial/skipped execution, unavailable capabilities and all native subtype JSON roundtrips.

## Exact clean-candidate commands and observed results

Run from `D:\DOWNLOAD\tmp\tillegal-contract-v2-publish-20261127`. `python` below is the existing `D:\DOWNLOAD\tillegal-ai\tillegal-ai-main\.venv\Scripts\python.exe`.

### v2

```text
python -m pytest tests/unit/applications/tillegal/test_contract_v2.py -q -p no:cacheprovider
Exit code: 0
...........................................                              [100%]
43 passed in 2.06s
```

### focused

```text
python -m pytest tests/unit/applications/tillegal tests/graph/test_query_search_workflow.py -q -p no:cacheprovider
Exit code: 0
........................................................................ [ 88%]
........................................................................ [100%]
648 passed in 19.03s
```

### full

```text
python -m pytest -q -p no:cacheprovider
Exit code: 0
........................................................................ [ 95%]
..................................                                       [100%]
754 passed in 19.49s
```

### ruff

```text
python -m ruff check --no-cache .
Exit code: 0
All checks passed!
```

### format

```text
python -m ruff format --check src/applications/tillegal/agents/contract_v2.py src/applications/tillegal/agents/pipeline_v2.py tests/unit/applications/tillegal/test_contract_v2.py
Exit code: 0
3 files already formatted
```

### imports

```text
python -c "from pathlib import Path; import src.query_search_bootstrap as b; import src.applications.tillegal.agents.pipeline_v2 as v; from src.applications.tillegal.graphs.legal_qa import QuerySearchNodes; assert Path(b.__file__).resolve().is_relative_to(Path.cwd()); assert Path(v.__file__).resolve().is_relative_to(Path.cwd()); print(\"Candidate V1 bootstrap / V2 / graph imports PASS; source paths verified\")"
Exit code: 0
Candidate V1 bootstrap / V2 / graph imports PASS; source paths verified
```

### dependencies

```text
python -c "import tomllib,importlib.metadata as m; from packaging.requirements import Requirement; from pathlib import Path; p=tomllib.loads(Path(\"pyproject.toml\").read_text()); reqs=[Requirement(x) for x in p[\"project\"][\"dependencies\"]+p[\"dependency-groups\"][\"dev\"]]; bad=[r.name for r in reqs if (r.marker is None or r.marker.evaluate()) and m.version(r.name) not in r.specifier]; assert not bad,bad; print(f\"All {len(reqs)} declared runtime/dev requirements satisfied; dependency files unchanged\")"
Exit code: 0
All 13 declared runtime/dev requirements satisfied; dependency files unchanged
```

## Publication boundary

The commit allowlist is two new production modules, one new test module and nine V2 documentation/example files (12 files total). The final publication report `08_FINAL_ACCEPTANCE_AND_PUBLICATION.md` is generated after the commit and explicitly identified as local-only. Historical audits, the local team-decision record, old Git reports and all unrelated dirty files are excluded.
