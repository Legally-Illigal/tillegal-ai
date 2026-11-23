# 18 — Controlled query formulation experiments

## Fixed design

Four cases selected before running: Q001 civil validity, Q004 employment, Q022 exact citation, Q040 loan/guarantee. A=original question; B=existing deterministic subqueries; C=saved primary Gemini-mode subqueries (Q022 is deterministic short circuit, not Gemini-generated); D=manually authored research-only issue queries. No hidden replacement of primary failures, no prompt changes, no LLM calls.

All A/B/C/D comparisons use BM25, top_k10, as_of_date2026-11-23, usage policy EXPERIMENTAL_ONLY, the same composed RetrievalService. Historical Q019 is excluded from this experiment and remains a separate saved2010 probe. Each subquery is run independently through Search with a synthetic one-query plan to isolate text effects. Full production multi-issue plans are checked separately through saved-response replay; synthetic runs do not exercise original issue mapping or quote_lookup warning logic.

No result filtering, scoring changes, or production promotion of D. A/B/C may have unequal subquery counts; per-query outcomes are reported, not pooled as a fair expert case-level score. Exact textual duplicates reuse an observation within the run and retain aliases.30 scheduled rows =28 Search invocations +2 aliases. Each request inspected at prefixes3/5/10 from one depth10 output; these are not independent top-k3/5 calls. Hybrid budgets10 BM25/10 Dense; reranker pool10; RRF constant60. Reranking only permutes the fused10 candidates it receives, not all20 branch candidates.

## Complete query schedule

|Row|Case|Variant|Objective|Chars|Mode|Latency ms|Cross-reference rank*|Query|
|---|---|---|---|---|---|---|---|---|
|0|Q001|A_original|0|47|bm25|3484.82|None|Điều kiện để hợp đồng dân sự có hiệu lực là gì?|
|1|Q001|D_research_only|0|51|bm25|1413.77|None|điều kiện có hiệu lực của giao dịch dân sự hợp đồng|
|2|Q001|B_deterministic|0|46|bm25|1257.86|None|Điều kiện để hợp đồng dân sự có hiệu lực là gì|
|3|Q001|C_gemini|0|41|bm25|1778.91|None|Điều kiện có hiệu lực của hợp đồng dân sự|
|4|Q004|A_original|0|131|bm25|1338.93|None|Tôi ký hợp đồng lao động 2 năm, mới làm được 6 tháng nhưng muốn nghỉ việc. Tôi có phải báo trước không và có phải bồi thường không?|
|5|Q004|D_research_only|0|62|bm25|1158.08|1|người lao động đơn phương chấm dứt hợp đồng lao động báo trước|
|6|Q004|D_research_only|1|52|bm25|1424.31|3|người lao động chấm dứt hợp đồng lao động bồi thường|
|7|Q004|B_deterministic|0|170|bm25|1292.49|2|người lao động đơn phương chấm dứt hợp đồng lao động nghĩa vụ báo trước trường hợp miễn báo trước; tình huống: hợp đồng lao động 2 năm mới làm được 6 tháng muốn nghỉ việc|
|8|Q004|B_deterministic|1|167|bm25|1250.89|1|người lao động đơn phương chấm dứt hợp đồng lao động trái pháp luật bồi thường chi phí đào tạo; tình huống: hợp đồng lao động 2 năm mới làm được 6 tháng muốn nghỉ việc|
|9|Q004|C_gemini|0|187|bm25|1434.06|5|người lao động đơn phương chấm dứt hợp đồng lao động xác định thời hạn nghĩa vụ báo trước; tình huống người dùng: Tôi ký hợp đồng lao động 2 năm; mới làm được 6 tháng nhưng muốn nghỉ việc|
|10|Q004|C_gemini|1|185|bm25|1441.32|3|người lao động đơn phương chấm dứt hợp đồng lao động trái pháp luật nghĩa vụ bồi thường; tình huống người dùng: Tôi ký hợp đồng lao động 2 năm; mới làm được 6 tháng nhưng muốn nghỉ việc|
|11|Q022|A_original|0|46|bm25|1732.72|1|Tra cứu Điều 35 Bộ luật Lao động 45/2019/QH14.|
|12|Q022|D_research_only|0|37|bm25|1733.69|1|Điều 35 Bộ luật Lao động 45/2019/QH14|
|13|Q022|B_deterministic|0|46|bm25|alias|1|Tra cứu Điều 35 Bộ luật Lao động 45/2019/QH14.|
|14|Q022|C_gemini|0|46|bm25|alias|1|Tra cứu Điều 35 Bộ luật Lao động 45/2019/QH14.|
|15|Q040|A_original|0|96|bm25|1500.94|None|Tôi cho A vay tiền, B ký bảo lãnh, A không trả. Tôi có thể yêu cầu A và B thực hiện nghĩa vụ gì?|
|16|Q040|D_research_only|0|27|bm25|1528.55|None|nghĩa vụ trả nợ của bên vay|
|17|Q040|D_research_only|1|27|bm25|1236.7|None|thực hiện nghĩa vụ bảo lãnh|
|18|Q040|B_deterministic|0|95|bm25|1504.82|None|Tôi cho A vay tiền, B ký bảo lãnh, A không trả. Tôi có thể yêu cầu A và B thực hiện nghĩa vụ gì|
|19|Q040|C_gemini|0|126|bm25|1817.56|None|nghĩa vụ trả nợ của người vay tiền hợp đồng vay tài sản; tình huống người dùng: Tôi cho A vay tiền; B ký bảo lãnh; A không trả|
|20|Q040|C_gemini|1|148|bm25|1362.69|None|trách nhiệm của bên bảo lãnh khi người được bảo lãnh không thực hiện nghĩa vụ; tình huống người dùng: Tôi cho A vay tiền; B ký bảo lãnh; A không trả|
|21|Q001|C_gemini|0|41|dense|903.85|None|Điều kiện có hiệu lực của hợp đồng dân sự|
|22|Q001|C_gemini|0|41|hybrid|2525.13|None|Điều kiện có hiệu lực của hợp đồng dân sự|
|23|Q001|C_gemini|0|41|rerank|3415.97|None|Điều kiện có hiệu lực của hợp đồng dân sự|
|24|Q004|C_gemini|0|187|dense|2005.36|None|người lao động đơn phương chấm dứt hợp đồng lao động xác định thời hạn nghĩa vụ báo trước; tình huống người dùng: Tôi ký hợp đồng lao động 2 năm; mới làm được 6 tháng nhưng muốn nghỉ việc|
|25|Q004|C_gemini|0|187|hybrid|2230.53|9|người lao động đơn phương chấm dứt hợp đồng lao động xác định thời hạn nghĩa vụ báo trước; tình huống người dùng: Tôi ký hợp đồng lao động 2 năm; mới làm được 6 tháng nhưng muốn nghỉ việc|
|26|Q004|C_gemini|0|187|rerank|3688.53|2|người lao động đơn phương chấm dứt hợp đồng lao động xác định thời hạn nghĩa vụ báo trước; tình huống người dùng: Tôi ký hợp đồng lao động 2 năm; mới làm được 6 tháng nhưng muốn nghỉ việc|
|27|Q022|C_gemini|0|46|dense|854.81|1|Tra cứu Điều 35 Bộ luật Lao động 45/2019/QH14.|
|28|Q022|C_gemini|0|46|hybrid|2948.87|1|Tra cứu Điều 35 Bộ luật Lao động 45/2019/QH14.|
|29|Q022|C_gemini|0|46|rerank|4061.21|1|Tra cứu Điều 35 Bộ luật Lao động 45/2019/QH14.|

