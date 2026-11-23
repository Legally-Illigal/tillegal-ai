# 17 — Relevance root-cause audit

Investigation date2026-11-23. Existing plans/raw Gemini responses and complete stored57 query/chunk rows were reused.0 new Gemini calls. Technical execution success is distinct from substantive relevance and legal correctness. No expert relevance labels exist.

## Evidence and scope

- [Full case audit](../../evaluation/query_search/relevance_investigation/case_audit.json) contains original questions, immutable authored expectations, both plans, all native requests/responses/chunks and aggregate evidence.
- [Human queue](../../evaluation/query_search/relevance_investigation/HUMAN_REVIEW_QUEUE.md) shows the full57 chunk texts with native ranks, source/provision identity, query, issues and temporal metadata. All labels remain null.
- [Experiments](../../evaluation/query_search/relevance_investigation/experiments.json) retain28 actual Search calls and2 explicit literal-query aliases. [Summary](../../evaluation/query_search/relevance_investigation/experiment_summary.json) provides prefixes3/5/10 and latencies.
- [Coverage](../../evaluation/query_search/relevance_investigation/coverage.json) enumerates58 visible source rows; [literal probes](../../evaluation/query_search/relevance_investigation/coverage_probes.json) are separately bounded.
- Current Query/Search source was inspected alongside RetrievalService, SQL RPC, tokenizer, E5, fusion and reranker. These modules are not interchangeable owners.

Confidence concerns the stated evidence/classification only, not expert legal relevance. Corpus statements refer to current credential-visible records, not every possible database/project or external legal corpus. BM25 SQL inspected locally supports bag-of-token matching; live results are consistent with that behavior, but deployed SQL was not introspected or altered.

## Q001

Question: Điều kiện để hợp đồng dân sự có hiệu lực là gì?

Expected information need: Điều kiện hiệu lực hợp đồng dân sự.

Classification/confidence: Coverage limitation (high for missing named code identities in visible metadata); ranking limitation (medium, preliminary relevance judgment). No attributable semantic defect.

Evidence and interpretation: Gemini query is already concise41 chars. Both lexical and semantic retrieval rank a training-contract validity placeholder. D introduces giao dịch dân sự but ranks signature/template material. Query changes alone do not supply the missing rule.

### deterministic: COMPLETED

Issues: []

Mode/options: `{"mode": "bm25", "top_k": 3, "as_of_date": "2026-11-23", "allowed_usage_policies": ["EXPERIMENTAL_ONLY"]}`

- Query0: Điều kiện để hợp đồng dân sự có hiệu lực là gì

|Query|Rank|Source title|Source ID|Chunk/provision|
|---|---|---|---|---|
|0|1|Văn bản hợp nhất 123/2026/VBHN-PL-VPQH của Văn phòng Quốc hội|4b8ae460-689c-4759-9514-a18198a214ab|ecdd3a4a-cbd7-4af7-ab01-072f917056be / chapter-ii-section-5-article-20-clause-1|
|0|2|Thông tư 141/2026/TT-BTC của Bộ Tài chính|d199e164-5747-426d-89ef-fb0e23a6d9c7|e2740feb-e0e8-44fc-b107-faf2c674a835 / appendix-4-part-ii-article-13|
|0|3|Văn bản hợp nhất 123/2026/VBHN-PL-VPQH của Văn phòng Quốc hội|4b8ae460-689c-4759-9514-a18198a214ab|d8369105-7be7-4b39-be3f-52a49f8b6c98 / chapter-ii-section-5-article-20-clause-2|

Citations/time/objective links: `{"citations": [], "temporal_context": [], "search_objectives": []}`

### gemini: COMPLETED

Issues: ["Điều kiện có hiệu lực của hợp đồng dân sự"]

Mode/options: `{"mode": "bm25", "top_k": 3, "as_of_date": "2026-11-23", "allowed_usage_policies": ["EXPERIMENTAL_ONLY"]}`

- Query0: Điều kiện có hiệu lực của hợp đồng dân sự

|Query|Rank|Source title|Source ID|Chunk/provision|
|---|---|---|---|---|
|0|1|Thông tư 141/2026/TT-BTC của Bộ Tài chính|d199e164-5747-426d-89ef-fb0e23a6d9c7|e2740feb-e0e8-44fc-b107-faf2c674a835 / appendix-4-part-ii-article-13|
|0|2|Văn bản hợp nhất 123/2026/VBHN-PL-VPQH của Văn phòng Quốc hội|4b8ae460-689c-4759-9514-a18198a214ab|ecdd3a4a-cbd7-4af7-ab01-072f917056be / chapter-ii-section-5-article-20-clause-1|
|0|3|Nghị quyết 25/2026/NQ-HĐND của HĐND Tỉnh Đắk Lắk|60c5be9f-20d9-4897-977e-2059f2c59ff2|c8057a3a-89a6-42e3-8df6-c82c783ed04e / chapter-iv-article-13-clause-2|

