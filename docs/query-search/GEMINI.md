# Kết nối Query semantic planner với Gemini

Ngày thực hiện: 23/11/2026. Project đích: `D:/DOWNLOAD/tillegal-ai/tillegal-ai-main`.

## Audit và quyết định

- `src/application/interfaces/llm_gateway.py`, `src/framework/llm/gateway.py` và `providers/litellm_adapter.py` vẫn là placeholder. Tìm trong src/configs/scripts/tests không thấy Gemini integration nào có sẵn.
- `SemanticQueryAgent` đã có cổng `StructuredCompletion(model, system, user, schema) -> str`, timeout, strict Pydantic validation, grounding facts, guard citation/numeric và lỗi không fallback. Không cần redesign planner.
- `QuerySearch.search` đã hỗ trợ injected `query_agent`, nhưng factory chỉ có đường cấu hình thủ công. Graph có sẵn gọi `understand` đồng bộ; không thay graph trong task này.
- `configs/models.yaml` trước thay đổi chỉ có OpenAI/Anthropic. Dependency LiteLLM đã có trong pyproject; môi trường hiện cài LiteLLM 1.106.4. Không thêm dependency.
- `GOOGLE_API_KEY` đã có giá trị trong process/user environment. Không đọc/in giá trị, không chép vào `.env`, không đổi hay bổ sung `GEMINI_API_KEY`.
- Bản đích không có `.git`. Dùng baseline SHA-256 và bản gốc để review; không suy diễn branch/HEAD từ worktree bên cạnh.

Giải pháp nhỏ nhất là adapter Gemini trong provider layer, dùng `litellm.acompletion` với route `gemini/`, và cấu hình Query riêng. Không hoàn thiện toàn bộ shared gateway hoặc router/retry/fallback framework. Đây là adapter cho protocol đã có, không phải một hệ thống gateway mới.

## Model

Mặc định: **`gemini-3.5-flash-lite`**; LiteLLM route: `gemini/gemini-3.5-flash-lite`.

API `GET /v1beta/models` trả HTTP 200 và liệt kê model này với `generateContent` cho key hiện tại. Tài liệu Google mô tả model stable, tối ưu độ trễ/chi phí cho extraction và có structured output. Đây là lựa chọn phù hợp cho lập kế hoạch JSON ngắn; không có kết luận benchmark rằng model này tốt nhất cho pháp luật tiếng Việt. Một câu hỏi tiếng Việt thực tế đã được kiểm tra thành công, chi tiết ở phần live bên dưới.

Nguồn đã kiểm tra:

