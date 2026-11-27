# Hướng dẫn tích hợp và chạy Phase A

> Ghi chú publication: tài liệu ghi lại implementation/acceptance Phase A. Candidate PR được kiểm thử lại độc lập trên main sau V2; trạng thái Git/CI mới nhất được ghi trong FINAL_MAIN_INTEGRATION_REPORT.md (local). Source links đã đổi sang đường dẫn tương đối để review trên GitHub.

## Cách khởi tạo được hỗ trợ

Caller/composition root sở hữu credentials, profile và lựa chọn provider. Graph không đọc GOOGLE_API_KEY, không hardcode model hoặc tạo provider mỗi request. Dùng factory hiện có; ví dụ dưới là hướng dẫn cho lần chạy được caller cho phép, không được thực thi live trong nhiệm vụ này.

```python
from datetime import date

from src.applications.tillegal.agents.search.agent import SearchOptions
from src.applications.tillegal.graphs.legal_qa import QuerySearchWorkflow
from src.framework.runtime.execution_context import ExecutionContext
from src.query_search_bootstrap import create_query_search

options = SearchOptions(
    mode="bm25",
    top_k=5,
    as_of_date=date(2026, 11, 27),  # Trusted caller date; set from backend request policy.
    allowed_usage_policies=("EXPERIMENTAL_ONLY",),
)
runner = create_query_search(settings.supabase, options, semantic_mode="gemini")
workflow = QuerySearchWorkflow(runner)  # Compile once and reuse application dependencies.
state = await workflow.execute(
    question,
    ExecutionContext(run_id=run_id, request_id=request_id),
    timeout_seconds=60,  # Caller-owned total deadline, not a new graph default.
)
plan = state["plan"]
search_result = state["search_result"]
handoff = state["handoff"]
```

Để dùng offline deterministic, thay semantic_mode="deterministic" (cũng là mặc định) và không inject query_agent. Graph giữ query sync cũ; cả workflow vẫn nên dùng async API vì Search vốn async.

Nếu đã có SemanticQueryAgent được cấu hình, inject trực tiếp bằng `create_query_search(settings.supabase, options, query_agent=configured_agent)`. Không truyền cả query_agent và semantic_mode="gemini"; factory hiện có từ chối cấu hình chồng chéo. Compiled graph chọn theo dependency thực tế query_agent, không theo flag user tự gửi trong state.

## Compiled graph API

QuerySearchWorkflow.execute được ưu tiên vì có ExecutionContext, lifecycle, cancellation và total deadline. Có thể gọi trực tiếp `await workflow.graph.ainvoke(initial_state)` hoặc `workflow.graph.astream(initial_state, stream_mode="updates")`; initial state cần question/run_id và request_id nếu có. Gọi trực tiếp không tự thêm chính sách deadline/context của GraphExecutor.execute.

Không dùng `workflow.graph.invoke(...)` cho cấu hình semantic: LangGraph báo không có synchronous query function và không chạy deterministic thay thế. Không thêm asyncio.run bên trong server event loop; caller async dùng await.

## Diễn giải output

- Clarification: status CLARIFICATION_REQUIRED; search_result/handoff None; hỏi user theo cơ chế caller hiện có.
- Query lỗi: nhận QueryAnalysisError hiện có, hoặc cancellation/deadline; không giả SearchState/evidence. Controller tự quyết định lỗi, graph không retry.
- Search chạy: giữ native SearchState và technical JudgeHandoff. READY/SEARCH_COMPLETED không chứng minh đủ căn cứ pháp lý; NO_MATCH không chứng minh không có quy định; RETRIEVAL_FAILED vẫn là lỗi kỹ thuật.
- Hybrid/Rerank: giữ response subclass và native rank/order; không sort RRF raw_score để thay reranker. Handoff JSON union giữ subtype như trước.

## Chạy kiểm thử mà không gọi API thật

Từ root project với virtualenv hiện có:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/graph/test_query_search_workflow.py -k phase_a -q -p no:cacheprovider
.\.venv\Scripts\python.exe -m pytest tests/graph/test_query_search_workflow.py -q -p no:cacheprovider
.\.venv\Scripts\python.exe -m pytest tests/unit/applications/tillegal tests/graph/test_query_search_workflow.py -q -p no:cacheprovider
.\.venv\Scripts\python.exe -m pytest tests/unit/applications/tillegal/test_contract_v2.py -q -p no:cacheprovider
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```

Những lệnh này dùng mocked provider/fake read fixtures của bộ test. Exact audit runs còn thêm launcher ngoài repo để chặn network; xem tài liệu 04. Lint whole integration tree và format hai file đã thay đổi cũng đã chạy PASS.

## Handoff cho bước tích hợp sau

Chỉ cần review/apply diff graph và test, kèm sáu tài liệu này trên base V2 hiện có. Không copy các thay đổi unrelated trong development tree. Source ở root và detached integration worktree giống nhau cho hai file Phase A. Không có dependency mới, thay config/key/model hay DB migration. Publication/merge được theo dõi riêng trên PR và báo cáo tích hợp cuối.