Citations/time/objective links: `{"citations": [], "temporal_context": [], "search_objectives": [{"query_index": 0, "issue_indices": [0]}]}`

## Q004

Question: Tôi ký hợp đồng lao động 2 năm, mới làm được 6 tháng nhưng muốn nghỉ việc. Tôi có phải báo trước không và có phải bồi thường không?

Expected information need: Nghĩa vụ báo trước và bồi thường khi người lao động nghỉ việc; không mặc định vi phạm.

Classification/confidence: Query formulation contributor (medium); coverage limitation (high for source identity); ranking limitation (medium). Search orchestration defect not established.

Evidence and interpretation: C queries187/185 chars append2-year/6-month facts. Short D62/52 chars shifts the known cross-reference to ranks1/3 versus C5/3. That cross-reference is not the requested principal rule. B also ranks it1/2. No consistent relevance gain established; retain facts and production strategy. C second query includes trái pháp luật as a research category, not a verified finding; downstream must not infer actual violation.

### deterministic: COMPLETED

Issues: ["Đơn phương chấm dứt hợp đồng lao động và nghĩa vụ báo trước", "Nghĩa vụ bồi thường khi chấm dứt hợp đồng lao động"]

Mode/options: `{"mode": "bm25", "top_k": 3, "as_of_date": "2026-11-23", "allowed_usage_policies": ["EXPERIMENTAL_ONLY"]}`

- Query0: người lao động đơn phương chấm dứt hợp đồng lao động nghĩa vụ báo trước trường hợp miễn báo trước; tình huống: hợp đồng lao động 2 năm mới làm được 6 tháng muốn nghỉ việc
- Query1: người lao động đơn phương chấm dứt hợp đồng lao động trái pháp luật bồi thường chi phí đào tạo; tình huống: hợp đồng lao động 2 năm mới làm được 6 tháng muốn nghỉ việc

|Query|Rank|Source title|Source ID|Chunk/provision|
|---|---|---|---|---|
|0|1|Văn bản hợp nhất 123/2026/VBHN-PL-VPQH của Văn phòng Quốc hội|4b8ae460-689c-4759-9514-a18198a214ab|e0956b58-06d5-4774-8ee1-ad97649eef70 / chapter-vi-article-54-clause-5|
|0|2|Nghị quyết 25/2026/NQ-HĐND của HĐND Tỉnh Đắk Lắk|60c5be9f-20d9-4897-977e-2059f2c59ff2|2973a693-2276-4e4f-a233-f7038e4717e0 / chapter-i-article-5-clause-2-point-b|
|0|3|Thông tư 141/2026/TT-BTC của Bộ Tài chính|d199e164-5747-426d-89ef-fb0e23a6d9c7|e76653f4-6cc6-4d82-8147-57e9ed6cb3ef / appendix-4-part-ii-article-10|
|1|1|Nghị quyết 25/2026/NQ-HĐND của HĐND Tỉnh Đắk Lắk|60c5be9f-20d9-4897-977e-2059f2c59ff2|2973a693-2276-4e4f-a233-f7038e4717e0 / chapter-i-article-5-clause-2-point-b|
|1|2|Thông tư 141/2026/TT-BTC của Bộ Tài chính|d199e164-5747-426d-89ef-fb0e23a6d9c7|4ebe13ce-f406-4970-ab5c-acceb90dbcdc / chapter-iii-article-15-clause-4-point-d|
|1|3|Nghị quyết 25/2026/NQ-HĐND của HĐND Tỉnh Đắk Lắk|60c5be9f-20d9-4897-977e-2059f2c59ff2|758fd1e3-72be-44e5-b4de-a55bd2b26a15 / chapter-i-article-5-clause-3|

Citations/time/objective links: `{"citations": [], "temporal_context": [], "search_objectives": []}`

### gemini: COMPLETED

Issues: ["Nghĩa vụ báo trước khi người lao động đơn phương chấm dứt hợp đồng lao động xác định thời hạn", "Nghĩa vụ bồi thường chi phí đào tạo hoặc vi phạm thời hạn báo trước khi người lao động nghỉ việc"]

