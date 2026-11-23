# Final matched comparison and regression characterization

Same immutable45-case ground truth and existing scoring terms. Historical baseline artifact hash/dataset/prompt remain available. Current planner was sent all original15 baseline cases, plus Q005/Q044 and previously unevaluated Gemini cases Q006/Q018/Q042. No ground truth/aliases were changed after observing results.

Historical Gemini accepted **12/15**; current first attempt for each matched case accepted **13/15** (Q007 grounding failure, Q037 HTTP429). One documented bounded rate-limit continuation yields **14/15** accepted. Both attempts remain in attempt_history; the retry is not hidden. All20 selected cases yield19 accepted; the5 additional cases all accepted. Acceptance is not legal correctness.

| Check (failures=zero) | Historical Gemini15 | Current Gemini15 | Deterministic same15 |
| --- | --- | --- | --- |
| issue_matches | 15/20 | 17/20 | 19/20 |
| distinct_objective_matches | 15/20 | 17/20 | 17/20 |
| fact_matches | 17/22 | 20/22 | 5/22 |
| missing_info_matches | 8/12 | 7/12 | 4/12 |
| temporal_matches | 1/3 | 3/3 | 3/3 |
| citation_matches | 2/4 | 4/4 | 4/4 |

Denominators include failed plans as zero. These are still authored span/term proxies, not expert semantic scores. Deterministic preserves original even where facts-field coverage is low. Do not infer that Gemini is overall better: it accepts fewer plans and loses some keyword/objective coverage relative to deterministic; missing-info proxy also regresses against the historical Gemini baseline.

| ID | Historical status | Current status | Outcome |
| --- | --- | --- | --- |
| Q001 | OK | OK |  |
| Q004 | OK | OK |  |
| Q007 | ERROR | ERROR | QUERY_ANALYSIS_INVALID_RESPONSE |
| Q010 | OK | OK |  |
| Q013 | OK | OK |  |
| Q016 | ERROR | OK |  |
| Q019 | OK | OK | NEGATED_TEMPORAL_REFERENCE_IGNORED |
| Q022 | OK | OK |  |
| Q025 | ERROR | OK | MODEL_REFERENCE_RECLASSIFIED |
| Q028 | OK | OK |  |
| Q031 | OK | OK |  |
| Q034 | OK | OK |  |
| Q037 | OK | OK |  |
| Q040 | OK | OK |  |
| Q043 | OK | OK |  |

## What actually improved / remains inconclusive

- Verified: Q025's document-as-time case is accepted with the literal reference retained, no applicability date invented. Q016 event dates remain. Q019 negated current-time reference is excluded by final deterministic postprocessing. Novel/unsupported dates remain rejected.
- Verified in targeted cases: Q004 queries retain shared numerical context; Q005 has two separate custody/property objectives; Q040 retains separate loan/guarantee mapping. A one-to-one keyword proxy does not decide whether each shared search is semantically adequate.
- Not resolved: Q007's primary response has a punctuation grounding mismatch. Its separate repeat passes, demonstrating variability rather than a stable fix. The repeat does not replace the primary failure.
- Not resolved: missing-information completeness across domains. The matched proxy is7/12 versus historical8/12, even though narrow known-duration consistency is tested. No global quality claim follows from higher acceptance.
- Relevance: zero expert labels. Nineteen assistant-provisional rank-one judgments identify weak targeting, but no expert ranking metrics or overall retrieval superiority are claimed.

## Live versus replay

Gemini raw outputs are real API results. After Q019 exposed a negation error, the final deterministic postprocessor was rerun on those immutable outputs to derive matched.json, marked SAVED_RAW_FINAL_CODE_REPLAY_NO_API. Original API plans/statuses are retained in gemini.json/gemini-resume.json. The correction does not change the provider prompt/hints for these cases; it is a postprocessing fix, not a fresh provider run for every row.

The separate variability sample Q007/Q025 accepted2/2. It is too small to estimate general reliability. There were **21** new Gemini invocations, under the25 cap; reported usage **14335** tokens. One429 is preserved; no dollar cost is invented. Latencies remain per attempt, including cold SDK startup. No speed improvement is claimed.

Offline reproduction without more API quota:

```powershell
.\.venv\Scripts\python.exe -m scripts.validate_query_semantics --mode summarize
.\.venv\Scripts\python.exe -m scripts.validate_query_semantics --mode replay
```

The persistent budget ledger now has21 attempts. New live batches must fit remaining budget before any request; no automatic reset. Derived summaries may be regenerated, raw result files cannot be overwritten by the evaluator.

## Causal attribution caution

The historical15-case baseline predates some earlier intent-schema fixes. This task did not spend another15 calls on an old-code control. Same IDs/rules support a historical matched comparison, not attribution of the entire12→14 difference to the new changes. Stronger mechanism-specific evidence is identical saved Q025 raw JSON changing from rejection to correctly audited reclassification, plus a new live Q025 response of the same erroneous temporal kind being handled. Missing-info/decomposition metrics and provider variability remain inconclusive in places.
