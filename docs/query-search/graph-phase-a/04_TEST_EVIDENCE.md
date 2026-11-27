# Bằng chứng kiểm thử Phase A

> Ghi chú publication: tài liệu ghi lại implementation/acceptance Phase A. Candidate PR được kiểm thử lại độc lập trên main sau V2; trạng thái Git/CI mới nhất được ghi trong FINAL_MAIN_INTEGRATION_REPORT.md (local). Source links đã đổi sang đường dẫn tương đối để review trên GitHub.

Ngày chạy: 27/11/2026. Các kết quả dưới đây vừa được thực thi, không tái sử dụng số historical PASS. Provider Gemini luôn mock, Retrieval dùng fake read ports; full regression chạy qua launcher chặn socket ngoài loopback, bật offline Hugging Face/Transformers và tắt auto-migrate/checkpointer trong môi trường test. Không gọi API trả phí, ghi Supabase, tải model hoặc sửa credentials/config.

## Hai nền source đã kiểm tra

|Check|Integration worktree trên V2 1384707|Development tree trên feature/query-search-agents|
|---|---|---|
|Case mới Phase A|22 PASS|Có trong bộ graph 52 PASS|
|Graph hiện có + mới|52 PASS (30 cũ + 22 mới)|52 PASS|
|Query/Search focused + graph|670 PASS|643 PASS|
|Contract V2|43 PASS|43 PASS|
|Full pytest|776 PASS|732 PASS|
|Ruff lint|Toàn repo PASS|Hai file thay đổi PASS|
|Ruff format|Hai file thay đổi PASS|Hai file thay đổi PASS|
|Import/bootstrap|V1, graph, V2 PASS; assert source path đúng worktree|PASS; assert path development|

Số lượng khác nhau vì development tree giữ base cũ với unrelated work; integration tree chứa main/V2 đã publish. Không lấy kết quả 732 của development làm bằng chứng duy nhất cho base mới. Không thêm/sửa production ngoài graph.

## Coverage theo acceptance requirements