Mode/options: `{"mode": "bm25", "top_k": 3, "as_of_date": "2026-11-23", "allowed_usage_policies": ["EXPERIMENTAL_ONLY"]}`

- Query0: người lao động đơn phương chấm dứt hợp đồng lao động xác định thời hạn nghĩa vụ báo trước; tình huống người dùng: Tôi ký hợp đồng lao động 2 năm; mới làm được 6 tháng nhưng muốn nghỉ việc
- Query1: người lao động đơn phương chấm dứt hợp đồng lao động trái pháp luật nghĩa vụ bồi thường; tình huống người dùng: Tôi ký hợp đồng lao động 2 năm; mới làm được 6 tháng nhưng muốn nghỉ việc

|Query|Rank|Source title|Source ID|Chunk/provision|
|---|---|---|---|---|
|0|1|Nghị quyết 25/2026/NQ-HĐND của HĐND Tỉnh Đắk Lắk|60c5be9f-20d9-4897-977e-2059f2c59ff2|01fcd190-2fc8-48ee-8cf5-de8fc77fada7 / chapter-i-article-5-clause-1-point-c|
|0|2|Nghị quyết 25/2026/NQ-HĐND của HĐND Tỉnh Đắk Lắk|60c5be9f-20d9-4897-977e-2059f2c59ff2|30142e55-42ce-494a-a6fe-a8a10eb46922 / chapter-ii-article-8-clause-1-point-b|
|0|3|Thông tư 141/2026/TT-BTC của Bộ Tài chính|d199e164-5747-426d-89ef-fb0e23a6d9c7|e76653f4-6cc6-4d82-8147-57e9ed6cb3ef / appendix-4-part-ii-article-10|
|1|1|Văn bản hợp nhất 01/2026/VBHN-NĐ-BNG của Văn phòng Chính phủ|1632d7cb-fb66-4389-b91b-820809e1432d|d7f358eb-2586-42c5-9c7d-d2b9f228ca91 / chapter-ii-article-10-clause-2|
|1|2|Văn bản hợp nhất 123/2026/VBHN-PL-VPQH của Văn phòng Quốc hội|4b8ae460-689c-4759-9514-a18198a214ab|e0956b58-06d5-4774-8ee1-ad97649eef70 / chapter-vi-article-54-clause-5|
|1|3|Nghị quyết 25/2026/NQ-HĐND của HĐND Tỉnh Đắk Lắk|60c5be9f-20d9-4897-977e-2059f2c59ff2|2973a693-2276-4e4f-a233-f7038e4717e0 / chapter-i-article-5-clause-2-point-b|

Citations/time/objective links: `{"citations": [], "temporal_context": [{"text": "2 năm", "start": 25, "end": 30, "role": "duration", "iso_date": null, "negated": false}, {"text": "6 tháng", "start": 45, "end": 52, "role": "duration", "iso_date": null, "negated": false}], "search_objectives": [{"query_index": 0, "issue_indices": [0]}, {"query_index": 1, "issue_indices": [1]}]}`

## Q005

Question: Tôi muốn ly hôn, việc nuôi con và chia tài sản giải quyết thế nào?

Expected information need: Nuôi con/cấp dưỡng và chia tài sản khi ly hôn.

Classification/confidence: Coverage limitation (medium-high from scoped metadata/literal evidence); ranking limitation (medium). Deterministic decomposition limitation (verified structural difference).

Evidence and interpretation: B has one broad query; C has two objectives. Custody query retrieves martyr-caregiver benefits; assets query retrieves reorganization of public premises. Separate objectives do not compensate for missing relevant coverage. No new live mode/formulation experiment for this case; saved BM25 only.

### deterministic: COMPLETED

Issues: []

Mode/options: `{"mode": "bm25", "top_k": 3, "as_of_date": "2026-11-23", "allowed_usage_policies": ["EXPERIMENTAL_ONLY"]}`

- Query0: Tôi muốn ly hôn, việc nuôi con và chia tài sản giải quyết thế nào

