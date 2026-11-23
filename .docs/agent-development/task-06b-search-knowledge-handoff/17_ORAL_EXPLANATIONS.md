# Giải thích miệng và blackboard walkthrough

Các mốc 60 giây/3 phút là mục tiêu luyện tập, chưa đo tốc độ nói của sinh viên. Nội dung dựa current source; ví dụ blackboard lấy observations của graph_failure, không thêm hành vi Judge.

## Script khoảng 60 giây

 Search Agent hiện tại của Tillegal là coroutine điều phối deterministic. Nó nhận QueryPlan dạng dict, RetrievalService và trusted SearchOptions. Trước khi đọc dữ liệu, nó validate plan rồi options, nếu có clarification thì dừng. Nếu không, nó dựng toàn bộ requests từ subquery.text cùng mode, top_k, ngày và policy do application cấp.

 Search await từng request theo thứ tự, giữ nguyên typed response và dừng ở FAILED, đồng thời giữ các responses trước đó. Nó không tạo embeddings, không implement BM25 / RRF /reranking và không merge evidence giữa các subqueries; những thuật toán thuộc service downstream.

Trong LangGraph, Search node gọi function này, rồi tạo JudgeHandoff với original question, IDs, options, requests và responses. READY chỉ nói có evidence và không retrieval failure, chưa phải đánh giá đủ căn cứ pháp lý. Exception không được đổi thành response thành công. Tests và trace phải ghi rõ fake backend hay live evidence lịch sử.

Nguồn: Search 38–56; graph 39–54; JudgeHandoff 44–93, tra [source index18](18_SOURCE_SYMBOL_INDEX.md).

## Script khoảng 3 phút

Em bắt đầu từ trách nhiệm. Query phân tích câu hỏi thành kế hoạch, còn Search biến kế hoạch đó thành các retrieval calls có cấu hình tin cậy. RetrievalService mới sở hữu preprocessing, index checks, backend calls, hydration, fusion hoặc rerank. Vì vậy tên Search Agent không có nghĩa một LLM tự quyết mọi bước.

Signature là async search(plan:dict, retrieval: RetrievalService, options: SearchOptions)-> SearchState. Câu lệnh đầu validate toàn QueryPlan, sau đó validate SearchOptions. Nếu clarification truthy thì trả hai tuples rỗng. Nếu plan hoặc options malformed thì exception xảy ra trước guard, không service call.

Trong đường bình thường, tuple comprehension dựng toàn bộ RetrievalRequest trước khi I/O. Query lấy nguyên subquery.text; mode, top_k, date và policies từ options. Domain, temporal_scope, purpose và original không tự biến thành filters. Policy validator strip và dedup giữ thứ tự; query validator chỉ kiểm nonblank rồi giữ text gốc. Vì vậy một tab-only clause thứ hai có thể qua QueryPlan rồi làm request construction fail với 0 calls cả batch.

Loop dùng for và await, nên sequential trong một invocation. top_k áp từng subquery, không tổng.3 queries với k 5 có tối đa 15 evidence occurrences nếu mọi response hợp lệ hoàn thành; không có guarantee unique hoặc đủ 15. Duplicate text vẫn gọi lại. Search không trộn ranks hoặc tính score mới.

Mỗi native response được append đúng object, nên subtype Hybrid /reranked, metadata, hash, ranking, warnings vàerror được giữ. NO_MATCH không làm loop dừng. FAILED được append rồi return failed prefix, các queries sau không chạy. Unexpected exception lại propagate, không có partial SearchState return. Content hash đúng không chứng minh đoạn luật đúng hoặc áp dụng cho tình huống.

Ở graph, Query node gọi understand trực tiếp, router skip Search nếu clarification. Search node gọi Search với pipeline dependencies, không tin options bị sửa trong state, sau đó tạo JudgeHandoff. Packet validator kiểm original context, counts, order, options, response echo và failure sequence. Union response types giữ fusion/reranking qua JSON. Warnings/errors là properties derive từ nested responses, không tự thành top-level JSON fields.

