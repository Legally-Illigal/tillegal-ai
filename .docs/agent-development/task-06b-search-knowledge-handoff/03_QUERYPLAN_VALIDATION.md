# Receiving QueryPlan: thứ tự validation và aliasing

Source [Search40–44](../../../src/applications/tillegal/agents/search/agent.py) xác định thứ tự, không phải phỏng đoán dựa tên model:

1. `parsed = QueryPlan.model_validate(plan)` tạo parsed schema view của input.
2. `options = SearchOptions.model_validate(options)` kiểm trusted runtime context.
3. Nếu parsed.clarification truthy, trả raw plan cùng requests/responses rỗng.
4. Nếu không, dựng toàn bộ tuple RetrievalRequest cho mọi parsed.subqueries.
5. Chỉ sau bước 4 thành công mới bắt đầu await service.

Do đó không có I/O nếu plan/options/request validation thất bại, kể cả request thứ hai bị invalid sau request thứ nhất hợp lệ. Cũng không có guarantee trả clarification khi plan malformed hoặc options invalid: hai validations trước guard vẫn fail.

## Những kiểm tra cụ thể

 QueryPlan yêu cầu sáu fields theo [QueryPlan20–26/Subquery15–17](../../../src/applications/tillegal/agents/query/agent.py). Subqueries count 1..4; purpose chỉ lookup/question_part/topic; text length 1..10000. Không có nonblank Subquery validator. `"\t"` có length 1 nên qua QueryPlan; receiving RetrievalRequest.nonblank_query 34–37 mới reject. QueryPlan không tái chạy calendar parser của understand cho temporal_scope tự supplied.

| Case OBSERVED | Plan validation | Guard/request validation | Service calls |
|---|---|---|---|
|one_bm25: valid quote_lookup |Pass |Một request |1 |
|clarification: Có được không? |Pass |Return CLARIFICATION_REQUIRED |0 |
|missing_plan: {} hoặc none_plan |Fail |Chưa tới options/guard |0 |
|empty_subqueries hoặc five_subqueries |Fail cardinality |Chưa guard |0 |
|empty_text |Fail min_length |Chưa requests |0 |
|unsupported_intent |Fail Literal |Không fallback label |0 |
|clarification_invalid_plan |Fail dù có message |Không skip schema |0 |
|tab_second:3 parts với tab ở giữa |Pass |Request query nonblank fail |0, dù request đầu hợp lệ |
|clarification_invalid_options |Pass plan |Fail options trước guard |0 |
|extra_plan_field |Parsed ignore confidence |Raw plan vẫn giữ confidence |1; không có confidence feature |
|spaces_retained |Pass |Request query giữ spaces |1; service query_used strip |

Đây là diagnostics mới [search-traces.json](evidence/search-traces.json); fake hoặc real service/fake ports ghi rõ từng case. Source-derived consequence: clarification empty string không skip vì if dùng truthiness. Không gán empty-string behavior này là clarification message được Query hiện sinh ra.

## Search có sửa plan không?

Không có assignment vào plan/nested fields trong Search. Return dictionaries dùng `"plan": plan` giữ đúng object caller đưa vào, không parsed. model_dump. Test [test_response_identity_and_plan_unchanged88–95](../../../tests/unit/applications/tillegal/test_query_search.py) kiểm content unchanged; [multimode56–78](../../../tests/unit/applications/tillegal/test_query_search_multimode.py) còn assert `result["plan"] is plan`.

Hệ quả: caller có thể mutate raw dict sau call; không được mô tả SearchState là immutable snapshot. Parsed QueryPlan mới chỉ dùng để đọc/validate; ignored extras không có nghĩa extras bị xóa khỏi raw result.plan. JudgeHandoff.plan là typed QueryPlan representation khác, nên extras có thể không còn ở packet.

 Search không xác minh response request context tại đây. Case context_mismatch cho thấy fake dependency trả response.query khác request vẫn được Search giữ nguyên và COMPLETED; JudgeHandoff.validate_context từ chối sau đó. Interface trust khác với receipt validation; không claim Search tự kiểm mọi outgoing/incoming association.

 Pydantic behavior phụ thuộc models/config hiện tại; không mô tả mọi validation là dự án tự viết. Inputs qua model_construct hoặc model_copy bypass validation là ngoài đường caller thông thường, không được dùng để suy toàn bộ trust boundary đã được bảo vệ.
