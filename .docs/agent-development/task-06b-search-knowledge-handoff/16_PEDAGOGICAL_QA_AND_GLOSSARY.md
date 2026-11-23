# Search Agent — học và vấn đáp từ cơ bản đến nâng cao

**50 câu hỏi có đáp án**, chia 5 nhóm. Đây là source-grounded learning resource; không biến thuật ngữ Agent thành năng lực LLM. Runtime examples OBSERVED ở 11; nguồn ký hiệu/ranges ở 18.

## Nhóm 1 — Trách nhiệm và boundaries

### 1. Search Agent giải quyết việc gì?

Nó thực thi kế hoạch tra cứu:validate plan/options, dựng requests, gọi service và giữ per-query responses. Nó không sinh câu trả lời hoặc kết luận pháp lý; nhờ vậy execution boundary có thể kiểm độc lập với Query rules.

Nguồn: [src/applications/tillegal/agents/search/agent.py:38–56](../../../src/applications/tillegal/agents/search/agent.py).

### 2. Tên Agent có đồng nghĩa LLM không?

Không. Toàn Search module chỉ schemas và coroutine orchestration; không có prompt hoặc inference call. Từ Agent mô tả vai trò chứ không chứng minh thuật toán học máy.

Nguồn: [src/applications/tillegal/agents/search/agent.py:3–56](../../../src/applications/tillegal/agents/search/agent.py).

### 3. Search có tạo embeddings không?

Không trực tiếp. Nó await retrieval.search(request); Dense branch của service mới gọi injected query_embedder.encode_query. End-to-end request có model work nhưng Search transport không tự implement encoder.

Nguồn: [src/application/services/retrieval_service.py:192–275](../../../src/application/services/retrieval_service.py).

### 4. Search có implement BM25 hoặc RRF không?

Không. Service dispatch bm25/dense/hybrid; hybrid helper dùng fusion. Search không đọc token/vector/branch scores để tính ranking. Phải phân biệt outer coordinator với algorithm owner.

Nguồn: [src/applications/tillegal/agents/search/agent.py:44–56](../../../src/applications/tillegal/agents/search/agent.py).

### 5. Entrypoint thực tế nhận gì?

Async search(plan:dict, retrieval: RetrievalService, options: SearchOptions)-> SearchState. Plan là query-derived data, options là trusted application context, retrieval là dependency được inject; annotations không tự kiểm duck-typed dependency.

Nguồn: [src/applications/tillegal/agents/search/agent.py:38–41](../../../src/applications/tillegal/agents/search/agent.py).

### 6. Vì sao Query và Search được tách?

Source chứng minh QuerySearch gọi understand rồi search; Query tạo QueryPlan, Search thực thi request transport. Rationale hợp lý là tách text rules khỏi side effects/config, nhưng source không tự đo lợi ích maintainability.

Nguồn: [src/query_search_bootstrap.py:20–21](../../../src/query_search_bootstrap.py).

### 7. QueryPlan có những fields nào?

original, intent, domain, temporal_scope, subqueries, clarification. Search model_validate toàn plan trước khi đọc; intent/domain/time được giữ trong plan nhưng không forward thành RetrievalRequest filters.

Nguồn: [src/applications/tillegal/agents/search/agent.py:40–44](../../../src/applications/tillegal/agents/search/agent.py).

### 8. Clarification nullable có nghĩa bỏ field được không?

Không. QueryPlan.clarification:str| None không có default nên vẫn required. Nullable cho phép giá trị None; optional-key là ý nghĩa khác, ví dụ total= False trên TypedDict.

Nguồn: [src/applications/tillegal/agents/query/agent.py:20–26](../../../src/applications/tillegal/agents/query/agent.py).

### 9. Thứ tự validation quan trọng thế nào?

Plan trước, options sau, rồi clarification guard, sau đó toàn bộ request tuple. Vì vậy malformed plan hoặc invalid options vẫn raise ngay cả khi input muốn clarification; không gọi service để “thử”.

