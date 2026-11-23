# Hướng dẫn thuyết trình và vấn đáp

Trình bày graph hai node, nhánh clarification và Search terminal outcomes. Dùng stream tests giải thích QUERY_COMPLETED là intermediate. Phân biệt lifecycle execution status với native retrieval status và legal evidence sufficiency. Trình bày union JSON round-trip để chứng minh handoff giữ đúng subtype.

Ví dụ live summary thực:

```json
{
  "question": "Trích dẫn: hợp đồng dân sự",
  "options": {
    "mode": "bm25",
    "top_k": 5,
    "as_of_date": "2026-11-17",
    "allowed_usage_policies": [
      "EXPERIMENTAL_ONLY"
    ]
  },
  "retrieval_calls": 1,
  "graph_status": "SEARCH_COMPLETED",
  "handoff_status": "READY",
  "response_statuses": [
    "OK"
  ],
  "evidence_counts": [
    5
  ],
  "warning_codes": [
    "TEMPORAL_METADATA_INCOMPLETE",
    "TEMPORAL_METADATA_INCOMPLETE",
    "TEMPORAL_METADATA_INCOMPLETE",
    "TEMPORAL_METADATA_INCOMPLETE",
    "TEMPORAL_METADATA_INCOMPLETE"
  ],
  "error_codes": []
}
```

Đây là summary, không toàn packet. Full packet ở evidence/offline-handoff-example.json được đánh dấu fake fixture, không live Supabase.

1. **LangGraph điều phối gì ở đây?** Hai node và nhánh END. Rules Query và thuật toán retrieval vẫn thuộc module hiện hữu; graph chỉ chuyển state và quyết định có chạy Search dựa trên clarification.

2. **Vì sao dùng factory/compiler/executor cũ?** Chúng đã có logic thực và foundation/executor tests. Dùng lại giúp context, lifecycle, deadline và cancellation tuân convention thay vì tạo framework song song.

3. **Graph pháp lý trước task có hoạt động không?** Không có workflow ở target: legal_qa.py và legal_qa_state.py chỉ docstring. Task hoàn thiện hai stub cho Query/Search scope, không tạo full legal QA graph.

4. **Tại sao không gọi QuerySearch.search ở Search node?** Method đó gọi understand rồi search. Query node đã chạy understand, nên Search node gọi underlying Search entrypoint với cùng injected pipeline để tránh phân tích Query hai lần.

5. **Query node nhận input nào?** state.question do wrapper đưa vào, run/request IDs đã từ ExecutionContext. Existing understand kiểm input;node không copy validation hoặc truy cập database.

6. **QueryPlan có đổi contract không?** State vẫn sáu-field dict original/intent/domain/temporal_scope/subqueries/clarification. Handoff validate bằng typed QueryPlan nhưng không thêm legal fields.

7. **Original có được normalize không?** Original giữ đúng đối số kể cả whitespace/NFD. Chỉ subquery text được xử lý NFC;test theo dõi original qua graph và JSON handoff.

8. **Clarification kết thúc thế nào?** Query node đặt CLARIFICATION_REQUIRED và route end. Stream chỉ có query event;Search node không chạy và zero Retrieval calls.

9. **Ngày31/02 có thành retrieval no-match không?** Không. Query giữ message cần kiểm ngày và graph dừng trước Search;không gọi Supabase để tìm dữ liệu dựa trên ngày bất khả thi.

10. **Mode/date/policy lấy ở đâu?** Trusted SearchOptions của pipeline do application cấp. Query temporal text và domain không ghi đè quyền hoặc thời điểm runtime;schema validation chưa thay thế authorization.

11. **Model có bị khởi tạo mỗi node không?** Không. Application tạo pipeline trước rồi workflow compile một lần. Nodes giữ cùng service/options;lazy model loading/caching vẫn do Retrieval bootstrap và adapters hiện hữu.

12. **Graph dừng ở đâu khi có evidence?** Search tạo JudgeHandoff READY rồi graph END. Không có edge hoặc call đến Judge chưa được triển khai.

13. **QUERY_COMPLETED khác SEARCH_COMPLETED?** QUERY_COMPLETED là intermediate sau plan trước I/O, thấy trong stream. SEARCH_COMPLETED là Search hoàn tất không FAILED và ít nhất một response có evidence.

14. **NO_MATCH có phải exception không?** Là native valid outcome empty evidence, no error. Graph có handoff NO_MATCH và executor có thể SUCCEEDED vì đã thực thi workflow xong.

15. **RETRIEVAL_FAILED có khiến lifecycle FAILED không?** Classified service failure là dữ liệu đã xử lý, nên lifecycle có thể SUCCEEDED. Phải đọc graph/handoff/response status để xác định retrieval outcome;không dùng lifecycle làm legal/retrieval correctness.

16. **Unexpected exception được xử lý sao?** GraphExecutor ghi lifecycle FAILED và propagate exception. Không trả final successful state hoặc tạo handoff giả từ responses thiếu.