|Query|Rank|Source title|Source ID|Chunk/provision|
|---|---|---|---|---|
|0|1|Văn bản hợp nhất 123/2026/VBHN-PL-VPQH của Văn phòng Quốc hội|4b8ae460-689c-4759-9514-a18198a214ab|629e562b-37be-42cb-b505-fda1118c25bd / chapter-i-article-3-clause-3|
|0|2|Quyết định 58/2026/QĐ-UBND của UBND Tỉnh Hưng Yên|5d85a3c5-e170-408f-a3f0-f0e1eeb3eb6b|2f5af256-2106-4f54-a1d6-dda82962af08 / chapter-ii-article-9-clause-2-point-e|
|0|3|Văn bản hợp nhất 01/2026/VBHN-NĐ-BNG của Văn phòng Chính phủ|1632d7cb-fb66-4389-b91b-820809e1432d|9f0bbbfc-a1b4-4eda-a453-e975bb2995d8 / chapter-ii-article-9-clause-4|

Citations/time/objective links: `{"citations": [], "temporal_context": [], "search_objectives": []}`

### gemini: COMPLETED

Issues: ["Quyền nuôi con và nghĩa vụ cấp dưỡng khi ly hôn", "Nguyên tắc chia tài sản khi ly hôn"]

Mode/options: `{"mode": "bm25", "top_k": 3, "as_of_date": "2026-11-23", "allowed_usage_policies": ["EXPERIMENTAL_ONLY"]}`

- Query0: quyền nuôi con và cấp dưỡng khi ly hôn
- Query1: chia tài sản khi ly hôn

|Query|Rank|Source title|Source ID|Chunk/provision|
|---|---|---|---|---|
|0|1|Văn bản hợp nhất 123/2026/VBHN-PL-VPQH của Văn phòng Quốc hội|4b8ae460-689c-4759-9514-a18198a214ab|97daa00c-389b-4c2c-84dd-06b103eaa7eb / chapter-i-article-4-clause-2|
|0|2|Văn bản hợp nhất 123/2026/VBHN-PL-VPQH của Văn phòng Quốc hội|4b8ae460-689c-4759-9514-a18198a214ab|ad2ed5c5-dab3-4547-a397-8aa7a06abbb6 / chapter-ii-section-3-article-16-clause-4|
|0|3|Văn bản hợp nhất 123/2026/VBHN-PL-VPQH của Văn phòng Quốc hội|4b8ae460-689c-4759-9514-a18198a214ab|30ed1d3e-b804-448b-8ce9-5f4eae0cd635 / chapter-ii-section-3-article-16-clause-5|
|1|1|Nghị định 369/2026/NĐ-CP của Chính phủ|450304fc-b390-46bc-8994-4fc8ba485c55|b6c170cb-de6d-42df-a79b-479251439db6 / article-3-clause-1|
|1|2|Quyết định 91/2026/QĐ-UBND của UBND Tỉnh Điện Biên|6eac2b3b-3f9a-4b5e-ad43-5a7d360b5a92|a31c4316-f650-4cc4-8ab8-84a06dfe6071 / chapter-i-article-3|
|1|3|Văn bản hợp nhất 01/2026/VBHN-NĐ-BNG của Văn phòng Chính phủ|1632d7cb-fb66-4389-b91b-820809e1432d|99856d5c-c73b-4d47-91f7-b96813b10328 / chapter-ii-article-9-clause-7|

Citations/time/objective links: `{"citations": [], "temporal_context": [], "search_objectives": [{"query_index": 0, "issue_indices": [0]}, {"query_index": 1, "issue_indices": [1]}]}`

## Q007

Question: Tôi đặt điện thoại trên mạng, đã chuyển tiền nhưng người bán không giao hàng và không trả lời tin nhắn. Tôi nên tìm hiểu quyền gì?

Expected information need: Quyền của người mua khi đã trả tiền nhưng chưa nhận hàng.

Classification/confidence: Query semantic/grounding rejection (high, saved primary failure); retrieval/corpus limitation (medium, deterministic branch only).

Evidence and interpretation: Primary Gemini plan failed strict source-quote grounding; preserved as blocked. B ranks training advertising expenses and unrelated material. Saved successful variability output is not substituted. No fresh Gemini call or C experiment for this case.

### deterministic: COMPLETED

Issues: []

Mode/options: `{"mode": "bm25", "top_k": 3, "as_of_date": "2026-11-23", "allowed_usage_policies": ["EXPERIMENTAL_ONLY"]}`

- Query0: Tôi đặt điện thoại trên mạng, đã chuyển tiền nhưng người bán không giao hàng và không trả lời tin nhắn. Tôi nên tìm hiểu quyền gì