Nguồn: [src/applications/tillegal/agents/search/agent.py:40–44](../../../src/applications/tillegal/agents/search/agent.py).

### 10. Clarification làm gì với retrieval calls?

Direct Search trả requests/responses rỗng và status CLARIFICATION_REQUIRED. Trong graph, router đã skip cả Search node. QueryPlan vẫn có subqueries; zero calls không đồng nghĩa zero subqueries.

Nguồn: [src/applications/tillegal/agents/search/agent.py:42–43](../../../src/applications/tillegal/agents/search/agent.py).

## Nhóm 2 — Validation và multi-query

### 11. Unknown fields của plan được xử lý ra sao?

Parsed QueryPlan mặc định ignore extras nhưng SearchState.plan giữ raw input object. Confidence tự thêm không trở thành feature; raw result và typed handoff.plan có thể khác về extra keys.

Nguồn: [src/applications/tillegal/agents/search/agent.py:40–43;51–56](../../../src/applications/tillegal/agents/search/agent.py).

### 12. Search có mutate hoặc copy plan không?

Function không ghi vào plan và return cùng object. Tests assert plan unchanged vàresult.plan is plan. Đây là preservation nhưng cũng aliasing:caller mutate raw dict sau return có thể đổi result.plan.

Nguồn: [src/applications/tillegal/agents/search/agent.py:43;51;56](../../../src/applications/tillegal/agents/search/agent.py).

### 13. Subqueries tối đa bao nhiêu?

Schema QueryPlan yêu cầu 1–4. Search nhận parsed list theo order, không tự chia thêm hoặc sửa text. External plan rỗng/năm subqueries bị Pydantic reject trước calls.

Nguồn: [src/applications/tillegal/agents/query/agent.py:25](../../../src/applications/tillegal/agents/query/agent.py).

### 14. Await loop có chạy queries concurrent không?

Không. Vòng for await từng request hoàn tất rồi mới tới request tiếp. Await có thể nhường event loop cho task khác nhưng không tự tạo task cho các subqueries còn lại.

Nguồn: [src/applications/tillegal/agents/search/agent.py:46–49](../../../src/applications/tillegal/agents/search/agent.py).

**Trả lời sai thường gặp:** Có await nên tự chạy đồng thời mọi query.

**Vì sao sai:** Await chỉ tạm dừng task hiện tại; for không schedule request tiếp trước completion.

**Cách trả lời đúng:** nêu cơ chế và ownership trong đáp án trên, trỏ source cụ thể, rồi giới hạn kết luận đúng layer. Đối chiếu runtime trace 11 nếu cần chứng minh thực thi.

### 15. Một subquery có một DB RPC không?

Không suy ra vậy. Search tạo một outer service call; service có thể đọc index, search, hydrate, postcheck vàhybrid chạy hai branches. Outer call count khác RPC count hoặc model inference count.

Nguồn: [src/application/services/retrieval_service.py:192–275](../../../src/application/services/retrieval_service.py).

### 16. top_k là per-query hay tổng toàn Search ?

Cùng options. top_k được đưa vào mỗi request; không có global budget subtraction.3 queries, k=5 cho tối đa 15 evidence occurrences nếu mọi response hợp lệ hoàn thành, không bảo đảm 15 unique chunks hoặc đủ 15 hits.

Nguồn: [src/applications/tillegal/agents/search/agent.py:44–56](../../../src/applications/tillegal/agents/search/agent.py).

**Trả lời sai thường gặp:** top_k 5 nghĩa tổng 5 chunks cho 3 queries.

**Vì sao sai:** Mỗi constructor nhận cùng k 5, không global counter; upper bound occurrences là 15 nếu mọi response hợp lệ hoàn thành.

**Cách trả lời đúng:** nêu cơ chế và ownership trong đáp án trên, trỏ source cụ thể, rồi giới hạn kết luận đúng layer. Đối chiếu runtime trace 11 nếu cần chứng minh thực thi.