Packet READY map graph SEARCH_COMPLETED; mọi response empty map NO_MATCH; classified failure map RETRIEVAL_FAILED. Lifecycle executor vẫn có thể succeeded với packet failure, vì graph computation đã hoàn tất. Outer timeout/cancel hoặc exception có lifecycle khác và propagate; không có Judge verdict được giả lập.

Factory tạo dependencies để reuse, lazy model loading thuộc adapters. In-memory isolation không chứng minh production client lifecycle hoặc tenant ACL. Lượt mới 320 tests offline pass; historical Task 4 live standalone all profiles, Task 5 chỉ graph BM25. Chưa có legal sufficiency, production load hoặc live graph all-mode verification mới trong task này.

## Blackboard: một execution graph_failure đầy đủ

 OBSERVED source: [search-traces.json](evidence/search-traces.json), graph_traces.graph_failure. Backend synthetic Recorder; không database/model. Raw question `thuế; hợp đồng; bảo hiểm`. Options mode=bm25, top_k 2, as_of_date 2026-11-10, policy(EXPERIMENTAL_ONLY,). ExecutionContext run_id =graph_failure, request_id =request-graph_failure.

```text
Workflow.execute
 initial={question,run_id,request_id} mới
       |
Query node -> understand(question)
 plan={
   original: 'thuế; hợp đồng; bảo hiểm',
   intent: legal_question, domain: unknown, temporal_scope: [],
   subqueries: [
      {text:'thuế',purpose:question_part},
      {text:'hợp đồng',purpose:question_part},
      {text:'bảo hiểm',purpose:question_part}],
   clarification: None}
       |
route_query(None) -> search
       |
Search node -> search(plan,pipeline.retrieval,pipeline.options)
 plan validate -> options validate -> no clarification
 eager requests tuple: [R1(thuế),R2(hợp đồng),R3(bảo hiểm)]
 all same mode/top_k/date/policies
       |
 await service.search(R1)
    -> NO_MATCH, empty evidence, FIXTURE_WARNING
 append response1
       |
 await service.search(R2)
    -> FAILED, empty evidence, error FIXTURE_FAILURE
 append response2 -> response.status == FAILED
       |
 SearchState={plan:same raw dict,
              requests:(R1,R2),
              responses:(response1,response2),status:FAILED}
 R3 prebuilt nhưng không service call,không còn trong returned requests
       |
 JudgeHandoff.from_search(...)
    status RETRIEVAL_FAILED vì Search status FAILED
    validate original/counts/query/options/response echo/failure sequence
    requests/responses count2 <= plan.subqueries count3
       |
 graph update:
    search_result=SearchState
    handoff=typed packet
    status=RETRIEVAL_FAILED
    errors=[FIXTURE_FAILURE]
       |
 END -> executor lifecycle succeeded -> caller nhận graph state
```

Trace full warnings/IDs/native response values ở 11/ JSON; diagram dùng projections để vẽ bảng. Không lấy packet request_id so bằng UUID riêng từng response. Nó là context identity khác.

## Các câu phản biện sau khi vẽ

- Nếu call 2 ném RuntimeError thay vì trả FAILED thì sao? Không đến packet/graph completed update; executor failed vàraise, nhưgraph_exception observed.
- Nếu call 1 có evidence thì sao? Classified failure vẫn thắng. Directpartial_failure đã observed giữ 2 evidence trướcfailed, handoff RETRIEVAL_FAILED; không tự giả đây là một execution mới củagraph_failure.
- Nếu mọi call NO_MATCH ? Search COMPLETED, packet/graph NO_MATCH, lifecycle succeeded.
- Nếu chỉ query 2 làtab? Requestconstruction fail trướcloop, nên 0 calls, không phải call 1 trước.
- Nếu packet READY ? Không Judge verdict; phải kiểm sufficiency ở layer chưa implement.
