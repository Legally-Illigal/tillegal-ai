# Real Supabase Query → Search → Retrieval verification

**Real Gemini output and real Supabase corpus, not fixture evidence.** To avoid duplicate paid model calls, scripts replay immutable accepted QueryPlans from real Gemini evaluation artifacts through actual Search/RetrievalService. The full trace crosses saved JSON; it is not a newly simultaneous Gemini + database call. The Gemini step, plan validation, read-only DB retrieval and provenance checks were all actually executed.

Preflight via existing RetrievalService BM25 returned OK with three evidence chunks, index `vbpl-bm25-unicode-v1` READY/version v1. No credentials/connection URL printed. The preflight result is in `runs/preflight.json`. Only existing read paths (`get_sparse_index`, `search_sparse_legal_chunks`, chunk/source reads, `get_dense_index`, vector search) were invoked; no schema, migration, corpus, policy or index mutation.

All executions use explicit `as_of_date=2026-11-23`, `EXPERIMENTAL_ONLY`, top_k=3. Hybrid branch budgets 10 each, rerank pool 8. Q001 tests civil contract validity in all four configured modes; Q004 tests employee exit; Q010 tests land certification. Final replay adds consumer Q007; final Q025 remains blocked because Query did not produce an accepted plan.

| Run | Case | Mode | Status | Evidence groups | Dedup collapsed | Hash/provenance | Rerank |
| --- | --- | --- | --- | --- | --- | --- | --- |
| retrieval-deterministic.json | Q001 | bm25 | COMPLETED | 3 | 0 | True/True |  |
| retrieval-deterministic.json | Q004 | bm25 | COMPLETED | 5 | 1 | True/True |  |
| retrieval-deterministic.json | Q010 | bm25 | COMPLETED | 3 | 0 | True/True |  |
| retrieval-before.json | Q001 | bm25 | COMPLETED | 3 | 0 | True/True |  |
| retrieval-before.json | Q001 | dense | FAILED | 0 | 0 | None/None |  |
| retrieval-before.json | Q001 | hybrid | FAILED | 0 | 0 | None/None |  |
| retrieval-before.json | Q001 | rerank | COMPLETED | 3 | 0 | True/True | APPLIED |
| retrieval-before.json | Q004 | bm25 | COMPLETED | 4 | 2 | True/True |  |
| retrieval-before.json | Q010 | bm25 | COMPLETED | 3 | 0 | True/True |  |
| retrieval-before-warm.json | Q001 | bm25 | COMPLETED | 3 | 0 | True/True |  |
| retrieval-before-warm.json | Q001 | dense | COMPLETED | 3 | 0 | True/True |  |
| retrieval-before-warm.json | Q001 | hybrid | COMPLETED | 3 | 0 | True/True |  |
| retrieval-before-warm.json | Q001 | rerank | COMPLETED | 3 | 0 | True/True | APPLIED |
| retrieval-before-warm.json | Q004 | bm25 | COMPLETED | 4 | 2 | True/True |  |
| retrieval-before-warm.json | Q010 | bm25 | COMPLETED | 3 | 0 | True/True |  |
| retrieval-candidate-warm.json | Q001 | bm25 | COMPLETED | 3 | 0 | True/True |  |
| retrieval-candidate-warm.json | Q001 | dense | COMPLETED | 3 | 0 | True/True |  |
| retrieval-candidate-warm.json | Q001 | hybrid | COMPLETED | 3 | 0 | True/True |  |
| retrieval-candidate-warm.json | Q001 | rerank | COMPLETED | 3 | 0 | True/True | APPLIED |
| retrieval-candidate-warm.json | Q004 | bm25 | COMPLETED | 5 | 1 | True/True |  |
| retrieval-candidate-warm.json | Q010 | bm25 | COMPLETED | 3 | 0 | True/True |  |
| retrieval-final.json | Q004 | bm25 | COMPLETED | 5 | 1 | True/True |  |
| retrieval-final.json | Q007 | bm25 | COMPLETED | 3 | 0 | True/True |  |

## Cold versus initialized

Cold Dense failed `RETRIEVAL_TIMEOUT` at encoding after about 30s. The following Hybrid failed `MODEL_BUSY` while the cancelled model-loading worker retained its lock. This is initialization-related evidence, not proof vector SQL was slow. Rerank in that same cold process completed with APPLIED; its native diagnostics confirm model inference occurred.

With explicit local initialization measured separately, all four modes completed and returned evidence. Baseline initialization: [{'model': 'e5_base', 'status': 'INITIALIZED', 'ms': 12819.46}, {'model': 'e5_rerank', 'status': 'INITIALIZED', 'ms': 3020.22}, {'model': 'cross_encoder', 'status': 'INITIALIZED', 'ms': 2731.88}]. This warm-up lives only in the evaluation harness; production timeouts/algorithms were not changed. Do not attribute warm/cold latency differences to Query quality.

Per-mode lifecycle: all four were configured and executed. E5/checkpoints initialized in warm runs. BM25, dense, hybrid and rerank returned results. Rerank statuses explicitly APPLIED; Hybrid alone is not called reranking. Cold failures are preserved, not overwritten.

## Provenance and actual outputs

For every nonempty successful result: content SHA-256 recomputed; source/chunk/structure identity preserved; each occurrence matched its request query and native response ID; identical source payloads safely deduplicated. Q004 had six occurrences condensed to four/five groups depending on the plan. Distinct snapshots/metadata stay in separate grouping keys. No version conflict was observed in these few real cases; existing unit tests cover conflicting payloads.

Source metadata, source URLs, effective dates, evidence content, query-local ranks/scores, fusion and reranking diagnostics are in the JSON run files. Warning codes remain visible, including incomplete temporal metadata; NONE of these checks establishes legal applicability or sufficiency. Retrieval results are BEST_EFFORT rather than immutable transaction snapshots.

The lexical topic proxy for the labour question was 0/2 with deterministic and 1/2 with Gemini. Consumer final Q007 was 0/2 despite technically successful retrieval. These are observations from simple keyword matching, **not proof of improved relevance or legal correctness**. Some top results concern different document topics. No labelled relevance set exists, so Precision/Recall/NDCG are not claimed.

```powershell
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
$env:OMP_NUM_THREADS='2'
$env:MKL_NUM_THREADS='2'
.\.venv\Scripts\python.exe -m scripts.evaluate_query_search_retrieval --plans evaluation/query_search/runs/gemini-before.json --output evaluation/query_search/runs/retrieval-repeat.json --as-of-date 2026-11-23 --warm-models
```

This invokes the existing real corpus read paths with local models; it does not call Gemini again. Raw run artifacts separate failed, blocked, initialized, executed and returned-result states.
