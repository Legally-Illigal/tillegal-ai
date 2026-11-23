# Final acceptance scope and inventory

- 444 original files under src/scripts/tests/configs/docs/evaluation remain SHA-256 identical; no deletion.
- No production Query/Search/provider/prompt/retrieval/config/graph/other-agent/corpus/crawler/schema changes.
- No dependency/model installation, no new Gemini or Supabase call. No full evaluation regeneration or human-label edits.
- Current578 focused /667 full tests PASS; Ruff check/format PASS17 files.
- Current public-entry fixture/replay verification:5 states +4 errors. Documented standalone example executed; live snippets syntax-checked only.
- Native subtype JSON serialization/restoration probe PASS with serialize_as_any=True; default omission documented. Manual-plan span-boundary limitation documented, not fixed.
- No Git metadata; branch/HEAD unavailable. No commit/push/merge/rebase/PR.
- Exact credential-value scan and report-link checks PASS.

## Runtime versions

```json
{
  "python": "3.12.16 (main, Oct 26 2026, 14:10:56) [MSC v.1944 64 bit (AMD64)]",
  "pydantic": "2.14.1",
  "litellm": "1.106.4",
  "supabase": "2.33.0",
  "python-dotenv": "1.2.4",
  "PyYAML": "6.0.3",
  "sentence-transformers": "5.7.0",
  "transformers": "5.22.2",
  "torch": "2.15.0",
  "pytest": "8.4.2",
  "ruff": "0.17.2"
}
```

## New files

- `docs/query-search/final-handoff/00_README.md`
- `docs/query-search/final-handoff/01_FINAL_ARCHITECTURE.md`
- `docs/query-search/final-handoff/02_QUERY_AGENT_INTERNALS.md`
- `docs/query-search/final-handoff/03_SEARCH_AGENT_INTERNALS.md`
- `docs/query-search/final-handoff/04_INPUT_OUTPUT_CONTRACTS.md`
- `docs/query-search/final-handoff/05_INTEGRATION_GUIDE.md`
- `docs/query-search/final-handoff/06_TEST_ACCEPTANCE.md`
- `docs/query-search/final-handoff/07_LIMITATIONS_AND_OWNERSHIP.md`
- `docs/query-search/final-handoff/08_TECHNICAL_DEFENSE_VI.md`
- `docs/query-search/final-handoff/09_HANDOFF_SUMMARY.md`
- `docs/query-search/final-handoff/SCOPE_REVIEW.md`
- `evaluation/query_search/final_acceptance/baseline_manifest.json`
- `evaluation/query_search/final_acceptance/checks.json`
- `evaluation/query_search/final_acceptance/contract_probes.json`
- `evaluation/query_search/final_acceptance/documentation_examples.json`
- `evaluation/query_search/final_acceptance/evidence_reconciliation.json`
- `evaluation/query_search/final_acceptance/execution.json`
- `evaluation/query_search/final_acceptance/scope_report.json`
- `evaluation/query_search/final_acceptance/serialization_probe.json`
- `scripts/verify_query_search_handoff.py`