|Yêu cầu|Test/case chứng minh|
|---|---|
|Default compiled graph deterministic, không model|[test_phase_a_default_compiled_graph_does_not_call_gemini](../../../tests/graph/test_query_search_workflow.py#L375)|
|Injected Gemini async trong graph; payload/schema/model/parameters và nguyên SearchState parity|[test_phase_a_compiled_gemini_matches_facade_payload_and_entire_search_state](../../../tests/graph/test_query_search_workflow.py#L386)|
|Compiled node order Query rồi Search; plan semantic giữ nguyên|[test_phase_a_compiled_stream_orders_semantic_query_before_search](../../../tests/graph/test_query_search_workflow.py#L415)|
|Lookup/clarification/date-invalid guards không model; clarification không retrieval|[test_phase_a_existing_deterministic_guards_make_zero_model_calls](../../../tests/graph/test_query_search_workflow.py#L436)|
|Timeout/provider/non-JSON/schema/grounding errors chặn Search, không fallback/retry|[test_phase_a_query_errors_never_fallback_or_execute_search](../../../tests/graph/test_query_search_workflow.py#L452)|
|Clarification do semantic model trả về skip Search|[test_phase_a_semantic_clarification_skips_search](../../../tests/graph/test_query_search_workflow.py#L484)|
|Caller cancel, token cancel, outer deadline cancel provider và giữ lifecycle|[test_phase_a_semantic_cancellation_and_deadline_propagate](../../../tests/graph/test_query_search_workflow.py#L498)|
|Hai invocation concurrent giữ question/facts/request/run riêng|[test_phase_a_concurrent_semantic_graph_requests_are_isolated](../../../tests/graph/test_query_search_workflow.py#L542)|
|BM25/Dense/Hybrid/Rerank subclasses, scores, provenance, dedup mục tiêu|[test_phase_a_semantic_native_subtypes_scores_and_dedup_stay_intact](../../../tests/graph/test_query_search_workflow.py#L578)|
|Sync invoke semantic báo TypeError rõ, không đổi planner|[test_phase_a_semantic_sync_invoke_is_explicitly_unsupported](../../../tests/graph/test_query_search_workflow.py#L620)|

Parity case chạy cả success và fail-at-second với ba subqueries: nguyên warnings/errors, partial completeness và skipped_subqueries được so bằng equality với facade. Native mode case đếm một top-level request/subquery; Hybrid/Rerank có hai branch calls nội bộ, giữ đúng hành vi native. Hai issues dùng chung search query vẫn giữ issue_indices [0,1], chỉ một semantic subquery và một top-level retrieval execution.

Đã so AST với snapshot trước sửa: mọi function/class test có trước vẫn giữ nguyên; production deterministic query/route/search cũng giữ nguyên. V1/V2 contracts, prompts/provider config và Retrieval files được bảo vệ bằng scope/hash check cuối.

## Lần chạy phát hiện và sửa test setup

Lần đầu 15 case mới PASS/7 FAIL. Năm case lỗi dùng pytest regex có $ nên match cả LangGraph exception note không đúng dự kiến; đã đổi sang so chặt error.args==(expected_code,) và str(error)==expected_code, giữ nguyên kiểm tra lỗi/no Search/no fallback. Hai case Hybrid/Rerank đếm cả recursive service branches thành duplicate; đã kiểm đúng một top-level mode và đủ ba native service calls, không thay algorithm. Một dòng mới vượt Ruff line length đã được format. Không có production fix bổ sung hay assertion cũ bị nới để PASS. Sau sửa, toàn bộ 22 case và regression trên hai nền đều PASS.

## Exact commands và output trên integration tree

Working directory: `D:\DOWNLOAD\tmp\tillegal-graph-phase-a-worktree-20261127`.
`offline_pytest.py` là launcher ngoài repo, chuyển đến worktree và chạy pytest.main với external socket guard; các pytest arguments chính là command được repository hỗ trợ. Log/JSON ở `D:\DOWNLOAD\tmp\tillegal-graph-phase-a-20261127`.

### new

```powershell
& 'D:\DOWNLOAD\tillegal-ai\tillegal-ai-main\.venv\Scripts\python.exe' 'D:\DOWNLOAD\tmp\tillegal-graph-phase-a-20261127\offline_pytest.py' 'D:\DOWNLOAD\tmp\tillegal-graph-phase-a-worktree-20261127' 'tests/graph/test_query_search_workflow.py' '-k' 'phase_a' '-q' '-p' 'no:cacheprovider'
```

```text
Exit code: 0
......................                                                   [100%]
22 passed, 30 deselected in 1.97s
```

### graph

```powershell
& 'D:\DOWNLOAD\tillegal-ai\tillegal-ai-main\.venv\Scripts\python.exe' 'D:\DOWNLOAD\tmp\tillegal-graph-phase-a-20261127\offline_pytest.py' 'D:\DOWNLOAD\tmp\tillegal-graph-phase-a-worktree-20261127' 'tests/graph/test_query_search_workflow.py' '-q' '-p' 'no:cacheprovider'
```

```text
Exit code: 0
....................................................                     [100%]
52 passed in 2.99s
```

### focused

```powershell
& 'D:\DOWNLOAD\tillegal-ai\tillegal-ai-main\.venv\Scripts\python.exe' 'D:\DOWNLOAD\tmp\tillegal-graph-phase-a-20261127\offline_pytest.py' 'D:\DOWNLOAD\tmp\tillegal-graph-phase-a-worktree-20261127' 'tests/unit/applications/tillegal' 'tests/graph/test_query_search_workflow.py' '-q' '-p' 'no:cacheprovider'
```

```text
Exit code: 0
........................................................................ [ 85%]
........................................................................ [ 96%]
......................                                                   [100%]
670 passed in 18.05s
```

### v2

```powershell
& 'D:\DOWNLOAD\tillegal-ai\tillegal-ai-main\.venv\Scripts\python.exe' 'D:\DOWNLOAD\tmp\tillegal-graph-phase-a-20261127\offline_pytest.py' 'D:\DOWNLOAD\tmp\tillegal-graph-phase-a-worktree-20261127' 'tests/unit/applications/tillegal/test_contract_v2.py' '-q' '-p' 'no:cacheprovider'
```

```text
Exit code: 0
...........................................                              [100%]
43 passed in 1.72s
```

### full

```powershell
& 'D:\DOWNLOAD\tillegal-ai\tillegal-ai-main\.venv\Scripts\python.exe' 'D:\DOWNLOAD\tmp\tillegal-graph-phase-a-20261127\offline_pytest.py' 'D:\DOWNLOAD\tmp\tillegal-graph-phase-a-worktree-20261127' '-q' '-p' 'no:cacheprovider'
```

```text
Exit code: 0
........................................................................ [ 83%]
........................................................................ [ 92%]
........................................................                 [100%]
776 passed in 17.91s
```

### ruff

```powershell
& 'D:\DOWNLOAD\tillegal-ai\tillegal-ai-main\.venv\Scripts\python.exe' '-m' 'ruff' 'check' '--no-cache' '.'
```

```text
Exit code: 0
All checks passed!
```

### format

```powershell
& 'D:\DOWNLOAD\tillegal-ai\tillegal-ai-main\.venv\Scripts\python.exe' '-m' 'ruff' 'format' '--check' 'src/applications/tillegal/graphs/legal_qa.py' 'tests/graph/test_query_search_workflow.py'
```

```text
Exit code: 0
2 files already formatted
```

### imports

```powershell
& 'D:\DOWNLOAD\tillegal-ai\tillegal-ai-main\.venv\Scripts\python.exe' '-c' 'from pathlib import Path; import src.query_search_bootstrap as b; import src.applications.tillegal.graphs.legal_qa as g; import src.applications.tillegal.agents.pipeline_v2 as v; assert all(Path(m.__file__).resolve().is_relative_to(Path.cwd()) for m in (b,g,v)); print("V1 bootstrap / compiled graph / V2 imports PASS, source paths verified")'
```

```text
Exit code: 0
V1 bootstrap / compiled graph / V2 imports PASS, source paths verified
```

## Giới hạn bằng chứng

Test xác nhận compiled async graph thật gọi existing adapter nhưng completion là mock, không live Gemini. Không đo chất lượng semantic/ngữ nghĩa pháp lý, không E2E với Judge/Summary hoặc production Supabase. Một request trace controlled được ghi riêng trong tài liệu 03; không có secret/header trong trace. Chưa commit/push/merge.