|Query|Rank|Source title|Source ID|Chunk/provision|
|---|---|---|---|---|
|0|1|Thông tư 141/2026/TT-BTC của Bộ Tài chính|d199e164-5747-426d-89ef-fb0e23a6d9c7|a7e7c870-9ee1-4d83-95d8-49fc1367dad5 / chapter-ii-article-7-clause-2-point-a|
|0|2|Quyết định 91/2026/QĐ-UBND của UBND Tỉnh Điện Biên|6eac2b3b-3f9a-4b5e-ad43-5a7d360b5a92|a31c4316-f650-4cc4-8ab8-84a06dfe6071 / chapter-i-article-3|
|0|3|Quyết định 90/2026/QĐ-UBND của UBND Tỉnh Điện Biên|d9748e58-6f88-49df-8763-33e8169fe62d|6086f5cc-2a48-4de0-9df0-1dce556a81cd / article-3-clause-1|

Citations/time/objective links: `{"citations": [], "temporal_context": [], "search_objectives": []}`

### gemini: BLOCKED_QUERY_PLAN

Primary Query failure preserved; no Search result fabricated.

## Q019

Question: Việc mua bán đất của gia đình diễn ra năm 2010, tôi cần tra cứu điều kiện có hiệu lực tại thời điểm đó, không phải hiện nay.

Expected information need: Điều kiện giao dịch mua bán đất tại thời điểm2010, không phải hiện nay.

Classification/confidence: Temporal metadata limitation (high); coverage limitation (medium-high); ranking limitation (medium).

Evidence and interpretation: Query retains event2010 and negated present. Trusted evaluation date2010-12-31 was explicit. Returned123/2026 source has issued_on2026-08-05 and effective_from/to null. Visible metadata has no recorded effective_from<=2010. Missing dates permit results but cannot certify historical applicability; later consolidation is not automatically invalid. No date-filter/schema changes.

### deterministic: COMPLETED

Issues: []

Mode/options: `{"mode": "bm25", "top_k": 3, "as_of_date": "2010-12-31", "allowed_usage_policies": ["EXPERIMENTAL_ONLY"]}`

- Query0: Việc mua bán đất của gia đình diễn ra năm 2010, tôi cần tra cứu điều kiện có hiệu lực tại thời điểm đó, không phải hiện nay.

|Query|Rank|Source title|Source ID|Chunk/provision|
|---|---|---|---|---|
|0|1|Văn bản hợp nhất 123/2026/VBHN-PL-VPQH của Văn phòng Quốc hội|4b8ae460-689c-4759-9514-a18198a214ab|bde15abf-8fb5-46ed-a16f-0ed833b7b06c / chapter-ii-section-2-article-11-clause-1-point-b|
|0|2|Văn bản hợp nhất 123/2026/VBHN-PL-VPQH của Văn phòng Quốc hội|4b8ae460-689c-4759-9514-a18198a214ab|8e1613de-4726-49f5-b464-b850b12a0a0d / chapter-ii-section-2-article-11-clause-1-point-a|
|0|3|Văn bản hợp nhất 123/2026/VBHN-PL-VPQH của Văn phòng Quốc hội|4b8ae460-689c-4759-9514-a18198a214ab|998e3b87-74ad-4108-b5fa-61e376364b24 / chapter-i-article-6-clause-2|

Citations/time/objective links: `{"citations": [], "temporal_context": [], "search_objectives": []}`

### gemini: COMPLETED

Issues: ["Điều kiện có hiệu lực của giao dịch mua bán đất năm 2010"]

Mode/options: `{"mode": "bm25", "top_k": 3, "as_of_date": "2010-12-31", "allowed_usage_policies": ["EXPERIMENTAL_ONLY"]}`

- Query0: điều kiện có hiệu lực của giao dịch mua bán đất năm 2010; tình huống người dùng: Việc mua bán đất của gia đình diễn ra năm 2010

|Query|Rank|Source title|Source ID|Chunk/provision|
|---|---|---|---|---|
|0|1|Văn bản hợp nhất 123/2026/VBHN-PL-VPQH của Văn phòng Quốc hội|4b8ae460-689c-4759-9514-a18198a214ab|41531a03-6aae-4c99-9c81-8ab9319457e9 / chapter-i-article-5-clause-2-point-g|
|0|2|Văn bản hợp nhất 123/2026/VBHN-PL-VPQH của Văn phòng Quốc hội|4b8ae460-689c-4759-9514-a18198a214ab|998e3b87-74ad-4108-b5fa-61e376364b24 / chapter-i-article-6-clause-2|
|0|3|Văn bản hợp nhất 123/2026/VBHN-PL-VPQH của Văn phòng Quốc hội|4b8ae460-689c-4759-9514-a18198a214ab|201e2c36-7a9b-4e61-a8bf-15f57dba4201 / chapter-ii-section-1-article-9-clause-7|

