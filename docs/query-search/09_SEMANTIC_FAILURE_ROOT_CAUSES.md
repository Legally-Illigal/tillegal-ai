# Semantic failure root causes — pre-implementation matrix

Audit date: 2026-11-23. Target D:/DOWNLOAD/tillegal-ai/tillegal-ai-main, no .git; no branch/HEAD inferred.
Inspected actual gemini-before/after/final.json outputs, current Query/semantic/schema/prompt, Search/provenance and evaluator. Gemini model remains gemini-3.5-flash-lite. Historical scores are not current test evidence.

| Case | Observed cause | Classification / planned response |
|---|---|---|
| Q004 | Two objectives generally identified, shared term/facts often absent from queries; missing-info empty or redundant | Grounded context/slot consistency, not broad suppression prompt |
| Q005 | Candidate combines divorce/custody/property into one issue/query | Model compression; clearer atomic-objective schema description and explicit issue→query links; no sentence splitting |
| Q007 | Baseline text/source_quote differ by dot | Genuine exact-grounding failure, retained guard; no paraphrase repair |
| Q016 | Original provider allows quote_lookup on ordinary question; later fixed enum works | Keep narrowed schema; preserve event dates separate from document identity |
| Q019 | 2010 preserved but user/caller applicability roles not structured | Span-based typed temporal context; no automatic day inferred from year |
| Q025 | Wrong intent in baseline, document number in temporal_mentions in final; query omits document ID | Model role error plus brittle rejection boundary; deterministically reclassify only exact grounded reference spans, preserve citation and real event dates |
| Q037 | Candidate paraphrases numerical facts | Genuine grounding rejection; preserve guard, append only supplied context |
| Q040 | Candidate compresses borrower/guarantor objectives | Model decomposition uncertainty; mapping and matched evaluation, not keyword-count claims |
| Q043 | Candidate HTTP429; known duration/reason/training can already be supplied | Provider/runtime distinct from semantic; bounded request budget/cooldown; no second model verifier |
| Q044 | Valid dates/facts but generated query drops scenario detail | Grounded context and typed temporal roles |

Search preserved native rank, hash, metadata and dedup in saved runs. No scoring algorithm fault demonstrated. Old alias proxies are not expert relevance labels. Human-reviewed retrieval labels are unavailable: collect a balanced independent review pool with null labels and explicit 0–3 rubric.

Pre-edit decision: add deterministic span parser plus typed additive context to QueryPlan; validate model temporal mentions against spans, reclassify reference-only mentions with an audit warning. Keep all unsupported facts/citations/numbers rejected. Add narrowly scoped supplied-slot consistency; improve atomic-objective guidance without restoring rejected broad prompt. Preserve issue/query mapping through Search occurrences. At most25 new Gemini requests, sequential, no hidden retry; same original15 IDs plus bounded targeted/unseen/variability checks.

## Verified outcomes

- Starting tree was actually checked: 622 pytest cases passed before edits.
- Q025 now succeeds on real Gemini and replay of the formerly rejected recorded response: exact45/2019/QH14 is retained as a user-supplied document reference, excluded from time, with MODEL_REFERENCE_RECLASSIFIED. No source identity is verified merely by parsing it.
- Q019 exposed a separate deterministic bug: “không phải hiện nay” was included in legacy scope. The original span remains typed with negated=true; final postprocessing excludes it from active scope. Recorded real model outputs were replayed through this correction without another API call.
- Q004 missing-info output includes a training question beginning with “Loại hợp đồng”; the old keyword proxy flags it, but dropping that whole compound question would discard a relevant unknown. The consistency rules intentionally retain it. This is a proxy limitation, not a score target.
- Q005 now produces custody and property objectives separately in the targeted live run. That does not prove every divorce information need has been covered.
- Q007 still violates exact fact equality in the primary run; the separate variability call succeeds. Neither guard relaxation nor selecting the favorable repeat is used to hide the primary failure.
- Initial batch received HTTP429 at Q037 and stopped. A single bounded continuation completed remaining selected IDs after independent work/cooldown. Both attempts remain in history.
- Real BM25 top results include military-honour/benefit, public-asset and training-template chunks for unrelated questions. Reasons are based on text inspection, not keyword overlap. Full corpus coverage and the relative contribution of corpus/retriever limitations are not established.
- Search now warns when an exact-lookup document number is absent from retrieved source titles; source text merely cross-references the requested article. Evidence/rank/completeness are not changed, and no legal sufficiency judgment is introduced.

No new automatic legal-answer agent, second verification model, schema migration or retrieval algorithm was introduced. Every result below separates live provider responses, deterministic replay, metadata checks, provisional assistant review and missing expert labels.
