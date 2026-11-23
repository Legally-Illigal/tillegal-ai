# Boundary Query → Search,không mở rộng kiến thức Search internals

Source [Search38–56](../../../src/applications/tillegal/agents/search/agent.py),[QuerySearch20–21](../../../src/query_search_bootstrap.py),[Graph24–40](../../../src/applications/tillegal/graphs/legal_qa.py).

## Exact object và receiving validation

Standalone orchestration gọi `search(understand(question), self.retrieval, self.options)`. Graph gọi `search(state["plan"], self.pipeline.retrieval, self.pipeline.options)`. First argument là six-field Python dict,không JSON string hoặc QueryPlan instance từ public understand.

Search40 parse `QueryPlan.model_validate(plan)`;41 parse options;42 check parsed.clarification;44 prebuild RetrievalRequest cho từng parsed.subqueries.text. Việc tạo request nằm downstream boundary,không thuộc Query. Không gọi model_validate_json ở receiving boundary này.

| Field | Receiving behavior | Giữ hay biến đổi |
|---|---|---|
|original |Schema check,str length;không gửi làm query nếu đã có subquery |Raw plan được giữ trong SearchState.plan |
|intent |Literal validation |Không chọn retrieval mode |
|domain |Literal validation |Không chuyển policy/filter |
|temporal_scope |list[str] validation |Không tự đổi as_of_date |
|subqueries |Cardinality/schema validate rồi đọc text |Mỗi text thành request.query;purpose không routing |
|clarification |Truthy guard |Requests/responses rỗng khi valid plan cần làm rõ |

SearchState.plan vẫn là input dict (tests assert identity);parsed QueryPlan là model khác để validate/read fields. JSON string không phải expected argument. Handoff phía sau dùng typed QueryPlan,ngoài scope Query learning sâu hơn,nhưng không làm mất original trong normal entrypoint.

Extra keys:QueryPlan default extra-ignore có thể bỏ extras trong parsed representation;raw SearchState.plan vẫn giữ nếu caller tự thêm. Đây không phải guarantee public arbitrary-extra round-trip. Confidence extra không làm Query có confidence score.

## Zero/malformed cases

- subqueries=[]:ValidationError trước guard hoặc I/O,kể cả clarification có message.
- Blank text=' ' có thể qua Subquery min_length nhưng RetrievalRequest.nonblank_query reject trước mọi service calls,vì requests được prebuild toàn bộ.
- Tab-only middle clause được observed từ understand là ví dụ thật cho trường hợp này. Graph đã vào Search node nhưng zero retrieval calls và exception propagate.
- Valid plan+clarification:direct Search trả CLARIFICATION_REQUIRED/requests()/responses();graph bypass Search hoàn toàn.
- Malformed intent/type/thiếu required fields:ValidationError,không invented fallback.

## Trusted options khác Query context

SearchOptions do application cấp gồm mode bm25/dense/hybrid,top_k1–50,as_of_date date và allowed_usage_policies không rỗng. QueryPlan không có những config fields này. Model/rerank paths và Supabase settings thuộc bootstrap. Search không suy quyền chỉ từ domain hoặc user text,Query không truy cập Supabase.

Cuốn Query guide dừng tại việc requests đi vào service. Ranking/evidence assembly,Hybrid/RRF và rerank là Retrieval study topics;không gán chúng cho Query Agent.
