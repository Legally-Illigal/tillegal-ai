# Query/Search quality validation: design and current audit

Date: 2026-11-23. Target: `D:/DOWNLOAD/tillegal-ai/tillegal-ai-main`. The target is an extracted tree with no `.git`; branch/HEAD are unknown. Existing useful documents and unrelated edits are preserved. No other worktree was used as this target's HEAD.

## Audit

| Source path | Relevant functions/current lines |
| --- | --- |
| src/applications/tillegal/agents/query/agent.py | understand:36–152 |
| src/applications/tillegal/agents/query/semantic.py | __call__:20–22; understand:42–111 |
| src/applications/tillegal/agents/query/gemini.py | create_gemini_query_agent:31–67 |
| src/framework/llm/providers/gemini_adapter.py | __call__:42–83 |
| src/applications/tillegal/agents/search/agent.py | _finish:55–115; search:118–177 |
| src/retrieval_bootstrap.py | create_retrieval_service:22–70 |
| src/application/services/retrieval_service.py | search:192–305; _read_and_validate_index:492–533 |
| src/integrations/database/repositories/rpc.py | call_rpc:21–27 |

The actual Query entry is `QuerySearch.search`: optional SemanticQueryAgent, then Search. `create_query_search(... semantic_mode="gemini")` activates the Gemini profile. Configured model and observed provider model are `gemini-3.5-flash-lite`, deadline 30 seconds, output budget 4096 tokens. The current graph still uses deterministic Query; it was not changed. No API values are in these reports.

QueryPlan fields: original, intent, domain, temporal_scope, subqueries, clarification, analysis_method, analysis_model, facts, issues, missing_information. Domain is only labour/unknown: other domains are exercised through semantic text, not a new classifier. Search accepts QueryPlan + trusted SearchOptions(mode/top_k/as_of_date/policy) and returns native requests/responses, aggregated evidence/occurrences, completeness, errors/warnings, skipped indices and executed_searches. Fail-fast and cancellation remain intact.

RetrievalService dispatches BM25/dense/hybrid; rerank is an optional hybrid configuration, not a separate RetrievalMode. SupabaseRpcRepository.call_rpc uses an existing synchronous client in asyncio.to_thread. Retrieval bootstrap disables auth session persistence and uses read repositories. No crawler/indexing/migration/write method is called. E5 and cross-encoder need local checkpoints; both were present and used with HF_HUB_OFFLINE/TRANSFORMERS_OFFLINE. No downloads.

## Dataset fixed before execution

`evaluation/query_search/cases.json`: **45 questions / 15 categories / 3 cases per category**, UTF-8. SHA-256 `dde3b1dcff9c8262371cb518d80b4ec6f330c2668d1bcab9c0cc62e5befa54ce`. Includes labour, civil, consumer, administrative, land, family and business questions, plus ambiguous intent. Category list: already_supplied, ambiguous_intent, citation_verification, exact_citation, exceptions_conditions, explicit_date, historical_context, implicit_issue, irrelevant_details, long_conversation, missing_information, multi_issue, multiple_subjects, numerical_facts, single_issue.

Each case has id, question, category/domain, expected_issues, expected_preserved_facts, required_missing_information, forbidden_invented_facts, expected_search_objectives, temporal_expectations, citation_constraints, already_supplied_topics, expected_intent, clarification_expected, notes, live_sample, split. `schema.json` documents machine types. Ground truth is authored from the user scenario before model output, and asserts search needs rather than legal conclusions. Article/document references are synthetic user-supplied input identities, not verified legal propositions. No legal-answer accuracy is measured.

## Scoring v1 (fixed throughout)

- Automatic: returned QueryPlan schema, original string preservation, exact fact span membership, numeric/citation runtime guards, literal citation identity in subqueries, temporal span inclusion, status/errors and reported usage.
- Heuristic: issue/objective/missing-info terms have explicit pipe-separated alternatives. `matches` uses NFC, case-folding and word boundaries. This vocabulary is not proof of semantic/legal equivalence.
- Distinct-objective proxy uses maximum one-to-one matching between expected objectives and subqueries. One broad query cannot count as several distinct searches. Unmatched labels are an overgeneration proxy; human review may find valid synonyms or real overgeneration.
- Fact coverage counts designated explicit spans in the facts field, not original. Deterministic preserves original even when its facts field is empty; a low facts-field score is not loss of the original question.
- Clarification/missing info checks compare pre-authored expectations; redundant-topic matches can be false positives (for example, asking about a special term may match a general contract-type keyword).
- **Aggregate coverage proxies are conditional on accepted plans.** Failures are always shown separately. They are not success-adjusted quality scores. Do not compare successful-only 1.0 against a different failed cohort as overall improvement.
- Every semantic result remains human-review-required. No automated judge or human-reviewed label is claimed. No Precision@K/Recall@K without corpus relevance judgments.

## Sampling and bounds

Deterministic: all 45. Gemini baseline: first case in each category (15 selected, 13 real calls; exact lookup/ambiguity bypass model). One request at a time, 0.5 seconds between completed live calls, no internal retries, deadline preserved. Candidate after: the same 15 plus six additional fixed IDs; provider 429 stopped at 20 rows/18 calls, leaving Q044 unattempted in that run. Final small: six IDs/6 calls after cooldown; total **37** attempted calls, bounded rather than an unlimited search.

Original split labels were unblinded in failure analysis and are **not a blind holdout claim**. Five additional candidate cases had not previously been sent to Gemini, and Q044 was first run in final-small; different prompt versions mean they must be reported separately. All full raw synthetic-question outputs, category metrics, prompts/hashes, usage and errors remain in runs/. Model stochasticity means rerunning identical inputs may not reproduce identical bytes.

Cost is null: 25131 reported tokens were observed across runs, but reliable account-specific pricing was not established. Runtime latency includes cold SDK import and does not isolate Google server processing.

## Reproduce (use new output filenames; old results cannot be overwritten)

```powershell
$env:PYTHONUTF8='1'
$env:LITELLM_LOCAL_MODEL_COST_MAP='True'
.\.venv\Scripts\python.exe -m scripts.evaluate_query_search --mode deterministic --label repeat --output evaluation/query_search/runs/deterministic-repeat.json
.\.venv\Scripts\python.exe -m scripts.evaluate_query_search --mode gemini --label repeat --max-requests 15 --output evaluation/query_search/runs/gemini-repeat.json
```

The second command invokes the current production planner and consumes existing Gemini quota. Historical prompts and outputs are preserved in artifacts; current code is not silently substituted into historical results.

## Semantic review rubric (not yet human-scored)

| Dimension | 0 | 1 | 2 |
|---|---|---|---|
| Issue identification/coverage | Wrong or missing main need | Some needs captured | All material needs captured |
| Overgeneration | Unrelated issues asserted | Related but unnecessary expansion | Only justified issues/conditions |
| Fact grounding | Invented/contradictory fact | Partial explicit context | Exact relevant facts without invention |
| Clarification | Asks supplied info or misses blocking ambiguity | Incomplete/nonblocking follow-up | Necessary, nonredundant questions |
| Search objectives | Off-topic or loses identity/time | Relevant but broad/combined | Distinct, contextual, grounded objectives |
| Temporal/citation handling | Invents/misidentifies source/time | Preserves partly | Preserves identity and separates time roles |

This rubric is supplied for future expert review; no 0–2 human scores are fabricated.
Terms used by automatic proxies are supporting signals, not substitutes for these judgments.
