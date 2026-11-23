# Failure analysis with observed evidence

| Case/failure | Expected | Actual | Root-cause evidence / action |
|---|---|---|---|
| Q007 buyer paid/no delivery, baseline | Exact facts; retrieval objective | text omitted final dot while source_quote retained it; whole plan rejected | Raw JSON shows mismatch. Strict StatedFact equality is working. Broader prompt experiment fixed this sample but was not promoted. Final narrow-schema run accepted a different exact-span response. |
| Q016 employment dates, baseline | legal_question; preserve dates | Model chose quote_lookup for “tra cứu quy định”; runtime rejected | Provider schema allowed two intents even though the semantic path accepts only legal_question. Narrow the provider enum; preserve runtime check. Final live case accepted. |
| Q025 citation verification, baseline | Check a claim, not exact quote lookup | quote_lookup rejected | Same provider intent mismatch. Candidate corrected intent but omitted document ID from search. Final corrected intent yet falsely classified 45/2019/QH14 as temporal; guard rejected. Do not bypass temporal grounding. |
| Q004 specified two-year contract | Don't ask supplied term/type again; retain genuinely missing reason/training | Baseline missing-info item matched a redundant-type proxy | A prompt-only fix removed redundancy but also suppressed useful missing info across cases. Rolled back the broad prompt, not proclaimed solved. The proxy may overcount “special agreement” as asking for type. |
| Q037 debt with numerical facts, candidate | Exact fact spans | “Cho vay 50 triệu đồng” / “Đến hạn chưa trả” were paraphrases not source spans; guard rejected | Raw candidate supports failure. Strict grounding was retained. Final prompt rollback produced accepted spans, but sample size does not prove general elimination. |
| Q005/Q040 multi-subject issues, candidate | Distinct search objectives | One broad query combined several objectives | One-to-one objective proxy fell; raw output confirms grouping. Prompt experiment rejected rather than optimizing against one example. |
| Candidate Q043 | Valid API response | HTTP429 GEMINI_RATE_LIMITED | Batch stopped without internal retry; Q044 not run in that batch. After independent work/cooldown only a bounded six-case final run was permitted. RPM versus daily quota cannot be inferred from sanitized status alone. |
| Cold Dense / following Hybrid | Successful local initialization before search | Timeout at encoding, then MODEL_BUSY | Stage detail and measured later initialization distinguish cold-start from DB latency. Harness warm-up only; algorithms and production deadlines unchanged. |
| Consumer Q007 real retrieval | Relevant sources for delivery/refund | Technical success, lexical proxy 0/2 | Retrieved chunks and source titles require relevance review. A legal conclusion cannot be inferred. No retrieval algorithm change is authorized or justified from this alone. |
| Historical Q019 | Preserve 2010 context | Query preserves time, but Search date remains caller-controlled | Existing temporal warning does not resolve a caller selecting the wrong historical date. No automatic as_of_date inference implemented. |

## Failure classes and review limits

Intent mismatch, lost explicit facts/citation identity, redundant and missing clarification, weak subquery decomposition, temporal misclassification, provider rate limiting and initialization failures are all present. No Search grouping/hash/provenance fault was observed in these real runs. There was no accepted ungrounded fact span, but this does not certify all issue wording or inferred claims. Fact text from a third-party legal allegation remains an allegation, not verified law.

The dataset's original heldout labels were inspected during analysis, so they no longer support blind validation. Additional unseen cases were tested once; output quality remains heuristic and human-review-required. No legal conclusion or model-generated score was used as unquestionable ground truth.

Artifacts: `gemini-before.json`, `gemini-after.json`, `gemini-final.json`, and the retrieval run files under `evaluation/query_search/runs/`. Each preserves actual question, raw synthetic-case response, metrics, failure code and prompt hash.
