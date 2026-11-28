# Orchestrator một lượt

Nhánh `feature/query-summary-orchestrator`, base integration `905652a`.
Thiết kế bám mục 2, 6, 9, 10 của PIPELINE_LEGAL_AI (1).pdf; PDF là
thiết kế đề xuất, không phải bằng chứng toàn hệ thống đã hoàn thành.
Không tìm thấy AGENTS.md trong repo hoặc các thư mục cha đã kiểm tra.

## Phần đã có và phần mới

Tái sử dụng QuerySearchNodes, QuerySearch, native SearchState, GraphExecutor,
ExecutionContext/lifecycle, JudgeAgent/evaluate_search và SummaryAgent/adapt_judge.
Graph Query/Search cũ và core các agent không đổi.

Mới: `graphs/single_pass.py` cung cấp state riêng, node wrappers, routing,
SinglePassOutput và workflow; `src/qa_bootstrap.py` inject dependencies.
Không có refine, evidence nhiều vòng, retry tự động, Verify hay Faith-Search.

Luồng: Query → Search → Judge → Summary → Finalize. Clarification đi thẳng
Finalize; Search FAILED/PARTIAL không vào Judge; Judge ERROR không vào Summary.
Search COMPLETE không evidence vẫn vào Judge (fast path INSUFFICIENT), Summary
abstain nếu không usable evidence. INSUFFICIENT vẫn giữ nguyên và Summary chỉ
sinh phần có căn cứ hoặc abstain. Không coi completion là đã xác minh.

## Python API

```python
from src.qa_bootstrap import create_single_pass_workflow
from src.framework.runtime.execution_context import ExecutionContext

workflow = create_single_pass_workflow(
    pipeline,  # QuerySearch với retrieval/options/query_agent đã cấu hình
    judge_provider=judge_provider,
    summary_provider=summary_provider,
    allow_live=False,
)
output = await workflow.execute(
    question,
    ExecutionContext(run_id="run-1", request_id="request-1"),
    timeout_seconds=60,
    lifecycle=lifecycle,  # optional ExecutionLifecycle
)
result = output.model_dump(mode="json")
```

Nếu không có request_id, workflow tạo UUID và dùng context mới cùng token
cancellation. Services/providers chia sẻ cần hỗ trợ chạy đồng thời; dữ liệu và
telemetry của mỗi request nằm riêng. Bootstrap không đọc .env, không tạo kết nối
ngầm. Judge/Summary provider không khai báo `mode="mock"` cần `allow_live=True`.
Retrieval/Query live phải được caller cấu hình chủ động; `allow_live` không tự
biến dịch vụ retrieval đã inject thành offline. Không có provider live được gọi
trong quá trình kiểm tra này.

## Offline

Từ repo root với Python >=3.12 và dependencies của repo:

```powershell
python -m examples.orchestrator.offline
```

Example gọi entrypoint chính, replay plan/retrieval và fixture JSON chỉ định.
`fixture.json` là dữ liệu synthetic từ fixtures test của repo; câu trả lời là câu
minh họa, không phải kết luận pháp lý. `output.json` là output mẫu để bàn giao.
Chạy lại demo không ghi đè file và không cần key, mạng hoặc database.

## State, output và điểm nối Verify

State kế thừa LegalQAState nhưng riêng cho graph mới; giữ native SearchState,
NativeJudgeResult nguyên vẹn, Summary và telemetry. Payload agent chỉ chứa dữ liệu
adapter chọn. Output Pydantic validate trường, context IDs/date/version, output
Summary và mapping citation → evidence. Envelope gồm workflow_status,
judge_status, summary_output, draft_version, verification_status=NOT_RUN,
as_of_date, stop_reason, errors, limitations, judge_carrier và trace.
Các ID/provenance không bị đổi; metadata unknown giữ null.

Verify sẽ nối sau Summary trước Finalize. Dữ liệu bàn giao:
- `summary_output.answer_draft`, `draft_version`, `claims`, `citations`;
- `judge_carrier.adapted.judge_input.evidence` và `evidence_map` (native provenance,
  occurrences và query associations), cùng `native_context`;
- `as_of_date`, request_id và run_id.

