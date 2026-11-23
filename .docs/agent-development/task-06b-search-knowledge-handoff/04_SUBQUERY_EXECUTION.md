# Multiple subqueries: tuần tự và giữ nguyên các tập kết quả

Algorithm chính ở [Search44–56](../../../src/applications/tillegal/agents/search/agent.py): prebuild requests tuple, tạo responses list local, for từng request, `await retrieval.search(request)`, append object, kiểm FAILED. Không có gather, TaskGroup, queue hoặc cross-query fusion.

## Semantics đầy đủ

| Thuộc tính | Hành vi source-grounded |
|---|---|
|Cardinality |1..4 theo QueryPlan 25; clarification có thể chứa queries nhưng không gọi |
|Order |Parsed subqueries order → requests order → responses order |
|Concurrent? |Không trong một invocation; await loop chờ request trước hoàn tất |
|Calls |Một outer service call mỗi subquery được xử lý; internal Hybrid branch calls không tính là Search calls |
| top_k |Cùng options. top_k cho từng request, không chia tổng budget |
|Aggregation |Chỉ đóng per-query responses thành tuple; không tạo global ranking |
|Dedup |Không dedup duplicate queries hoặc cùng chunk giữa responses |
|Failure |Classified FAILED append rồi return, ngừng các subqueries còn lại |
|Prior results |Giữ các successful/no-match responses trước FAILED |
|Exception |Không catch; không return SearchState hoặc handoff partial cho caller |
|Requests khi FAILED |Sliced requests[:len(responses)] chỉ giữ prefix đã có response, không toàn prebuilt tuple |
|Shared state |Local lists/tuples theo invocation; service/options objects có thể dùng chung |

## Ví dụ số có điều kiện rõ ràng

 SOURCE-DERIVED: n=3, k=5, mọi call trả non-failed response hợp lệ →3 outer calls, 3 responses, từng response có tối đa 5 evidence theo RetrievalResponse 139–140. Tổng occurrences tối đa 15; không phải 15 unique chunks và không có guarantee đạt đủ 15. Với n<=4, k<=50, upper bound tương tự là 200 occurrences nếu cả 4 call hoàn thành. Không áp bound này cho số internal candidate hits của Hybrid /rerank hoặc ký tự payload.

 OBSERVED multi_success:3 explicit subqueries thuế/hợp đồng/bảo hiểm, top_k 2, real RetrievalService /fake ports.3 calls, 3 OK responses, mỗi 2 evidence, tổng 6 occurrences nhưng chỉ 2 chunk IDs distinct vì fixtures trả cùng corpus nhỏ. `max_active_calls=1`; events lần lượt start 1, return 1, start 2, return 2, start 3, return 3. Đây là quan sát bổ sung cho chứng minh sequential từ for/await, không benchmark throughput.

 OBSERVED duplicate_calls: hai text thuế giống nhau vẫn 2 calls, 2 NO_MATCH responses. Không có cache/dedup tại Search. Nếu Query đã loại duplicate topic thì đó là một rule upstream khác; base parts duplicates có thể còn.

 OBSERVED partial_failure:3 queries, call 1 OK/2 evidence, call 2 FAILED /empty, call 3 không chạy. SearchState.status= FAILED, requests/responses length 2, prior 2 evidence vẫn nằm response đầu. Handoff RETRIEVAL_FAILED ưu tiên failure dù có prior evidence. Không trộn partial history này với Hybrid strict branch-failure policy trong một service call.

 OBSERVED exception_second:call 1 OK, call 2 raise RuntimeError, call 3 không chạy. Diagnostic recorder giữ history quan sát được; Search không trả state chứa history đó. Trong graph, executor lifecycle FAILED và exception propagate, không tạo packet RETRIEVAL_FAILED để thay exception.

Evidence: [trace JSON](evidence/search-traces.json), [graph test155–165](../../../tests/graph/test_query_search_workflow.py), [service response validator132–149](../../../src/applications/tillegal/retrieval/contracts.py). Các cases ở 11 thể hiện full objects.

## Await không phải cùng lúc

Await nhường event loop khi dependency chờ I/O; task khác có thể tiến triển. Nó không tự schedule các requests kế tiếp. Nhiều workflow invocations có thể chạy concurrent qua application/gather, khác concurrency bên trong một Search invocation. Shared model locks có thể báo MODEL_BUSY ở downstream, nên không suy total throughput từ 3 calls tuần tự hoặc fake state-isolation test.
