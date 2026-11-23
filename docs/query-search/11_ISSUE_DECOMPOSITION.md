# Information needs, context and missing-information consistency

## Observations and selected changes

Saved Q005/Q040 candidate outputs compress several needs into a single issue/query; Q004 often loses duration/worked-time context in the query strings. A schema-valid response can therefore be too general. There was no evidence of max-token truncation in these stored successful responses; the provider finish guard already rejects non-stop/truncated output. Compression is not automatically a token-budget fault.

Do not split sentences or create a query for every keyword. Keep LegalIssue's existing issue/search_query structure, add an atomic-information-need description and a small instruction to avoid grouping every need merely because it shares a situation. This is not the prior rejected broad prompt: no blanket suppression of missing information is restored. No second model call or reasoning loop is added.

`SemanticQueryAgent.understand` preserves the model's issue sequence, deduplicates identical search strings and builds SearchObjective(query_index, issue_indices). Several issues may share a query; repeated issue labels may use different searches. Maximum four subqueries remains unchanged. Distinct-query proxy is retained for comparability, not imposed as a legal correctness rule.

Grounded shared scenario context is appended from exact fact spans, bounded to600 characters before extra supplied slots; legal-reference-containing allegations/questions are not promoted into scenario context. This keeps known duration/amount/party/event facts where the model has selected them. It may still add retrieval noise if the model selects irrelevant factual spans: relevance must be assessed separately.

## Missing information

`context.py::supplied_context` intentionally recognizes only three demonstrated employment slots: contract duration, explicit exit reason and certain explicit training-agreement expressions. It is not a comprehensive ontology. The model receives these literal spans as hints.

`reconcile_missing` removes a generic duration question when duration is supplied, but keeps compound questions about special terms/training. It similarly handles narrow reason/training repetitions. For explicit employee-exit questions, genuinely unknown reason/training may be added as optional follow-up questions. clarification remains the separate blocking field; these optional questions do not prevent searching general rules.

The8-item budget is retained; context/regex coverage remains limited. No inference that a training agreement exists, that the employee breached a contract, or that compensation is due is made. Q004's compound training question is deliberately retained even though an old keyword proxy flags “Loại hợp đồng”.

## Search association

`Search._finish` reads validated SearchObjective links and stores issue_indices in each EvidenceOccurrence beside subquery_index/response_index/query/request_id/rank/score. Old plans have empty mappings rather than fabricated associations. Deduplicated evidence can have occurrences from several objectives. Source payload keys, legal versions and native response order/scores remain unchanged.

Observed new Q005: two queries (custody/support and property), compared with one broad query in the rejected candidate. Q004 retains two needs with both two-year and six-month context. Q040 produced separate repayment/guarantee searches. These examples support the targeted behavior, not universal issue coverage. Some desired missing-information objectives remain absent in the full matched cohort.

See14_FINAL_COMPARISON.md for failure-inclusive scores and12_RELEVANCE_EVALUATION.md for actual source review. No claim that one query per expected keyword is always correct.