### 17. Duplicate subquery có bị bỏ không?

Không. Text trùng vẫn tạo request ở mỗi vị trí và gọi lại service. Có thể cùng evidence IDs xuất hiện ở nhiều responses; unique constraint chỉ trong từng RetrievalResponse.

Nguồn: [src/applications/tillegal/agents/search/agent.py:44–48](../../../src/applications/tillegal/agents/search/agent.py).

### 18. Có multi-query fusion không?

Không. responses list đóng thành tuple nhưng không merge scores/evidence. Hybrid RRF nằm bên trong một service call, khác fusion giữa các subqueries. Không dùng từ aggregate để ngụ ý đã có global ranking.

Nguồn: [src/applications/tillegal/agents/search/agent.py:45–56](../../../src/applications/tillegal/agents/search/agent.py).

**Trả lời sai thường gặp:** Có nhiều queries thì đã có RRF giữa chúng.

**Vì sao sai:** Search không có fusion call; RRF ở service Hybrid xử lý backend branches trong một query.

**Cách trả lời đúng:** nêu cơ chế và ownership trong đáp án trên, trỏ source cụ thể, rồi giới hạn kết luận đúng layer. Đối chiếu runtime trace 11 nếu cần chứng minh thực thi.

### 19. NO_MATCH có làm Search dừng không?

Không. Nó khác FAILED; loop tiếp tục. Nếu xử lý hết, SearchState COMPLETED ngay cả mọi responses empty. Handoff NO_MATCH phụ thuộc tất cả evidence empty.

Nguồn: [src/applications/tillegal/agents/search/agent.py:49–56](../../../src/applications/tillegal/agents/search/agent.py).

### 20. FAILED ở query thứ hai giữ gì?

Responsefailed được append rồi return FAILED với requests prefix length 2 và hai responses. Kết quả query 1 còn nguyên; query 3 không chạy. Handoff ưu tiên RETRIEVAL_FAILED dù query 1 có evidence.

Nguồn: [src/applications/tillegal/agents/search/agent.py:48–55](../../../src/applications/tillegal/agents/search/agent.py).

**Trả lời sai thường gặp:** FAILED xóa hết prior evidence.

**Vì sao sai:** Append trước failure return vàtuple giữ history; packet failure vẫn chứa prior responses.

**Cách trả lời đúng:** nêu cơ chế và ownership trong đáp án trên, trỏ source cụ thể, rồi giới hạn kết luận đúng layer. Đối chiếu runtime trace 11 nếu cần chứng minh thực thi.

## Nhóm 3 — Options và Request

### 21. Exception ở query thứ hai có giống FAILED không?

Không. Không có try/except trong Search nên exception propagate và function không return SearchState. Recorder trong diagnostic còn prior history không có nghĩa application nhận được partial state contract.

Nguồn: [src/applications/tillegal/agents/search/agent.py:46–56](../../../src/applications/tillegal/agents/search/agent.py).

**Trả lời sai thường gặp:** Mọi lỗi đều thành response FAILED.

**Vì sao sai:** Unexpected exception không nằm response contract tại Search; không cócatch đểconvert.

**Cách trả lời đúng:** nêu cơ chế và ownership trong đáp án trên, trỏ source cụ thể, rồi giới hạn kết luận đúng layer. Đối chiếu runtime trace 11 nếu cần chứng minh thực thi.

### 22. Retrieval mode do ai chọn?

Application cung cấp SearchOptions.mode. Search chỉ forward; không suy từ intent, domain hoặc user text. Graph dùng pipeline.options kể cả state.options bị thay.

Nguồn: [src/applications/tillegal/graphs/legal_qa.py:39–46](../../../src/applications/tillegal/graphs/legal_qa.py).

### 23. Rerank có phải mode thứ tư không?

Không. Enum chỉ bm25, dense, hybrid. Rerank là config.enabled trong service chohybrid. Test profile tênrerank map options.mode thànhhybrid; mode=rerank thực bị reject.