Citations/time/objective links: `{"citations": [], "temporal_context": [{"text": "2010", "start": 42, "end": 46, "role": "event_date", "iso_date": null, "negated": false}, {"text": "thời điểm đó", "start": 90, "end": 102, "role": "historical_reference", "iso_date": null, "negated": false}, {"text": "hiện nay", "start": 115, "end": 123, "role": "current_reference", "iso_date": null, "negated": true}], "search_objectives": [{"query_index": 0, "issue_indices": [0]}]}`

## Q022

Question: Tra cứu Điều 35 Bộ luật Lao động 45/2019/QH14.

Expected information need: Đúng Điều35 của Bộ luật Lao động45/2019/QH14, không phải nguồn khác nhắc đến.

Classification/confidence: Scoped source-identity coverage limitation (high); exact-match ranking limitation (high observed mismatch, not algorithm defect).

Evidence and interpretation: All4 modes rank chunk2973a693… from Nghị quyết25/2026 first; it cites khoản2 Điều35 but is its own Điều5. Complete visible58-row metadata and exact document_number probe return no45/2019/QH14 source. Source unrepresented under that identity in this scope. Current Search warning appears in offline native-response replay; experiment synthetic plans isolate formulation, so do not test exact-intent warning themselves.

### deterministic: COMPLETED

Issues: []

Mode/options: `{"mode": "bm25", "top_k": 3, "as_of_date": "2026-11-23", "allowed_usage_policies": ["EXPERIMENTAL_ONLY"]}`

- Query0: Tra cứu Điều 35 Bộ luật Lao động 45/2019/QH14.

|Query|Rank|Source title|Source ID|Chunk/provision|
|---|---|---|---|---|
|0|1|Nghị quyết 25/2026/NQ-HĐND của HĐND Tỉnh Đắk Lắk|60c5be9f-20d9-4897-977e-2059f2c59ff2|2973a693-2276-4e4f-a233-f7038e4717e0 / chapter-i-article-5-clause-2-point-b|
|0|2|Văn bản hành chính liên quan 742/QĐ-UBND của UBND Thành phố Bắc Ninh|4cb20317-2cb1-43fb-886d-443731536540|96e8c139-65d4-48aa-98ec-bdd2e169e984 / appendix-1|
|0|3|Nghị định 369/2026/NĐ-CP của Chính phủ|450304fc-b390-46bc-8994-4fc8ba485c55|6552f08a-6132-4ca0-97d7-aab238929d2f / document|

Citations/time/objective links: `{"citations": [], "temporal_context": [], "search_objectives": []}`

### gemini: COMPLETED

Issues: []

Mode/options: `{"mode": "bm25", "top_k": 3, "as_of_date": "2026-11-23", "allowed_usage_policies": ["EXPERIMENTAL_ONLY"]}`

- Query0: Tra cứu Điều 35 Bộ luật Lao động 45/2019/QH14.

|Query|Rank|Source title|Source ID|Chunk/provision|
|---|---|---|---|---|
|0|1|Nghị quyết 25/2026/NQ-HĐND của HĐND Tỉnh Đắk Lắk|60c5be9f-20d9-4897-977e-2059f2c59ff2|2973a693-2276-4e4f-a233-f7038e4717e0 / chapter-i-article-5-clause-2-point-b|
|0|2|Văn bản hành chính liên quan 742/QĐ-UBND của UBND Thành phố Bắc Ninh|4cb20317-2cb1-43fb-886d-443731536540|96e8c139-65d4-48aa-98ec-bdd2e169e984 / appendix-1|
|0|3|Nghị định 369/2026/NĐ-CP của Chính phủ|450304fc-b390-46bc-8994-4fc8ba485c55|6552f08a-6132-4ca0-97d7-aab238929d2f / document|

Citations/time/objective links: `{"citations": [{"kind": "article", "text": "Điều 35", "start": 8, "end": 15, "source": "user_supplied_unverified"}, {"kind": "document", "text": "45/2019/QH14", "start": 33, "end": 45, "source": "user_supplied_unverified"}], "temporal_context": [], "search_objectives": []}`

## Q025

Question: Một bài viết nói Điều 35 Bộ luật Lao động 45/2019/QH14 cho nghỉ ngay mọi trường hợp. Tôi muốn kiểm tra trích dẫn này có đúng không.

Expected information need: Kiểm tra phát biểu cho nghỉ ngay mọi trường hợp bằng nguồn và điều luật đúng.