- [Google: Gemini 3.5 Flash-Lite](https://aistudio.google.com/docs/models/gemini-3.5-flash-lite)
- [Google: structured output](https://aistudio.google.com/docs/structured-output)
- [LiteLLM: Gemini provider và response_schema](https://docs.litellm.ai/docs/providers/gemini)

Không chọn 2.5 Flash mặc định vì tài liệu Google hiện thông báo deprecation và auto-routing từ 01/12/2026. Không dùng alias `latest` để tránh tự đổi model ngoài ý muốn.

## Các thành phần mới

| File | Trách nhiệm |
|---|---|
| `src/framework/llm/providers/gemini_adapter.py` | `GeminiStructuredCompletion`: nhận SecretStr, gọi LiteLLM một lần, yêu cầu JSON/schema, chặn response rỗng/truncated/blocked/non-object, chuẩn hóa lỗi an toàn |
| `src/applications/tillegal/agents/query/gemini.py` | `GeminiQuerySettings`, `create_gemini_query_agent`: đọc profile và environment, tạo adapter + SemanticQueryAgent |
| `src/query_search_bootstrap.py` | Thêm `semantic_mode="gemini"` vào factory hiện có; deterministic vẫn là mặc định |
| `configs/models.yaml` | Thêm provider `gemini` và profile `query_semantic`; giữ nguyên các giá trị OpenAI/Anthropic và global default của thành phần khác |
| `scripts/verify_gemini_query.py` | CLI kiểm chứng explicit Gemini/deterministic, request smoke và Query → Search bằng RetrievalService/index giả |
| `tests/unit/applications/tillegal/test_gemini_query.py` | Test provider responses được mock, factory/configuration, bảo vệ secrets, schema, lỗi và interface Query/Search |

## Luồng thực thi

```text
create_query_search(..., semantic_mode="gemini")
  -> create_gemini_query_agent()
  -> đọc profiles.query_semantic + providers.gemini + GOOGLE_API_KEY
  -> SemanticQueryAgent(complete=GeminiStructuredCompletion(...))

await pipeline.search(question)
  -> SemanticQueryAgent.understand(question)
  -> validation deterministic có sẵn
  -> GeminiStructuredCompletion(model, system, user, schema)
  -> LiteLLM acompletion(model="gemini/...") -> Google Gemini API
  -> JSON text -> SemanticAnalysis strict validation + các guard có sẵn
  -> QueryPlan -> Search -> RetrievalService
```

Adapter gửi schema từ planner dưới dạng `response_format={"type":"json_object","response_schema":schema}`. Planner tiếp tục validate cục bộ, không tin rằng provider đã kiểm tra đủ schema. Bất kỳ guard nào thất bại đều chặn Search.

Response chỉ được nhận khi finish_reason=`stop`, content là JSON object dài 1–32.000 ký tự. Không bỏ qua output bị cắt hoặc safety blocked. Key giữ dưới SecretStr, bị loại khỏi repr. Lời gọi dùng `no-log=True`, `num_retries=0`, `caching=False`; adapter không tự retry hoặc fallback. Không in upstream exception message, response body hay headers. Các mã provider an toàn như `GEMINI_RATE_LIMITED` giữ HTTP status nếu có.

Provider timeout và timeout planner lấy cùng một giá trị, mặc định 30 giây. Cancellation vẫn truyền lên caller. LiteLLM được import lười trong worker thread để không chặn event loop; lần import đầu có thể tốn thời gian trong deadline. Bảng giá model của LiteLLM không cần tải từ Internet để lập query; khi kiểm chứng đặt `LITELLM_LOCAL_MODEL_COST_MAP=True` để dùng bảng đi kèm package. Không chỉnh package hay bật debug logging.

## Bật/tắt và cấu hình

Đường production dùng RetrievalService hiện hữu:

```python
pipeline = create_query_search(
    settings.supabase,
    search_options,  # mode/date/policy/top-k vẫn do ứng dụng truyền rõ
    semantic_mode="gemini",
)
result = await pipeline.search(question)
```

Đường offline:

```python
pipeline = create_query_search(settings.supabase, search_options, semantic_mode="deterministic")
```

Existing manual `query_agent=` injection vẫn hoạt động. Không truyền đồng thời `query_agent` và `semantic_mode="gemini"`; factory báo `QUERY_AGENT_CONFIGURATION_CONFLICT`. Mode không hợp lệ bị từ chối trước khi tạo retrieval.

| Cấu hình | Nguồn / giá trị |
|---|---|
| API key | Chỉ đọc `GOOGLE_API_KEY` từ environment hiện có |
| Model | `GEMINI_MODEL` nếu có, nếu không dùng `profiles.query_semantic.model` |
| Deadline | `QUERY_LLM_TIMEOUT_SECONDS` nếu có, nếu không dùng `providers.gemini.timeout_seconds`; hữu hạn, >0 và ≤120 |
| Output budget | `profiles.query_semantic.max_output_tokens`, mặc định 4096 |

Factory không tự load hoặc ghi `.env`, không thay process environment. Cấu hình thiếu/sai có mã `GEMINI_QUERY_CONFIGURATION_INVALID`, không kèm Pydantic input chứa credentials.

**Phạm vi bật semantic là lời gọi trực tiếp `QuerySearch.search`.** Graph có sẵn vẫn gọi Query đồng bộ deterministic; không được coi việc truyền pipeline vào graph là đã bật Gemini. Không sửa graph, handoff hoặc các agent khác trong task này.

## Lệnh thật đã chạy

Chạy PowerShell trong `D:/DOWNLOAD/tillegal-ai/tillegal-ai-main`; key đã tồn tại trong environment, không paste key vào lệnh:

```powershell
$env:PYTHONUTF8='1'
$env:LITELLM_LOCAL_MODEL_COST_MAP='True'
.\.venv\Scripts\python.exe -m scripts.verify_gemini_query --mode gemini --smoke-test
.\.venv\Scripts\python.exe -m scripts.verify_gemini_query --mode gemini --search-backend fixture
```

Lệnh thứ hai dùng câu hỏi mặc định đã ghi trong script: hợp đồng 2 năm, làm 6 tháng, muốn nghỉ việc, hỏi báo trước và bồi thường. Có thể thêm `--question "..."` để đổi câu. `--search-backend none` chỉ chạy Query; `fixture` chạy Search và RetrievalService thật với sparse/index ports giả, không đọc Supabase.

Tắt LLM để test offline:

```powershell
.\.venv\Scripts\python.exe -m scripts.verify_gemini_query --mode deterministic --search-backend fixture
```

Các lệnh Gemini trên gọi API thật và có thể tiêu tốn quota/chi phí. CLI chỉ chạy live khi người gọi chọn `--mode gemini`. `--smoke-test` dùng JSON nhỏ với `ok=true`; đây không phải câu hỏi pháp luật.

## Kết quả live thực tế

Xem [GEMINI_LIVE_RESULTS.json](GEMINI_LIVE_RESULTS.json) để đọc bản ghi kết quả, model, timestamp và latency. Các thời điểm hiển thị dưới đây theo Asia/Saigon, ngày 23/11/2026. Latency đo toàn bộ lượt CLI, bao gồm import SDK và validation, không phải thời gian xử lý riêng phía Google.

| Kiểm tra | Kết quả | Model | Latency |
|---|---|---|---:|
| Liệt kê model bằng key hiện có | PASS, HTTP 200 | Danh sách có gemini-3.5-flash-lite | Không đo |
| Smoke đầu tiên | FAIL, GEMINI_TIMEOUT | gemini-3.5-flash-lite | 33.212,32 ms |
| Smoke, dùng local cost map | PASS, JSON `{ "ok": true }` | gemini-3.5-flash-lite | 6.341,89 ms |
| Câu hỏi tiếng Việt → Query → Search → RetrievalService/index giả | PASS | gemini-3.5-flash-lite | 6.867,84 ms |

Smoke đầu có warning sampling deprecated và coroutine chưa await khi timeout; không kết luận API Google bị lỗi từ lượt đó. Lượt sau đặt local cost map đã thành công. Adapter sau đó bỏ tham số temperature không cần thiết cho Gemini 3+ và chuyển import SDK sang thread; lượt pháp luật sau thay đổi thành công, không có hai warning trên.

Trong kết quả pháp luật live:

- `analysis_method=llm`, `analysis_model=gemini-3.5-flash-lite`.
- Facts là các span “Tôi ký hợp đồng lao động 2 năm” và “mới làm được 6 tháng nhưng muốn nghỉ việc”, đều có nguyên văn trong câu hỏi.
- Hai issues tương ứng nghĩa vụ báo trước và bồi thường khi chấm dứt hợp đồng; hai subqueries tương ứng. Không có số điều luật tự thêm.
- `SemanticAnalysis` và `QueryPlan` validation đều thành công; Search thực hiện hai truy vấn, trả `COMPLETED/COMPLETE`.
- Hai native retrieval response là `NO_MATCH`, evidence=0 vì index giả chủ động trả rỗng. Đây là kiểm chứng interface và luồng thực thi, không phải bằng chứng relevance của retrieval trên corpus thật.
- Model có hỏi lại loại hợp đồng dù câu hỏi đã nêu thời hạn hai năm; đây là thông tin thiếu còn dư thừa về mặt ngữ nghĩa, không bị schema loại bỏ. Không tuyên bố model hiểu hoàn hảo hoặc có độ chính xác pháp lý đo được.

## Giới hạn còn lại

Chưa chạy Supabase/corpus retrieval thật hoặc benchmark tiếng Việt. Không đánh giá/đưa ra câu trả lời pháp luật, không xác minh điều luật hay hiệu lực. Exact lookup và câu cần clarification theo guard cũ vẫn dùng deterministic mà không gọi model, với nhãn đúng. Có API key không bảo đảm quota/permission/model availability cho mọi thời điểm.

Shared gateway chung và adapter OpenAI/LiteLLM placeholder vẫn ngoài scope; các tác vụ Gemini trong task này gọi qua provider adapter mới, không tuyên bố hoàn thiện gateway toàn hệ thống. Không đổi BM25/Dense/Hybrid/Reranking, Search, Judge/Summary/Answer/Verification hoặc graph. Tất cả thay đổi local, không commit/push.