Nguồn: [src/applications/tillegal/retrieval/contracts.py:13–16](../../../src/applications/tillegal/retrieval/contracts.py).

**Trả lời sai thường gặp:** Rerank là enum mode củaRequest.

**Vì sao sai:** Chỉba enum labels; profiletênrerank không thay schema.

**Cách trả lời đúng:** nêu cơ chế và ownership trong đáp án trên, trỏ source cụ thể, rồi giới hạn kết luận đúng layer. Đối chiếu runtime trace 11 nếu cần chứng minh thực thi.

### 24. as_of_date lấy từ temporal_scope không?

Không. SearchOptions. as_of_date được supplied độc lập và copy qua Request. Temporal mentions của Query không tự trở thành governance date hoặc chứng minh luật còn hiệu lực.

Nguồn: [src/applications/tillegal/agents/search/agent.py:18–21;44](../../../src/applications/tillegal/agents/search/agent.py).

### 25. Policies được xử lý thế nào?

Tuple StrictStr min 1, reject blank, strip từng value và dedup giữ thứ tự. Không lowercase, không suy policy từ câu hỏi và không tự authorize người dùng. Application phải quyết định allowed set.

Nguồn: [src/applications/tillegal/agents/search/agent.py:21–28](../../../src/applications/tillegal/agents/search/agent.py).

### 26. StrictInt có ích gì ở top_k ?

Nó reject bool hoặc string số thay vì để chúng làm số hợp lệ; constraints giới hạn 1..50. Không được nóibool True tự trở thành top_k 1 ở boundary này.

Nguồn: [src/applications/tillegal/agents/search/agent.py:19](../../../src/applications/tillegal/agents/search/agent.py).

### 27. SearchOptions có defaults không?

Bốn fields đều required. RetrievalRequest. top_k có default 10 nhưng Search luôn truyền options. top_k nên không dùng fallback đó trong integration này.

Nguồn: [src/applications/tillegal/agents/search/agent.py:18–21;44](../../../src/applications/tillegal/agents/search/agent.py).

### 28. Search có strip subquery không?

Không. Request.nonblank_query kiểmvalue.strip nhưngreturnvalue gốc. Service mới dùng query.strip cho preprocessing/encoding/ query_used. Giữ raw request query hỗ trợ đối chiếu với plan.

Nguồn: [src/applications/tillegal/retrieval/contracts.py:32–37](../../../src/applications/tillegal/retrieval/contracts.py).

### 29. Vì sao tab ở query thứ hai gây zero calls?

Subquery min_length chấp nhận một tab nhưng Request nonblank reject. Tuple comprehension eager chưa hoàn tất toàn batch nên loop service chưa bắt đầu; kể cả request đầu đã dựng local cũng chưa được gọi.

Nguồn: [src/applications/tillegal/agents/search/agent.py:44–47](../../../src/applications/tillegal/agents/search/agent.py).

**Trả lời sai thường gặp:** Request đầu hợp lệ sẽ gọi trước khi query 2 được validate.

**Vì sao sai:** Prebuild tuple nằm trướcloopawait nên toàn batch validation trướcI/O.

**Cách trả lời đúng:** nêu cơ chế và ownership trong đáp án trên, trỏ source cụ thể, rồi giới hạn kết luận đúng layer. Đối chiếu runtime trace 11 nếu cần chứng minh thực thi.

### 30. Date string trong options có được parse không?

Có thể theo Pydantic date field, ví dụ 2026-11-10 thànhdate. Invalid calendar string bị reject. Đây là trusted option parsing, khác Query user mention invalid date tạo clarification.

Nguồn: [src/applications/tillegal/agents/search/agent.py:20;41](../../../src/applications/tillegal/agents/search/agent.py).

## Nhóm 4 — Output/provenance/ranking

### 31. Request có run_id / request_id không?

