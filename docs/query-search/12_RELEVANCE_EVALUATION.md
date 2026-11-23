# Auditable retrieval relevance evaluation

## Balanced collection

Fixed questions: Q001, Q004, Q005, Q007, Q019, Q022, Q025, Q040. They cover civil contracts, labour/multi-issue, family/multi-issue, consumer nondelivery, historical land context, exact lookup, external citation verification and borrower/guarantor relationships. Selection includes known failures, not only successful Gemini examples.

For each case, saved deterministic and real Gemini plans use identical trusted BM25 options: top_k3 and EXPERIMENTAL_ONLY. Q019 has an explicit research anchor2010-12-31 for both variants, not an inferred exact date; all other cases use2026-11-23. Corpus access is read-only. Model outputs are replayed rather than called again for each retrieval variant. Observed index signatures remained the same: True. This is BEST_EFFORT, not a transactional corpus snapshot.

| Case | Variant | Status | Groups | Occurrences | Collapsed |
| --- | --- | --- | --- | --- | --- |
| Q001 | deterministic | COMPLETED | 3 | 3 | 0 |
| Q001 | gemini | COMPLETED | 3 | 3 | 0 |
| Q004 | deterministic | COMPLETED | 5 | 6 | 1 |
| Q004 | gemini | COMPLETED | 6 | 6 | 0 |
| Q005 | deterministic | COMPLETED | 3 | 3 | 0 |
| Q005 | gemini | COMPLETED | 6 | 6 | 0 |
| Q007 | deterministic | COMPLETED | 3 | 3 | 0 |
| Q007 | gemini | BLOCKED_QUERY_PLAN | N/A | N/A | N/A |
| Q019 | deterministic | COMPLETED | 3 | 3 | 0 |
| Q019 | gemini | COMPLETED | 3 | 3 | 0 |
| Q022 | deterministic | COMPLETED | 3 | 3 | 0 |
| Q022 | gemini | COMPLETED | 3 | 3 | 0 |
| Q025 | deterministic | COMPLETED | 3 | 3 | 0 |
| Q025 | gemini | COMPLETED | 3 | 3 | 0 |
| Q040 | deterministic | COMPLETED | 3 | 3 | 0 |
| Q040 | gemini | COMPLETED | 6 | 6 | 0 |

Q007 Gemini is BLOCKED_QUERY_PLAN in the primary pool because its first response violates fact grounding. The separate favorable variability repeat is not substituted to improve the primary comparison. Completeness, warnings/errors, native evidence and provenance remain in relevance/runs.json.

## Rubric and artifacts

0=unrelated;1=broadly related/insufficiently targeted;2=relevant to part;3=directly relevant to the specific objective. This is not a legal correctness, applicability or claim-support label. A source mentioning the requested article is not automatically a direct answer to that article's text or an external legal claim.

- `relevance/pool.json`: **57 ranked query/chunk rows**, including question, model issue links where present, actual objective, document title/URL, chunk/node/block identity, source/snapshot/hash and full text. Native rank is per query, not a fabricated global rank.
- `relevance/labels_template.json`: all labels null, ready for independent human review; identify reviewer/source and explain every score.
- `relevance/REVIEW_QUEUE.md`: readable full-text review queue. Native variant names are omitted from the row presentation, but this is not claimed as a blinded expert trial.
- `relevance/assistant_provisional_labels.json`: **19 model-assisted provisional spot judgments**, covering every native rank-one row inspected by the Codex assistant. Reviewer is explicitly not a human expert; every label has a semantic reason and requires human review. No extra Gemini labeling call was used.

There are **zero human/expert labels**. The base pool stays entirely unlabeled; the separate provisional overlay leaves38 rows without any judgment. Provisional score counts: {'0': 10, '1': 9, '2': 0, '3': 0}. These are a spot-review distribution, not expert Precision@1. Expert Precision@K, Recall@K and NDCG remain null; no full-corpus relevance set or reliable ideal ranking exists.

## Findings from full-text inspection

Civil validity returned an armed-forces honour definition or a training-contract template; divorce/custody returned martyr-caregiver/public-asset text; consumer nondelivery returned training recruitment expenses; exact Article35 lookup returned another regulation that merely cross-references it. These findings reflect the paragraphs' subjects, not keyword overlap. Provisional labels0/1 are open to correction by an expert.

No Search rank/hash/version/dedup defect was found. New Search issue_indices retain objective provenance. An exact-source metadata warning is now added when the requested document number is not confirmed in source titles; a real Q022 probe confirmed this warning while preserving all evidence. This does not remove indirect sources or decide legal sufficiency.

Root attribution remains limited: broad query formulation contributes, while existing retrieval output and corpus coverage may also constrain relevance. Top-k failures do not prove a required source is absent from the entire corpus. No retrieval scoring algorithm was altered to compensate for an unverified cause.

## Commands

```powershell
.\.venv\Scripts\python.exe -m scripts.evaluate_query_relevance --gemini evaluation/query_search/semantic_v2/matched.json
.\.venv\Scripts\python.exe -m scripts.evaluate_query_search_retrieval --plans evaluation/query_search/semantic_v2/matched.json --output evaluation/query_search/semantic_v2/source_identity_real.json --as-of-date 2026-11-23 --bm25-only --case-ids Q022
```

The first command refuses to overwrite its existing pool: use --output with a new folder for another collection. No Gemini call is made by either retrieval command.

## Historical-source metadata limitation

The Q019 historical probe used2010-12-31 but returned sources titled2026, with issued_on=2026-08-05 and effective_from/effective_to=null. The existing retrieval filter cannot establish historical applicability from these missing effective dates. A later consolidated publication could discuss earlier law, so the evaluator does not discard it or infer legal applicability from its title. This is a verified metadata limitation; no corpus/schema/filter algorithm was changed. Source dates and raw metadata are available in the native responses in runs.json, and require review.
