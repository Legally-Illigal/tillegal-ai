# 19 — Read-only corpus coverage evidence

## Observed complete metadata scope

Source enumeration is ordered by id and paginated100 rows/page, capped1000. Actual58 rows fit one page; exact counts before/after58,58;58 unique IDs. Thus enumeration is complete for the records visible to CURRENT credentials at observation time, not every possible source outside that visibility. There is no transactional snapshot. Before/after source/index metadata identical.

Visible retrieval_chunks count2609; sparse index document_count2609 (chunks, not58 source documents). Count equality does not prove per-chunk index coverage. Index READY is operational, not a quality/coverage certification. Dense index model multilingual-e5-small,384 dimensions, normalized with query/passage prefix metadata. Both observed index identities/version/updated timestamps remained stable. No writes, crawler, index rebuild or schema changes.

## Exact identity versus mentions

The58 source metadata rows contain no document_number45/2019/QH14. An independent exact-equality read returns count0. This is demonstrable absence of that stored identity within the verified visible source-table scope. It is not proof that no excerpt/paraphrase/duplicate under another identity exists anywhere. Literal chunk query45/2019/QH14 returns count1, source60c5be9f-20d9-4897-977e-2059f2c59ff2, chunk2973a693-2276-4e4f-a233-f7038e4717e0, Nghị quyết25/2026/NQ-HĐND. It is Điều5 Khoản2 Điểmb of that resolution, merely referencing khoản2 Điều35 of the code.

Source demonstrably present: that local resolution; Thông tư141/2026/TT-BTC and Văn bản hợp nhất123/2026/VBHN-PL-VPQH are also present by metadata and returned chunks. Their presence does not establish suitability for general employment, civil, divorce or consumer questions.

Visible titles/numbers lack named primary civil/labour/family/consumer codes. Generic titles are not an exhaustive subject classifier: do not assert all relevant rules absent or require one particular statute as the only possible answer source. No external legal-source verification was performed; this is repository/corpus evidence only.

## Bounded literal content probes

Filters: all visible chunk rows regardless of policy/date; case-insensitive SQL ILIKE substring; exact count, up to10 returned full chunks. Counts0 mean literal phrase absent within that query-visible scope, not semantic absence across alternate wording/Unicode forms.

|Literal|Exact visible matching count|Interpretation|
|---|---|---|
|đơn phương chấm dứt|1|Literal only; inspect returned content|
|bảo lãnh|0|Literal only; inspect returned content|
|ly hôn|0|Literal only; inspect returned content|
|giao dịch dân sự|0|Literal only; inspect returned content|
|điều kiện có hiệu lực|0|Literal only; inspect returned content|
|không giao hàng|0|Literal only; inspect returned content|
|mua bán đất|0|Literal only; inspect returned content|
|45/2019/QH14|1|Literal only; inspect returned content|
|nghĩa vụ trả nợ|1|Literal only; inspect returned content|

The sole nghĩa vụ trả nợ match concerns public-policy credit publicity and use of allocated interest, not the full borrower/guarantor dispute. The sole đơn phương chấm dứt match is the local-resolution cross-reference. These give positive source evidence, not merely missing search results.

## Historical limitation

All58 visible sources have either effective_from after2010 or null;0 recorded dates<=2010-12-31,2 null. The saved Q0192010 request returns source issued2026-08-05 with no effective range. Local RPC eligibility permits null effective dates. That design preserves uncertain material; it cannot demonstrate historic applicability. A later consolidated text could describe older law, so neither publication year nor null dates alone prove legal inapplicability.

Owner handoff: corpus team should validate coverage/source identities and temporal metadata with a legal reviewer; Retrieval team can inspect candidate recall and ranking once suitable reference chunks are independently identified. These are follow-up recommendations, not work completed or database modifications.

Artifacts: [coverage before](../../evaluation/query_search/relevance_investigation/coverage.json), [after](../../evaluation/query_search/relevance_investigation/coverage_after.json), [literal/exact probes](../../evaluation/query_search/relevance_investigation/coverage_probes.json).

## Visible source inventory