Không trong RetrievalRequest schema. Service sinh response. request_id riêng; graph context IDs nằm state/handoff. Không có bảo đảm UUID response bằng request identifier của application.

Nguồn: [src/applications/tillegal/retrieval/contracts.py:23–44;113–128](../../../src/applications/tillegal/retrieval/contracts.py).

**Trả lời sai thường gặp:** Response UUID là requestID của API.

**Vì sao sai:** Schema không cóRequestID đầu vào vàservice tự sinh UUID; graphIDs là lớp khác.

**Cách trả lời đúng:** nêu cơ chế và ownership trong đáp án trên, trỏ source cụ thể, rồi giới hạn kết luận đúng layer. Đối chiếu runtime trace 11 nếu cần chứng minh thực thi.

### 32. SearchState là model hay dict?

 TypedDict mô tả dictionary vớiplan, requests, responses, status. Nó không phải BaseModel tự có model_dump_json hoặc runtime validators. Những models nested là typed Pydantic objects.

Nguồn: [src/applications/tillegal/agents/search/agent.py:31–35](../../../src/applications/tillegal/agents/search/agent.py).

### 33. Typed responses có bị serialize ngay khi Search return không?

Không. Listappend và tuple conversion giữ object identity/subtype. JSON trong tài liệu là diagnostic serialization để nhìn data; không phải implementation HTTP response.

Nguồn: [src/applications/tillegal/agents/search/agent.py:48;53;56](../../../src/applications/tillegal/agents/search/agent.py).

### 34. UnifiedEvidence bảo toàn provenance ra sao?

 Search không remap fields, giữ nguyên response.evidence. IDs, content/hash, source/chunk/time/policy metadata giữ theo dependency output. Tests identity và all-mode metadata hỗ trợ preservation, không chứng minh upstream provenance accurate.

Nguồn: [src/applications/tillegal/retrieval/contracts.py:65–110](../../../src/applications/tillegal/retrieval/contracts.py).

### 35. Hash MATCHED_STORED có nghĩa đoạn luật đúng không?

Không. Nó mô tả integrity so với stored content ở phạm vi service kiểm. Stored chunk có thể có breadcrumb, chưa verified raw quote; không bảo đảm hiệu lực hoặc applicability tình huống.

Nguồn: [src/applications/tillegal/retrieval/contracts.py:65–75](../../../src/applications/tillegal/retrieval/contracts.py).

**Trả lời sai thường gặp:** Hash đúng chứng minh pháp luật đúng.

**Vì sao sai:** Integrity không đánh giá authenticity/applicability hoặc rawquote.

**Cách trả lời đúng:** nêu cơ chế và ownership trong đáp án trên, trỏ source cụ thể, rồi giới hạn kết luận đúng layer. Đối chiếu runtime trace 11 nếu cần chứng minh thực thi.

### 36. Search có sửa score_kind hoặc rank không?

Không. Response đã có backend semantics trước khi Search append. Per-response validator kiểmrank 1..N/method; không có cross-response total order.

Nguồn: [src/applications/tillegal/retrieval/contracts.py:131–149](../../../src/applications/tillegal/retrieval/contracts.py).

### 37. Sau rerank có nên sort raw_score lại không?

Không. Reranked response giữ raw_score nghĩa RRF nhưng evidence order/rank theo Cross-Encoder selection. Sort RRF lại phá ranking downstream đã chọn; CE scores nằm reranking metadata riêng.

Nguồn: [src/applications/tillegal/retrieval/reranking_models.py:63–107](../../../src/applications/tillegal/retrieval/reranking_models.py).

**Trả lời sai thường gặp:** raw_score phải descending sau mọi ranking stage.

**Vì sao sai:** Rerank giữ RRF score, CEthayorder; consumerdùngevidence.rank.

**Cách trả lời đúng:** nêu cơ chế và ownership trong đáp án trên, trỏ source cụ thể, rồi giới hạn kết luận đúng layer. Đối chiếu runtime trace 11 nếu cần chứng minh thực thi.