Classification/confidence: Scoped source-identity coverage limitation (high); ambiguous evidence (high); downstream claim-grounding limitation (known boundary).

Evidence and interpretation: Citation retained and no false temporal scope. First result is the same cross-reference, which does not verify the universal allegation. User claim appears as extracted fact, not legally established fact. Exact-source warning currently covers quote_lookup only; Q025 legal_question has no guaranteed warning. This is documented rather than guessed from query text. Saved BM25 only, no new mode run.

### deterministic: COMPLETED

Issues: []

Mode/options: `{"mode": "bm25", "top_k": 3, "as_of_date": "2026-11-23", "allowed_usage_policies": ["EXPERIMENTAL_ONLY"]}`

- Query0: Một bài viết nói Điều 35 Bộ luật Lao động 45/2019/QH14 cho nghỉ ngay mọi trường hợp. Tôi muốn kiểm tra trích dẫn này có đúng không.

|Query|Rank|Source title|Source ID|Chunk/provision|
|---|---|---|---|---|
|0|1|Nghị quyết 25/2026/NQ-HĐND của HĐND Tỉnh Đắk Lắk|60c5be9f-20d9-4897-977e-2059f2c59ff2|2973a693-2276-4e4f-a233-f7038e4717e0 / chapter-i-article-5-clause-2-point-b|
|0|2|Quyết định 47/2025/QD-UBND của UBND Thành phố Hà Nội|a7ad31ed-9de1-4fc6-b5f1-fc671a4366dd|43dcd233-fe3b-4b9b-9c8e-17a7454a10ca / article-7-clause-5|
|0|3|Thông tư 141/2026/TT-BTC của Bộ Tài chính|d199e164-5747-426d-89ef-fb0e23a6d9c7|8d9d86b3-ab2a-44cf-9b31-4a9b0ae5d988 / appendix-3|

Citations/time/objective links: `{"citations": [], "temporal_context": [], "search_objectives": []}`

### gemini: COMPLETED

Issues: ["Kiem tra quy dinh ve quyen don phuong cham dut hop dong cua nguoi lao dong tai Dieu 35 Bo luat Lao dong 2019"]

Mode/options: `{"mode": "bm25", "top_k": 3, "as_of_date": "2026-11-23", "allowed_usage_policies": ["EXPERIMENTAL_ONLY"]}`

- Query0: Điều 35 Bộ luật Lao động 45/2019/QH14 quyền đơn phương chấm dứt hợp đồng lao động của người lao động

|Query|Rank|Source title|Source ID|Chunk/provision|
|---|---|---|---|---|
|0|1|Nghị quyết 25/2026/NQ-HĐND của HĐND Tỉnh Đắk Lắk|60c5be9f-20d9-4897-977e-2059f2c59ff2|2973a693-2276-4e4f-a233-f7038e4717e0 / chapter-i-article-5-clause-2-point-b|
|0|2|Thông tư 141/2026/TT-BTC của Bộ Tài chính|d199e164-5747-426d-89ef-fb0e23a6d9c7|e76653f4-6cc6-4d82-8147-57e9ed6cb3ef / appendix-4-part-ii-article-10|
|0|3|Nghị định 369/2026/NĐ-CP của Chính phủ|450304fc-b390-46bc-8994-4fc8ba485c55|b6c170cb-de6d-42df-a79b-479251439db6 / article-3-clause-1|

Citations/time/objective links: `{"citations": [{"kind": "article", "text": "Điều 35", "start": 17, "end": 24, "source": "user_supplied_unverified"}, {"kind": "document", "text": "45/2019/QH14", "start": 42, "end": 54, "source": "user_supplied_unverified"}], "temporal_context": [], "search_objectives": [{"query_index": 0, "issue_indices": [0]}]}`

## Q040

Question: Tôi cho A vay tiền, B ký bảo lãnh, A không trả. Tôi có thể yêu cầu A và B thực hiện nghĩa vụ gì?

Expected information need: Nghĩa vụ trả nợ của A và nghĩa vụ của B theo bảo lãnh.

Classification/confidence: Coverage limitation (medium-high); query formulation contributor (medium); ranking limitation (medium).

Evidence and interpretation: C maps borrower/guarantor separately but carries all shared facts. D27-char variants change sources; bảo lãnh literal probe finds0 visible chunks; nghĩa vụ trả nợ has1 policy-publicity match. D guarantor query even ranks territorial-sea sovereignty first. No stable gain supporting promotion of D.