|Source ID|Number|Title|Effective from|Effective to|
|---|---|---|---|---|
|05232619-fa5a-450c-9da0-3508242ff4b4|27/2026/NQ-HĐND|Nghị quyết 27/2026/NQ-HĐND của HĐND Tỉnh Đắk Lắk|2026-10-30|None|
|0530c818-69f1-4ea5-b2ab-848ed94426b0|41/2026/TT-BYT|Thông tư 41/2026/TT-BYT của Bộ Y tế|2027-01-01|None|
|05f53f68-4002-4826-b503-8982cd1022df|103/2026/QĐ-UBND|Quyết định 103/2026/QĐ-UBND của UBND Thành phố Cần Thơ|2026-11-16|None|
|06f63baf-82c6-4b69-bf4b-de823eadd210|363/2026/NĐ-CP|Nghị định 363/2026/NĐ-CP của Chính phủ|2026-11-11|None|
|0ec7ac3b-f0fb-4da6-9192-b01a8819796a|103/2026/QĐ-UBND|Quyết định 103/2026/QĐ-UBND của UBND Tỉnh Lâm Đồng|2026-11-20|None|
|1632d7cb-fb66-4389-b91b-820809e1432d|01/2026/VBHN-NĐ-BNG|Văn bản hợp nhất 01/2026/VBHN-NĐ-BNG của Văn phòng Chính phủ|None|None|
|1bf79acd-cf8d-48c8-a6ad-7cdacd68b6ad|85/2026/QĐ-UBND|Quyết định 85/2026/QĐ-UBND của UBND Thành phố Bắc Ninh|2026-11-01|None|
|1f2487f4-f41f-4cab-a4c3-f194b154e0fd|2981/QĐ-UBND|Văn bản hành chính liên quan 2981/QĐ-UBND của UBND Thành phố Bắc Ninh|2026-11-05|None|
|1f8f6429-ef52-4948-ad05-0d8a5784815b|205/2026/QĐ-UBND|Quyết định 205/2026/QĐ-UBND của UBND Tỉnh Cà Mau|2026-11-20|None|
|2d80d390-38b8-4535-8835-21dc71888b69|63/2026/NQ-HĐND|Nghị quyết 63/2026/NQ-HĐND của HĐND Tỉnh Tuyên Quang|2026-11-09|None|
|3625780d-1a54-4598-99f4-03d5301edde9|2744/QĐ-UBND|Văn bản hành chính liên quan 2744/QĐ-UBND của UBND Tỉnh Thái Nguyên|2026-08-25|None|
|363ef1e9-697e-4cf2-905c-e1f24a28b9cb|31/2026/NQ-HĐND|Nghị quyết 31/2026/NQ-HĐND của HĐND Tỉnh Đắk Lắk|2026-10-20|None|
|3ce40260-d6bd-44ec-8c61-7d2c11ed4795|127/2026/QĐ-UBND|Quyết định 127/2026/QĐ-UBND của UBND Tỉnh Ninh Bình|2026-10-06|None|
|450304fc-b390-46bc-8994-4fc8ba485c55|369/2026/NĐ-CP|Nghị định 369/2026/NĐ-CP của Chính phủ|2026-11-11|None|
|4b8ae460-689c-4759-9514-a18198a214ab|123/2026/VBHN-PL-VPQH|Văn bản hợp nhất 123/2026/VBHN-PL-VPQH của Văn phòng Quốc hội|None|None|
|4cb20317-2cb1-43fb-886d-443731536540|742/QĐ-UBND|Văn bản hành chính liên quan 742/QĐ-UBND của UBND Thành phố Bắc Ninh|2026-05-29|None|
|4f0f6c94-060d-429b-87d5-1cc1dafaf12c|34/2026/NQ-HĐND|Nghị quyết 34/2026/NQ-HĐND của HĐND Tỉnh Đắk Lắk|2026-10-30|None|
|5344a418-4cf5-4b1b-98ac-11295c4b10e9|34/2020/NQ-HĐND|Nghị quyết 34/2020/NQ-HĐND của HĐND tỉnh Kon Tum|2020-07-23|2026-11-06|
|56d86975-8d0d-417e-ae45-3c009c294acf|61/2026/QĐ-UBND|Quyết định 61/2026/QĐ-UBND của UBND Tỉnh Hưng Yên|2026-11-15|None|
|5b055611-278b-424c-b3a3-3db011172203|05/2026/UBTVQH16|Pháp lệnh 05/2026/UBTVQH16 của Uỷ ban Thường vụ Quốc hội|2027-01-01|None|
|5d85a3c5-e170-408f-a3f0-f0e1eeb3eb6b|58/2026/QĐ-UBND|Quyết định 58/2026/QĐ-UBND của UBND Tỉnh Hưng Yên|2026-10-22|None|
|5e363c33-decb-4520-b0b6-17d8987d05be|28/2026/NQ-HĐND|Nghị quyết 28/2026/NQ-HĐND của HĐND Tỉnh Đắk Lắk|2026-10-30|None|
|60c5be9f-20d9-4897-977e-2059f2c59ff2|25/2026/NQ-HĐND|Nghị quyết 25/2026/NQ-HĐND của HĐND Tỉnh Đắk Lắk|2026-10-30|None|
|652fa66e-6aca-4d64-8f78-2e3d47d59e15|32/2026/NQ-HĐND|Nghị quyết 32/2026/NQ-HĐND của HĐND Tỉnh Đắk Lắk|2026-10-20|None|
|669fe9d8-8596-4d61-a61a-84b171098f8a|36/2018/QĐ-UBND|Quyết định 36/2018/QĐ-UBND của UBND Tỉnh Đồng Nai|2018-09-17|2026-11-11|
|68740571-19a7-46c9-9321-c096de25a2ac|84/2026/QĐ-CTUBND|Quyết định 84/2026/QĐ-CTUBND của CT UBND Tỉnh Sơn La|2026-11-20|None|
|69401e45-80f3-4693-a6ea-8755000d33ae|51/2025/TT-BCT|Thông tư 51/2025/TT-BCT của Bộ Công Thương|2026-11-11|None|
|6eac2b3b-3f9a-4b5e-ad43-5a7d360b5a92|91/2026/QĐ-UBND|Quyết định 91/2026/QĐ-UBND của UBND Tỉnh Điện Biên|2026-11-20|None|
|7b0faf29-8023-4c00-85df-07e8d0bb4bd3|78/2026/QĐ-UBND|Quyết định 78/2026/QĐ-UBND của UBND Tỉnh Sơn La|2026-11-10|None|
|7cfa52a7-5d84-4a14-8fce-8cdd387839ed|94/2026/NQ-HĐND|Nghị quyết 94/2026/NQ-HĐND của HĐND Tỉnh Thái Nguyên|2026-10-14|None|
|7f05855c-6943-4aaa-ae58-7bdcf1c83f42|113/2026/QĐ-UBND|Quyết định 113/2026/QĐ-UBND của UBND Thành phố Đồng Nai|2026-11-11|None|
|83436efa-fabf-4ce5-a345-00d608919c78|178/2026/TT-BQP|Thông tư 178/2026/TT-BQP của Bộ Quốc phòng|2026-12-18|None|
|83bc28c9-93cc-44c4-a68e-74a2e58d4285|89/2026/QĐ-UBND|Quyết định 89/2026/QĐ-UBND của UBND Thành phố Bắc Ninh|2026-10-29|None|
|883a1777-2c2d-429d-aab8-70f7ea69b847|29/2026/NQ-HĐND|Nghị quyết 29/2026/NQ-HĐND của HĐND Tỉnh Đắk Lắk|2026-10-30|None|
|8da27a6c-2b46-4cb3-9e94-8253239130aa|35/2015/QĐ-UBND|Quyết định 35/2015/QĐ-UBND của UBND Tỉnh Đồng Nai|2015-10-29|2026-11-11|
|8f4b121a-29d6-4c16-9e7e-bbe1b149761e|23/2026/NQ-HĐND|Nghị quyết 23/2026/NQ-HĐND của HĐND Tỉnh Đắk Lắk|2026-10-30|None|
|8f9ea55b-ae3e-4dfa-9736-6c5e1b834ef4|60/2026/VBHN-NĐ-BQP|Văn bản hợp nhất 60/2026/VBHN-NĐ-BQP của Bộ Quốc phòng|2026-10-16|None|
|939ec7ab-9561-4de0-a35f-ec54910747c2|122/2025/QĐ-CTUBND|Quyết định 122/2025/QĐ-CTUBND của CT UBND Tỉnh Đồng Tháp|2025-11-01|2026-11-11|
|9d0ae27e-e13f-441d-95af-8a41a4525d6f|86/2026/QĐ-UBND|Quyết định 86/2026/QĐ-UBND của UBND Thành phố Bắc Ninh|2026-10-14|None|
|9dee9d3d-eae6-4cc9-b8a9-478905106b05|120/2026/QĐ-UBND|Quyết định 120/2026/QĐ-UBND của UBND Tỉnh Ninh Bình|2026-10-10|None|
|a7ad31ed-9de1-4fc6-b5f1-fc671a4366dd|47/2025/QD-UBND|Quyết định 47/2025/QD-UBND của UBND Thành phố Hà Nội|2025-08-01|None|
|b147dd06-0225-4a9d-aec3-fb3b991d56c9|51/2026/NQ-HĐND|Nghị quyết 51/2026/NQ-HĐND của HĐND Tỉnh Cà Mau|2026-07-10|None|
|b456f567-75ac-49c1-9a9f-90975ed6efc3|130/2026/QĐ-UBND|Quyết định 130/2026/QĐ-UBND của UBND Tỉnh Đắk Lắk|2026-11-05|None|
|b7984e1c-44ad-448c-a1c7-c4c623f4eb3b|128/2026/QĐ-UBND|Quyết định 128/2026/QĐ-UBND của UBND Tỉnh Đắk Lắk|2026-11-02|None|
|c6f5ba15-12c5-4157-8913-d87cb1574001|87/2026/QĐ-UBND|Quyết định 87/2026/QĐ-UBND của UBND Thành phố Bắc Ninh|2026-11-10|None|
|c86a0989-cb2f-42c4-a9ea-e04a7c934326|35/2026/NQ-HĐND|Nghị quyết 35/2026/NQ-HĐND của HĐND Tỉnh Đắk Lắk|2026-10-30|None|
|d199e164-5747-426d-89ef-fb0e23a6d9c7|141/2026/TT-BTC|Thông tư 141/2026/TT-BTC của Bộ Tài chính|2026-11-11|None|
|d8cb2282-cb29-445e-8add-8b5c02163590|104/2026/QĐ-UBND|Quyết định 104/2026/QĐ-UBND của UBND Tỉnh Cà Mau|2026-06-08|None|
|d9748e58-6f88-49df-8763-33e8169fe62d|90/2026/QĐ-UBND|Quyết định 90/2026/QĐ-UBND của UBND Tỉnh Điện Biên|2026-11-15|None|
|e14c22ff-0740-4dc6-88fc-a49f5f15a6f7|52/2026/QĐ-UBND|Quyết định 52/2026/QĐ-UBND của UBND Tỉnh Hưng Yên|2026-10-15|None|
|e5346883-5945-4839-8d81-1fde42ab68c7|84/2026/QĐ-UBND|Quyết định 84/2026/QĐ-UBND của CT UBND Thành phố Bắc Ninh|2026-10-25|None|
|e6ac127e-f1c8-4c74-966d-9d4fb1190558|125/2026/QĐ-CTUBND|Quyết định 125/2026/QĐ-CTUBND của CT UBND Tỉnh Đồng Tháp|2026-11-11|None|
|e8fd9cd5-06b7-4594-971e-be8f19d4d728|153/2026/QĐ-UBND|Quyết định 153/2026/QĐ-UBND của UBND Thành phố Hà Nội|2026-11-11|None|
|e9314766-3bc9-4a51-adc5-abcd152cc5e2|20/2026/QĐ-UBND|Quyết định 20/2026/QĐ-UBND của UBND Tỉnh Ninh Bình|2026-02-18|None|
|ec88104b-53da-478b-95cd-753dec610370|155/2025/NĐ-CP|Nghị định 155/2025/NĐ-CP của Chính phủ|2025-07-01|None|
|ed9cfdf6-efc5-4ed3-93f0-6d4471bd1e41|88/2026/QĐ-UBND|Quyết định 88/2026/QĐ-UBND của UBND Thành phố Bắc Ninh|2026-11-10|None|
|ee6c00f2-08d1-451c-84e0-2514a39896a8|33/2026/NQ-HĐND|Nghị quyết 33/2026/NQ-HĐND của HĐND Tỉnh Đắk Lắk|2026-10-30|None|
|fa475d91-60a5-4886-b46c-622014d02447|90/2026/QĐ-UBND|Quyết định 90/2026/QĐ-UBND của UBND Thành phố Bắc Ninh|2026-10-30|None|