### 38. Warnings/error có bị Search bỏ không?

Không có transformation trên native response. Mỗi response giữ warnings/error; SearchState không flatten thành top-level fields. Graph packet derive properties; graph errors channel chỉ chứa codes nhưng details vẫn ở packet.

Nguồn: [src/applications/tillegal/agents/search/agent.py:48–56](../../../src/applications/tillegal/agents/search/agent.py).

### 39. Graph Search node gọi QuerySearch.search không?

Không. Nó gọi Search function trực tiếp vớistate.plan vàpipeline dependencies. Query node đã gọi understand, nhờ vậy không chạy Query lần hai trong Search node.

Nguồn: [src/applications/tillegal/graphs/legal_qa.py:24–47](../../../src/applications/tillegal/graphs/legal_qa.py).

### 40. Graph final statuses khác Search status thế nào?

 Search COMPLETED map packet READY khi có evidence rồigraph SEARCH_COMPLETED; mọi empty→packet/graph NO_MATCH. Search FAILED → RETRIEVAL_FAILED. Execution exceptions không có final state thay thế.

Nguồn: [src/applications/tillegal/graphs/legal_qa.py:39–54](../../../src/applications/tillegal/graphs/legal_qa.py).

## Nhóm 5 — Graph, handoff, lifecycle và evidence

### 41. RETRIEVAL_FAILED có làm executor lifecycle FAILED không?

Không nhất thiết. Nếu graph trả packet failure bình thường, executor.succeed vẫn chạy. Lifecycle phản ánh computation completion; typed retrieval outcome là status bên trong output.

Nguồn: [src/framework/runtime/executor.py:65–77](../../../src/framework/runtime/executor.py).

**Trả lời sai thường gặp:** Graphbusinessfailure luôn làexecutionfailure.

**Vì sao sai:** Typedfailure làordinaryreturn nênexecutorsucceed; khi exception thìmới lifecyclefail/cancel.

**Cách trả lời đúng:** nêu cơ chế và ownership trong đáp án trên, trỏ source cụ thể, rồi giới hạn kết luận đúng layer. Đối chiếu runtime trace 11 nếu cần chứng minh thực thi.

### 42. JudgeHandoff do ai tạo và kiểm gì?

Graph Search node gọi from_search. Packet kiểmquestion=original, nonclarifying, counts/order, requestoptions, responseecho, stopatfirstfailure, statuses. Không Judge evaluation.

Nguồn: [src/applications/tillegal/state/legal_qa_state.py:44–93](../../../src/applications/tillegal/state/legal_qa_state.py).

### 43. READY chứng minh đủ evidence không?

Chưa. from_search chỉ kiểm Search nonfailed và có bất kỳ evidence nonempty. Không coverage/relevance/citation/legal sufficiency thresholds. Một phầnOK và phần khác NO_MATCH vẫn có thể READY.

Nguồn: [src/applications/tillegal/state/legal_qa_state.py:76–82](../../../src/applications/tillegal/state/legal_qa_state.py).

**Trả lời sai thường gặp:** READY nghĩa Judge đã chấp thuận.

**Vì sao sai:** Không Judge node; statuschỉ dựatrênevidence nonemptyvà Search nonfailed.

**Cách trả lời đúng:** nêu cơ chế và ownership trong đáp án trên, trỏ source cụ thể, rồi giới hạn kết luận đúng layer. Đối chiếu runtime trace 11 nếu cần chứng minh thực thi.

### 44. Warnings/errors properties có thành top-level JSON không?

Không tự thành fields vì dùng@property, không@computed_field. Mọi warning/error vẫn serialize ở từng response và properties derive khi access sau restore. Không nói “không top-level” nghĩa đã mất data.

Nguồn: [src/applications/tillegal/state/legal_qa_state.py:34–41](../../../src/applications/tillegal/state/legal_qa_state.py).

