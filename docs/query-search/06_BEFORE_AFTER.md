# Before / candidate / final comparison

| Cohort | Cases | Accepted plans | API calls | Issue proxy* | Distinct-query proxy* | Fact spans* | Missing-info proxy* | Redundant cases* |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Deterministic all | 45 | 45 | 0 | 0.9365 | 0.7143 | 0.0769 | 0.1143 | 2 |
| Deterministic matched | 15 | 15 | 0 | 0.95 | 0.85 | 0.2273 | 0.3333 | 2 |
| Gemini baseline | 15 | 12 | 13 | 1.0 | 1.0 | 1.0 | 0.8 | 1 |
| Rejected candidate matched | 15 | 13 | 13 | 0.9412 | 0.7647 | 1.0 | 0.3636 | 0 |
| Final small | 6 | 5 | 6 | 0.8571 | 0.7143 | 1.0 | 0.0 | 0 |

All proxy columns are conditional on accepted plans; all failures remain separately visible. For unbiased quality claims use the same case IDs and include runtime failure rate. These synthetic questions are not representative of all Vietnamese law.

## Structural/runtime comparisons on matched cases

- Baseline full selected cohort: 12/15 accepted. Candidate on the same IDs: 13/15; one guard failure Q037 and one HTTP429 Q043. Broad prompt candidate was rejected because other quality dimensions regressed.
- Final versus baseline on exactly ['Q004', 'Q007', 'Q016', 'Q025', 'Q037']: baseline 2/5; final 4/5. Previously accepted Q004/Q037 remain accepted, Q007/Q016 recover, Q025 remains rejected (a different temporal error). This is a small targeted cohort, **not a full 15-case final re-evaluation**.
- Final additional Q044: accepted. Candidate additional Q002/Q005/Q008/Q017/Q026: accepted but decomposition/missing-info weaknesses remained. They cannot be combined into one same-prompt blind holdout statistic.
- Deterministic 45 before/after plans identical: **True**. No deterministic implementation changed.

## Semantic and retrieval conclusions

Fact span coverage among accepted plans stayed high; that includes guard selection effects. Required missing-information and distinct-objective proxies fell in the candidate and remain limited in the final small sample. Zero accepted ungrounded fact spans is an enforced condition, not a general hallucination score. Exact citation repair passes deterministic regression; live Q025 remains blocked and must not be called fixed end-to-end.

All four real retrieval modes returned evidence after separately measured local initialization. Hash/provenance checks passed. The labour BM25 lexical proxy was 0/2 deterministic versus 1/2 with Gemini; the consumer final case was 0/2. No expert relevance judgments exist, so **this task does not establish that semantic planning improves overall retrieval relevance, recall or legal correctness**. It establishes real connectivity, contract/provenance correctness on tested paths, known failures and a reproducible evaluation method.

Latency is in each raw run. API cold startup and local model initialization differ across executions, so reduced warm timings are not credited to Query improvements. Total observed Gemini attempts: 37; reported tokens: 25131; cost unknown.

Machine-readable comparison: `evaluation/query_search/summary.json`. Scoring rules/dataset were unchanged. Historical candidate results are not labelled as results of the final production prompt.