Envelope giữ carrier đầy đủ để integration audit; API/UI công khai có thể cần
projection riêng và giới hạn kích thước. Không đưa toàn carrier vào prompt Verify
mà chỉ chọn cặp claim/citation và nguồn cần thiết. Trace ở output là danh sách node
đã chạy; run_id/context vẫn đi qua executor và tracing của framework.

## Timeout, cancellation và lỗi

Judge/Summary sync chạy bằng asyncio.to_thread, nhận dữ liệu tách rời. Deadline
và token cancellation dùng GraphExecutor. TimeoutError/ExecutionCancelledError
được propagate đúng cơ chế framework và cập nhật lifecycle; không có envelope
Finalize khi graph bị hủy/timeout. Lỗi input/planner đã phân loại trả QUERY_FAILED;
lỗi adapter/agent có code an toàn trong envelope. Programming errors ngoài contract
propagate qua executor; không giấu bằng một draft hoặc thông báo thành công.

Hủy await không dừng được request provider sync/thread đang chạy. Provider phải
có I/O timeout riêng. asyncio.run có thể chờ worker còn chạy khi đóng default
executor. Kết quả worker sau hủy bị bỏ, không được ghi ngược vào state; provider
vẫn có thể tốn tài nguyên. Không có retry tự động nên không khởi tạo request trùng.

## Kiểm tra

```powershell
python -m pytest tests/graph/test_single_pass_workflow.py -q
python -m pytest tests/graph tests/unit/applications/tillegal/test_judge_native.py tests/unit/applications/tillegal/test_summary_native.py tests/unit/applications/tillegal/test_summary_display.py -q
python -m ruff check src/applications/tillegal/graphs/single_pass.py src/qa_bootstrap.py tests/graph/test_single_pass_workflow.py examples/orchestrator/offline.py
```

Tests là kiểm tra contract/routing, không chứng minh độ đúng pháp lý hoặc chất lượng
LLM. Bước tiếp theo (ngoài phạm vi): Query refine, evidence tích lũy rồi vòng lặp.

## Kết quả kiểm tra bàn giao

- 215 tests pass trong phạm vi graph, Judge/Summary native + display, Query/Search
  deterministic/semantic/multimode và framework graph routing; gồm 17 case graph mới.
- Ruff check và Ruff format --check: pass cho bốn file Python mới.
- Python syntax parse và validation lại JSON output mẫu: pass.
- Mypy không có trong môi trường và không thuộc dev dependencies; chưa chạy static
  type checker. Không chạy toàn test suite hoặc live services; phạm vi regression
  tập trung vào graph và các module tích hợp.

## Test online bằng CLI

Tạo `.env` tại repo root (không commit), gồm GOOGLE_API_KEY, SUPABASE_URL và
SUPABASE_SERVICE_ROLE_KEY của corpus hiện có. Có thể dùng --env-file với đường dẫn
khác. Biến môi trường đã tồn tại được ưu tiên; GEMINI_MODEL chọn model Query,
JUDGE_GEMINI_MODEL và SUMMARY_GEMINI_MODEL override hai model tương ứng nếu cần.

```powershell
python -m scripts.run_orchestrator --as-of-date 2026-11-28 --allow-live
```

CLI hỏi câu hỏi trong terminal; hoặc truyền `--question "Câu hỏi của bạn"`.
Mặc định env-file là `.env` tại repo root và timeout graph là 240 giây.
Có thể dùng `--timeout-seconds 240` và `--output-root <folder>`.
Phải bật --allow-live trước khi cấu hình provider; lệnh này có thể phát sinh phí.
Search là BM25 top 3, policy EXPERIMENTAL_ONLY, không dense/reranker.
Không cần tạo script Python hoặc nối lại graph. Script chỉ cấu hình và gọi
create_single_pass_workflow/execute; không thay implementation Orchestrator.

Terminal hiển thị trace, workflow/Judge/Summary statuses, draft và limitations.
JSON đầy đủ lưu tại tmp/orchestrator-online/online-<uuid>/output.json.
Exit code 0: hoàn tất hoặc cần clarification; 1: workflow lỗi/config/timeout;
2: tham số sai hoặc thiếu --allow-live; 130: ngắt bàn phím khi đang thực thi.
Bản nháp luôn chưa Verify. Khi timeout trong provider sync, tiến trình có thể
chờ worker kết thúc lúc đóng asyncio executor; không chạy lại ngay để tránh
request trùng. Không có secrets được in bởi CLI; không chia sẻ .env.