**Trả lời sai thường gặp:** Không có warnings top-level nghĩa warnings mất.

**Vì sao sai:** Nestedresponsesvẫngiữdata; propertiesderivekhi truy cập.

**Cách trả lời đúng:** nêu cơ chế và ownership trong đáp án trên, trỏ source cụ thể, rồi giới hạn kết luận đúng layer. Đối chiếu runtime trace 11 nếu cần chứng minh thực thi.

### 45. Vì sao packet dùng union response types?

Union cóReranked Hybrid, Hybrid, base để giữ fieldsfusion/reranking qua validation/serialization. Tests round-trip equality vàtype exact cho 4 profiles; identity chỉ trong process, không giữis qua JSON.

Nguồn: [src/applications/tillegal/state/legal_qa_state.py:15;30](../../../src/applications/tillegal/state/legal_qa_state.py).

### 46. Search có check response context từ service không?

Function chỉ đọcresponse.status rồi giữ object. Diagnostic fake response.query mismatch vẫn COMPLETED; JudgeHandoff.validate_context mới reject. Dependency contract trust không đồng nghĩa explicit validation ở Search.

Nguồn: [src/applications/tillegal/state/legal_qa_state.py:49–55](../../../src/applications/tillegal/state/legal_qa_state.py).

**Trả lời sai thường gặp:** Search validate cảresponse context.

**Vì sao sai:** Codechỉgiữresponse; packetvalidator mới so request/response fields.

**Cách trả lời đúng:** nêu cơ chế và ownership trong đáp án trên, trỏ source cụ thể, rồi giới hạn kết luận đúng layer. Đối chiếu runtime trace 11 nếu cần chứng minh thực thi.

### 47. Timeout của service khác timeout của graph thế nào?

Service catches timeout thành FAILED /detailTIMEOUT; Search có thể tạo failed packet. Outer GraphExecutor deadline cancel task vàraise TimeoutError, lifecycle FAILED, no final packet output. Không một timeout policy chung cho mọi tầng.

Nguồn: [src/framework/runtime/executor.py:47–63](../../../src/framework/runtime/executor.py).

### 48. Cancellation có dừng ngay model/ SDK worker không?

Không bảo đảm. Awaittask có thể bị cancel trong khi to_thread vẫn chạy; model lock giữ tớiworker finally vàRPC có HTTP timeout. Search không có cơ chế killthread; đừng suy từ coroutine cleanup sang native work terminated.

Nguồn: [src/integrations/embeddings/e5_query_encoder.py:27–44;69–101](../../../src/integrations/embeddings/e5_query_encoder.py).

**Trả lời sai thường gặp:** task.cancel đảm bảo DB/model đã dừng hoàn toàn.

**Vì sao sai:** to_thread worker có thểcònchạy; lock/timeoutsdownstreamkhông kill thread.

**Cách trả lời đúng:** nêu cơ chế và ownership trong đáp án trên, trỏ source cụ thể, rồi giới hạn kết luận đúng layer. Đối chiếu runtime trace 11 nếu cần chứng minh thực thi.

### 49. DI có nghĩa mỗi request tạo model mới không?

Không. Factory tạo service/adapters/wrappers; Search reuse injected instance. Encoder/scorer lazy-load weights first-use vàcache trên wrapper. Production owner có tạo factory mỗi request haykhông cần xem entrypoint lifecycle, không suy từfactory.

Nguồn: [src/retrieval_bootstrap.py:22–70](../../../src/retrieval_bootstrap.py).

### 50. In-memory graph tests và historical live chứng minh gì?

Offline graph allprofiles kiểm wiring/types/errors vớifake ports; Task 4 live kiểmstandalone 4 profiles, Task 5 live graph BM25. Chưa live graph Dense / Hybrid /rerank, production load hoặc semanticcorrectness. Không cộng historicaltests vào 320 mới.

Nguồn: [src/applications/tillegal/graphs/legal_qa.py:57–95](../../../src/applications/tillegal/graphs/legal_qa.py).

