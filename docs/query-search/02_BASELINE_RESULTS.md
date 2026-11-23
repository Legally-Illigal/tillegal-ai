# Baseline: deterministic versus real Gemini

No prompt optimization occurred before these runs. Baseline prompt SHA-256: `b47b64e0c5791e58a0600701b49c6576c30440cadbab46223b954078442df2c1`. Model `gemini-3.5-flash-lite`, timeout 30.0 seconds. Source/date/corpus applicability is not judged by this benchmark.

| Cohort | Cases | Accepted plans | API calls | Issue proxy* | Distinct-query proxy* | Fact spans* | Missing-info proxy* | Redundant cases* |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Deterministic all | 45 | 45 | 0 | 0.9365 | 0.7143 | 0.0769 | 0.1143 | 2 |
| Deterministic matched | 15 | 15 | 0 | 0.95 | 0.85 | 0.2273 | 0.3333 | 2 |
| Gemini baseline | 15 | 12 | 13 | 1.0 | 1.0 | 1.0 | 0.8 | 1 |
| Rejected candidate matched | 15 | 13 | 13 | 0.9412 | 0.7647 | 1.0 | 0.3636 | 0 |
| Final small | 6 | 5 | 6 | 0.8571 | 0.7143 | 1.0 | 0.0 | 0 |

\* Coverage/quality columns are accepted-plan heuristic/span checks; see design. The first two deterministic rows are different cohorts and must not be confused.

Deterministic returned 45/45 valid plans. Gemini baseline returned 12/15: 10 llm plans, two deterministic short circuits, three guard failures. 12 of 13 raw model JSON responses passed the SemanticAnalysis schema; two of those were then rejected for incompatible intent. Thus JSON success is distinct from execution success.

| ID | Category | Baseline status | Facts matched/expected | Distinct objectives matched/expected | Missing-info matched/expected | Error |
| --- | --- | --- | --- | --- | --- | --- |
| Q001 | single_issue | OK | 0/0 | 1/1 | 0/0 |  |
| Q004 | multi_issue | OK | 2/2 | 2/2 | 2/2 |  |
| Q007 | implicit_issue | ERROR | N/A | N/A | N/A | QUERY_ANALYSIS_INVALID_RESPONSE |
| Q010 | missing_information | OK | 1/1 | 1/1 | 3/3 |  |
| Q013 | ambiguous_intent | OK | 0/0 | 0/0 | 1/1 |  |
| Q016 | explicit_date | ERROR | N/A | N/A | N/A | QUERY_ANALYSIS_INVALID_RESPONSE |
| Q019 | historical_context | OK | 1/1 | 1/1 | 1/1 |  |
| Q022 | exact_citation | OK | 0/0 | 1/1 | 0/0 |  |
| Q025 | citation_verification | ERROR | N/A | N/A | N/A | QUERY_ANALYSIS_INVALID_RESPONSE |
| Q028 | exceptions_conditions | OK | 0/0 | 1/1 | 0/0 |  |
| Q031 | long_conversation | OK | 4/4 | 2/2 | 0/0 |  |
| Q034 | irrelevant_details | OK | 1/1 | 1/1 | 0/1 |  |
| Q037 | numerical_facts | OK | 3/3 | 1/1 | 0/1 |  |
| Q040 | multiple_subjects | OK | 2/2 | 2/2 | 1/1 |  |
| Q043 | already_supplied | OK | 3/3 | 2/2 | 0/0 |  |

Baseline model usage: {'prompt_tokens': 4326, 'completion_tokens': 2880, 'total_tokens': 7206}; median case latency 1716.99 ms; p95 nearest rank 5621.16 ms. No dollar cost estimated. Original question remains in every accepted plan. Zero ungrounded fact spans in accepted plans is enforced by guards, not proof of absence of all hallucinations in issues/subqueries.

Full per-case facts, raw model text, category-level metrics and error details: `evaluation/query_search/runs/deterministic-before.json` and `gemini-before.json`. Scoring terms are authored, not expert relevance annotations. A score of 1.0 among accepted Gemini cases does not hide the three rejected cases.
