# Deterministic và Gemini trong compiled graph

> Ghi chú publication: tài liệu ghi lại implementation/acceptance Phase A. Candidate PR được kiểm thử lại độc lập trên main sau V2; trạng thái Git/CI mới nhất được ghi trong FINAL_MAIN_INTEGRATION_REPORT.md (local). Source links đã đổi sang đường dẫn tương đối để review trên GitHub.

|Đặc điểm|Deterministic|Semantic dependency được inject|
|---|---|---|
|Cấu hình|QuerySearch.query_agent=None; factory mặc định deterministic|Factory semantic_mode=gemini hoặc caller cấp query_agent đã cấu hình|
|Node được compile|query sync cũ|query_semantic async|
|Hiểu câu hỏi|understand(question)|await existing_agent.understand(question)|
|Model call|0|Ordinary QA hợp lệ: 1; guard cũ có thể 0|
|Plan|QueryPlan V1|Cùng QueryPlan V1, thường analysis_method=llm|
|Search/options/handoff|Giữ nguyên|Cùng Search/options/handoff|
|Provider lỗi|Không có provider|Propagate QueryAnalysisError; không fallback/retry|
|Request state|Mới cho mỗi invocation|Mới cho mỗi invocation; agent reusable không giữ plan per-request|

Nguồn: [QuerySearchNodes.query](../../../src/applications/tillegal/graphs/legal_qa.py#L24); [QuerySearchNodes.query_semantic](../../../src/applications/tillegal/graphs/legal_qa.py#L35); [create_query_search](../../../src/query_search_bootstrap.py#L28).

## Phân biệt mode

Business qa/verify trong V2 không đổi; Phase A không triển khai Verify. Semantic planner deterministic/gemini được caller chọn qua composition/injection. Retrieval bm25/dense/hybrid và rerank config vẫn do SearchOptions/native bootstrap quản lý. Không suy ba loại mode này từ nhau, không cho user question ghi đè trusted options.

SemanticQueryAgent hiện có deterministic input/date/lookup/clarification guards. Vì vậy lookup hoặc clarification có thể không gọi Gemini; đó là hành vi guard trước provider, khác fallback sau lỗi. Node graph không thêm rule mới hoặc thay prompt. Nguồn: [SemanticQueryAgent.understand](../../../src/applications/tillegal/agents/query/semantic.py#L48).

## Async và sync API

Dùng QuerySearchWorkflow.execute, compiled graph.ainvoke hoặc graph.astream. Giữ method query sync để caller/test cũ dùng trực tiếp. Workflow đầy đủ vốn có async Search, nên không quảng cáo .invoke sync cho QA toàn luồng kể cả deterministic.

Với cấu hình semantic, compiled graph.invoke bị LangGraph từ chối ngay tại query bằng TypeError “No synchronous function provided”, không gọi model/retrieval hoặc chuyển sang deterministic. Đã test trên LangGraph 1.2.17. Không thêm wrapper chạy event loop ngầm. Caller dùng async API đúng khả năng của compiled graph.

## Khác biệt với facade

Facade await runner.search(question) vốn chọn cùng injected agent, rồi gọi Search. Graph mới await agent ở node query, truyền plan sang Search node hiện có để còn clarification routing và handoff. Không gọi runner.search trong graph. Test parity so exact provider kwargs, QueryPlan và toàn SearchState trên controlled native IDs/timestamps, gồm lỗi partial và skipped queries. Native read ports thật với fixture xác nhận subtypes/scores không đổi.