## Glossary

| Thuật ngữ | Nghĩa trong hệ thống hiện tại |
|---|---|
| Orchestration | Điều phối calls/validation/order; không đồng nghĩa thực hiện retrieval algorithm. |
| Dependency injection | Truyền service/options từ bên ngoài để kiểm và reuse. |
| QueryPlan | Kế hoạch 6 fields của Query; Search nhận serializeddict. |
| Subquery | Text/purpose cho một phần tra cứu; không có per-query trusted policy riêng. |
| SearchOptions | Trusted mode/ top_k /date/policies doapplication cấp. |
| RetrievalRequest | Pydantic request của một outerservicecall. |
| RetrievalMode | Enum bm25/dense/hybrid; rerank là configstage. |
| StrictInt | Integer validation không coercion bool/string như số tạifield này. |
| StrictStr | String validation reject non-string policy/query input. |
| Eager evaluation | Dựng toàn request tuple trước awaitloop. |
| Coroutine | Async function execution có thể suspend ởawait. |
| Sequential await | Chờ từng call trước call kế; khác fan-out. |
| Concurrency | Nhiều task có thể cùng tiến triển; không tự sinh từfor-await. |
| Fan-out | Schedule nhiều calls đồng thời; Search hiện không làm. |
| top_k | Max evidence per request; không global budget ở Search. |
| Occurrence | Một evidence entry; khác uniquechunk identity xuyên responses. |
| NO_MATCH | Valid retrieval outcome empty, không inputerror. |
| Classified failure | Response FAILED có typed public error detail. |
| Exception propagation | Ném lỗi vềcaller khi không cócatchconvert. |
| Partial history | Các responses trướcfailure, được giữ khi FAILED response. |
| Native response | Object gốc typed service trả; không flatten/remap. |
| Object identity | Quan hệis trong process; khác value equality sau JSON. |
| Subtype | Hybrid /reranked extensions của base RetrievalResponse. |
| UnifiedEvidence | Storedchunk và ranking/provenance/time/policy contract. |
| Provenance | Thông tin truy ngược chunk/structure/source/snapshot/offset. |
| Content hash | SHA-256 củapayload phục vụintegrity; không legaltruth. |
| Score kind | Nhãn nghĩa score: BM25 /COSINE_SIMILARITY/ RRF. |
| RRF | Fusion of backend ranks ở service Hybrid, không multi-query Search fusion. |
| Reranking | Post Hybrid modelstage, order có thể khác RRF rawscore. |
| Rank | Vị trí 1-based trong evidence tuple của một response. |
| as_of_date | Trusted retrievaldate; khác temporalmention. |
| Usage policy | Governance label/filter đượcapplication supply. |
| JudgeHandoff | Versionedtechnical packet cho future Judge, không verdict. |
| READY | Nonfailed Search có evidence; không sufficiency guarantee. |
| TypedDict | Typing củadict, không tựruntime validator. |
| Reducer | Merge rule củagraphchannel, vdappend_unique choerrors. |
| Lifecycle | Executor trạng thái computation, succeeded/failed/cancelled. |
| ContextVar | Async context binding cho runmetadata, không Requestfield. |
| Deadline | Giới hạn thời gian ở service/graph; outcome khác nhau. |
| Cancellation | Yêu cầu dừngasynctask; không universal native worker termination. |
| Lazy load | Loadweights lúc cần, lưu trênwrapper để reuse. |
| MODEL_BUSY | Nonblockingmodellock từchối overlapwork; không Search queue. |
| BEST_EFFORT | Observed consistency guard, khôngtransaction snapshot. |
| OBSERVED | Dữ liệu đã thu từexecution; phải ghi fake/live. |
| SOURCE-DERIVED | Kết luận từcode, không giả làm measuredresult. |
| ILLUSTRATIVE | Ví dụ giảng giải chưa khẳng định đã chạy. |