*Tracked chunk2973a693-2276-4e4f-a233-f7038e4717e0 is a local-resolution cross-reference, NOT positive ground truth. A better rank for it does not mean a better answer.

## Outcomes

- Q001: C41 chars still ranks the training-contract placeholder first in all4 modes. D51 chars ranks a signature block first. Not all research variants are shorter; they alter vocabulary too. No measured substantive improvement.
- Q004: C187/185 chars versus D62/52. For notice, cross-reference moves C5→D1; for compensation C3→D3. This shows formulation sensitivity, not correct rule retrieval. D compensation rank1 concerns suspension of revolutionary benefits. Dropping all supplied facts globally would be unjustified.
- Q022: A/B/C identical46-char text; D37 chars preserves number/article. Cross-reference rank1 throughout all4 modes; no requested source identity found. Query shortening cannot manufacture that source.
- Q040: C126/148 chars, D27/27. Short borrower query retrieves public investment/debt material; guarantor D retrieves territorial sovereignty. No consistent cross-case improvement; no production change.
- Many neighboring clauses from the same source dominate the bounded pools. They are distinct chunks, not necessarily duplicate payloads. Search retains their native positions and does not impose diversity.

Relevance statements here are preliminary assistant technical observations, with no numeric human labels. No P@K/NDCG/recall claims. Relevant sources could exist under different titles or paraphrases beyond inspected pools.

## Modes and latency

Mode comparison fixes the first C query for Q001/Q004/Q022. All12 mode/case outcomes (BM25 baseline included) completed, all3 reranker responses APPLIED. Query/context, filters and branch budgets fixed. Main top-ranked mismatch persisted. There is no evidence here of a retrieval configuration failure or index-change failure.

|Mode|Measured calls|Median ms|Min ms|Max ms|
|---|---|---|---|---|
|bm25|19|1434.06|1158.08|3484.82|
|dense|3|903.85|854.81|2005.36|
|hybrid|3|2525.13|2230.53|2948.87|
|rerank|3|3688.53|3415.97|4061.21|

BM25 latency covers19 formulation calls, other modes3 each, so these medians are not a general speed benchmark. Initialization separately measured: E5=15746.19ms, CrossEncoder=3251.53ms; excluded from request timings. Request timings include network, hydration and inference, not pure model inference only. Reranker diagnostics retain inference/truncation data in raw responses.

Before/after metadata identical, individual responses retain index identities, BEST_EFFORT rather than transaction snapshot. Raw chunks/IDs/ranks/failures: [experiments.json](../../evaluation/query_search/relevance_investigation/experiments.json).280 experimental rows prepared separately in [experimental_review.json](../../evaluation/query_search/relevance_investigation/experimental_review.json), all human labels null. Original57-row queue reused independently.

## Reproduce

From project root, existing.env plus environment config and existing local checkpoints required. Do not overwrite previous results. No Gemini key is needed by this tool.

```powershell
$env:PYTHONUTF8='1'
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
.\.venv\Scripts\python.exe -m scripts.investigate_query_relevance --live --output evaluation/query_search/relevance_investigation_NEW
.\.venv\Scripts\python.exe -m scripts.investigate_query_relevance --coverage-probes-only --output evaluation/query_search/relevance_investigation_NEW
.\.venv\Scripts\python.exe -m scripts.investigate_query_relevance --analyze-only --output evaluation/query_search/relevance_investigation_NEW
```

Offline reanalysis of delivered artifacts needs no network/model:

```powershell
.\.venv\Scripts\python.exe -m scripts.investigate_query_relevance --analyze-only
```
