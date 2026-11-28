# Native Judge → Summary integration

Branch: feature/query-search-judge-summary-integration. Base: cba277c.
Judge commits: 32a0df6 (core/adapter), 202a16d (Gemini/stage tracing).
Worktree remains `D:\Trang\TilLegal (Legal AI)\tillegal-judge-native-adapter`:
`git worktree move` to tillegal-query-search-judge-summary failed with Permission
denied on Windows. Git metadata and local .env/.venv/artifacts remain intact.
Branch rename succeeded. No folder recreation or .env modification was performed.

## Python boundary

```python
from src.applications.tillegal.agents.response.adapter import adapt_judge
from src.applications.tillegal.agents.response.agent import SummaryAgent, FixtureSummaryProvider

# native_judge_result: existing NativeJudgeResult, not Judge output alone.
value = adapt_judge(native_judge_result)
provider = FixtureSummaryProvider({
    "units": [], "limitations": ["Mock replay; không đánh giá ngữ nghĩa."],
    "abstain": True,
})
draft = SummaryAgent(provider).summarize(value)
```

Adapter revalidates Judge input/output, reprojects saved native SearchState through
the pure Judge adapter and compares maps/native context. This does not rerun search.
Question, scope, issue/evidence IDs and trusted date must match. Carrier payload is
detached; no mutation. No revision/Verify input yet: initial draft_version=1 only.

Input v2: schema_version, carrier (adapted + judge_result + telemetry), request_id,
question, query_plan.issues, as_of_date, draft_version, stop_reason,
previous_draft=null, verification_report=null, judge_result (checked identical copy).
Request is bounded to 2 MB by default; model prompt 100 KB including output schema;
output 24000 characters. SummaryLimits retains the old configurable bounds.

Only usable evidence content is passed to model, with Judge issue checks/gaps.
Query associations are retrieval intent, not proof of support. No legacy bundle,
quote renaming, fabricated groups/omissions/locators/article/version. Empty
context_gaps means unavailable context expansion, not complete legal context.

Output keeps answer_draft, claims, citations, draft_version, limitations, status,
request_id/as_of_date/stop_reason/error. Native representation uses schema_version=2:
citations carry content/content_sha256/content_representation instead of pretending
legacy quote/bundle/locator invariants. URLs/source fields are copied by code from
native metadata; document_version_id and exact_citation_verified remain null.
Claims have code-owned C/R IDs, issue_ids, citation_ids and origin=draft. Public
rendering/reference checks run; semantic claim support still requires future Verify.
Issue reports preserve Judge coverage; display_response includes limitations.

SUFFICIENT → draft; INSUFFICIENT + usable → source statements/partial draft or
abstention; partial issues reject application statements. No usable → abstention
without model. Judge ERROR → SUMMARY_JUDGE_ERROR without Summary model. Invalid
carrier/model JSON/IDs/URLs/markers/mapping → ERROR, never legal conclusions.

## Providers / scripts

Gemini Summary subclasses bounded LiveGeminiJudge transport, overriding output_schema
with LLM_OUTPUT_SCHEMA (units/limitations/abstain). Shared wire projection strips
unsupported constraints; Python retains full validation. No fallback/retry. Same
GOOGLE_API_KEY; SUMMARY_GEMINI_MODEL overrides saved Judge telemetry model.
Timeout 90 seconds; synchronous generate cannot be forcibly cancelled.

Run Summary only (new output directory required, no calls to first three stages):

```powershell
Set-Location 'D:\Trang\TilLegal (Legal AI)\tillegal-judge-native-adapter'
& '.\.venv\Scripts\python.exe' scripts/run_live_summary.py `
  --artifacts 'outputs/live-20261128-180301' `
  --judge-dir 'outputs/live-20261128-180301/judge-rerun-20261128-180753' `
  --env-file '.env' --out 'outputs/summary-replay-new'
```

Optional four-agent sequential live script (not LangGraph; may make paid calls):

```powershell
$repo = (Get-Location).Path
& '.\.venv\Scripts\python.exe' scripts/run_live_query_search_judge.py `
  --repo $repo --env-file "$repo\.env" `
  --question 'Công trình nhà ở tại khu vực nguy cơ sạt lở cần lưu ý gì?' `
  --as-of-date '2026-11-28' --out 'outputs/four-agents-new' --with-summary
```

No migration/crawler/database writes. Search is read-only. Scripts refuse existing
output folder. JSON UTF-8. outputs/ is ignored; no live payload is committed.

## Evidence and limitations

One live Summary call succeeded using unchanged successful judge-rerun artifacts:
outputs/summary-live-20261128-native-01; model gemini-3.5-flash-lite;
DRAFT_UNVERIFIED, 3 claims/3 citations. No new Query/Search/Judge calls.
Token usage/money cost not exposed by current transport. No claim that the corpus
belongs to a particular crawl date. No human/legal quality validation or Verify.
Stored live artifacts precede final additive citation-date/limitation formatting;
core/schema/provider logic is the same; no further paid rerun was made.

Full regression: python -m pytest -q → 810 passed in 22.65s (17 new Summary tests).
Includes transport wire schema/safe errors, adapter immutability/identity, unknown
metadata, usable-only payload, error/abstain/partial, ID/URL/marker/mapping rejection,
version/limits/timeout and Query/Search/Judge regression. CLI --help verified for
both scripts. Four-agent live E2E not executed; no quality claim inferred from mocks.

Future orchestrator owner must preserve carrier scope, time/history and model
timeouts, choose routing/budgets and eventual Verify. No LangGraph/state/startup/API,
Verify/Faith-Search/search-loop/retry-controller or crawler/schema/retrieval change.