### deterministic: COMPLETED

Issues: []

Mode/options: `{"mode": "bm25", "top_k": 3, "as_of_date": "2026-11-23", "allowed_usage_policies": ["EXPERIMENTAL_ONLY"]}`

- Query0: Tôi cho A vay tiền, B ký bảo lãnh, A không trả. Tôi có thể yêu cầu A và B thực hiện nghĩa vụ gì

|Query|Rank|Source title|Source ID|Chunk/provision|
|---|---|---|---|---|
|0|1|Thông tư 141/2026/TT-BTC của Bộ Tài chính|d199e164-5747-426d-89ef-fb0e23a6d9c7|090179c9-e2de-461d-a01c-1fa3b194ffc2 / appendix-4-part-ii-article-7|
|0|2|Thông tư 141/2026/TT-BTC của Bộ Tài chính|d199e164-5747-426d-89ef-fb0e23a6d9c7|19020537-db2c-40f3-a438-8fe4aa1c5c7a / appendix-3|
|0|3|Quyết định 84/2026/QĐ-CTUBND của CT UBND Tỉnh Sơn La|68740571-19a7-46c9-9321-c096de25a2ac|ceecd689-76dc-4f65-b003-b19769c216d4 / article-5|

Citations/time/objective links: `{"citations": [], "temporal_context": [], "search_objectives": []}`

### gemini: COMPLETED

Issues: ["Nghĩa vụ trả nợ của người vay khi đến hạn", "Trách nhiệm thực hiện nghĩa vụ bảo lãnh của bên bảo lãnh"]

Mode/options: `{"mode": "bm25", "top_k": 3, "as_of_date": "2026-11-23", "allowed_usage_policies": ["EXPERIMENTAL_ONLY"]}`

- Query0: nghĩa vụ trả nợ của người vay tiền hợp đồng vay tài sản; tình huống người dùng: Tôi cho A vay tiền; B ký bảo lãnh; A không trả
- Query1: trách nhiệm của bên bảo lãnh khi người được bảo lãnh không thực hiện nghĩa vụ; tình huống người dùng: Tôi cho A vay tiền; B ký bảo lãnh; A không trả

|Query|Rank|Source title|Source ID|Chunk/provision|
|---|---|---|---|---|
|0|1|Quyết định 84/2026/QĐ-CTUBND của CT UBND Tỉnh Sơn La|68740571-19a7-46c9-9321-c096de25a2ac|9a511e38-6993-480b-a6d2-38ae07c2d206 / article-3-2|
|0|2|Thông tư 141/2026/TT-BTC của Bộ Tài chính|d199e164-5747-426d-89ef-fb0e23a6d9c7|15eab05a-8f91-479c-a2b7-28f9e13ebbe4 / appendix-3|
|0|3|Quyết định 125/2026/QĐ-CTUBND của CT UBND Tỉnh Đồng Tháp|e6ac127e-f1c8-4c74-966d-9d4fb1190558|770f1d65-af83-430b-a1ff-3d5559ed9492 / chapter-ii-article-4-clause-4|
|1|1|Nghị quyết 31/2026/NQ-HĐND của HĐND Tỉnh Đắk Lắk|363ef1e9-697e-4cf2-905c-e1f24a28b9cb|132faf53-8ab3-4c85-8335-68e08a20c5ec / article-3-clause-3-point-b|
|1|2|Quyết định 58/2026/QĐ-UBND của UBND Tỉnh Hưng Yên|5d85a3c5-e170-408f-a3f0-f0e1eeb3eb6b|35c9b307-d959-4c87-951e-138df5e6f4cd / chapter-ii-article-13-clause-3-point-b|
|1|3|Thông tư 141/2026/TT-BTC của Bộ Tài chính|d199e164-5747-426d-89ef-fb0e23a6d9c7|c5ecba64-8983-4fe5-883c-3107e033b13f / chapter-ii-article-10-clause-2-point-b|

Citations/time/objective links: `{"citations": [], "temporal_context": [], "search_objectives": [{"query_index": 0, "issue_indices": [0]}, {"query_index": 1, "issue_indices": [1]}]}`

## Attribution conclusion

Verified: source identity mismatch, scoped58-row coverage, missing temporal dates, preserved native ranking/occurrences, primary Q007 rejection. Provisional: judgments about which passages substantively answer an issue; no expert metrics. Query length affects ranking but is not proven the dominant cause. Retrieval algorithms are not proven defective by these observations. No production Query/Search change was justified by this bounded experiment.