17. **QueryInputError có giữ nguyên type không?** Có. Graph không catch rồi đổi thành RuntimeError hoặc no-match. Tests invalid type/blank/control assert QueryInputError propagate và service chưa gọi.

18. **Timeout của service khác graph deadline thế nào?** Service timeout có thể trả FAILED/TIMEOUT, graph giữ failed packet. Outer graph deadline khiến executor cancel invocation và raise TimeoutError, không có packet mới trả về.

19. **Cancellation đã kiểm những đường nào?** Token cancellation sau Search bắt đầu và caller task.cancel đều được kiểm, bao cleanup cooperative fake và lifecycle CANCELLED. Token precancel trước start theo convention executor có thể để lifecycle CREATED.

20. **Native inference có dừng ngay khi cancel không?** Không có bảo đảm đó. Encoder/reranker có threading lock giữ tới khi worker thoát;Task 5 chỉ kiểm cooperative async cancellation, không chạy lại native interruption tests live.

21. **Hai request cùng workflow có lẫn state không?** execute tạo initial dict mới và graph không saver. Tests repeated/concurrent cùng instance kiểm run IDs, questions, results và errors không tái dùng từ lượt trước.

22. **Reducer errors dùng để làm gì?** Kế thừa append_unique của WorkflowState cho safe service codes top-level. Native typed error detail vẫn trong response, error codes không thay thế full diagnostic contract.

23. **Handoff gồm gì?** Original question, typed plan, context request/run IDs, options, requests/responses và technical/search statuses. UnifiedEvidence cùng warnings/errors ở canonical responses, giữ per-query association.

24. **UnifiedEvidence có bị đổi dạng không?** Không map sang EvidenceBundle cũ. Tests assert cùng response object giữa search_result và packet, JSON round-trip vẫn giữ evidence/metadata.

25. **Tại sao cần union response subclasses?** Hybrid có fusion;reranked có thêm reranking. Nếu parse/serialize qua base-only schema có thể mất hoặc từ chối fields;union cụ thể trước giúp round-trip đúng subtype.

26. **Warnings/errors có top-level JSON keys không?** Không;đó là properties convenience. Serialized data nằm responses[i].warnings/error và properties được derive lại sau parse mà không duy trì duplicate state.

27. **READY nghĩa đủ căn cứ pháp lý không?** Chỉ có technical retrieval output hoàn tất và có evidence. Điều kiện/ngoại lệ/hiệu lực/applicability là đánh giá của Judge tương lai, không suy từ READY hoặc raw_score.

28. **Nếu query thứ hai thất bại?** Search dừng và packet giữ prior responses cùng failed response để đối soát, nhưng status RETRIEVAL_FAILED. Caller không dùng prior successful evidence như normal READY packet.

29. **Có confidence/correctness score mới không?** Không. BM25/cosine/RRF/reranker giữ nghĩa ranking;không thêm legal sufficiency hoặc verified labels.

30. **Graph có checkpoint mới không?** Không attach saver, không mở Postgres setup. In-memory graph và explicit handoff JSON được kiểm, durable checkpoint/resume/ACL cần scope riêng.

31. **JSON round-trip chứng minh gì?** Schema packet tái tạo đúng UUID/date/tuples/subtypes/nulls và metadata ở tests. Chưa chứng minh checkpoint lifecycle hoặc backward migration qua version tương lai.

32. **Có thể override options qua raw state không?** Search node luôn lấy pipeline.options. Test thay state.options sang mode khác không đổi actual request;application vẫn phải bảo vệ dependency injection khỏi input không tin cậy.

33. **Graph đã gọi Supabase thật chưa?** Có đúng một BM25 smoke:1 call, OK, 5 evidence, READY trong3.062241s. Warnings TEMPORAL_METADATA_INCOMPLETE và IDs/hash/round-trip đều được giữ.

34. **Cả bốn modes đã live qua graph chưa?** Chưa. Graph4 profiles được kiểm offline với real service/fake ports. Task 4 live modes là historical retrieval pipeline evidence trước khi nối graph.

35. **Có thể cộng30 graph tests với320 không?** Không.30 nằm trong 320 regression. Lượt26/316 trước và các reruns không tạo thêm distinct cases.

36. **Caller xử lý execution exception thế nào?** Dùng exception/lifecycle riêng, không tái sử dụng packet run trước. Lifecycle diagnostic có thể chứa underlying text, nên không xuất verbatim ra public client.

37. **Unknown provenance có tự được điền không?** Không. UnifiedEvidence có thể thiếu source URL/snapshot/offset;graph giữ unknown. Stored chunk có breadcrumb và hash check chưa phải verified raw legal quote.

38. **Bước tiếp theo đã làm Judge chưa?** Chưa. Task 5 dừng ở boundary được version hóa;Judge cần tiêu chí/task riêng cho sufficiency và cách xử lý gaps/failures mà không thay nghĩa technical statuses.
