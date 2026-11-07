# Tích hợp RAG vào AI Service — milestone pilot cục bộ

## Chạy thử

Từ thư mục workspace chứa cả `ai_core/` và `tillegal-ai-main/`, chạy bằng PowerShell. Pilot dùng mã baseline qua Python import và đọc artifacts từ checkout RAG đã bàn giao. Wheel của AI Service đứng riêng cần cài/cung cấp thêm checkout này và index. BM25 chỉ cần index T4. Dense/hybrid cần cả dependency ML, model lock và index T7 tương thích theo hướng dẫn bàn giao.

```powershell
$env:PYTHONPATH="$pwd/.tmp/rag-integration-runtime;$pwd/tillegal-ai-main;$pwd"
$env:APP_ENV="development"
$env:TILLEGAL_RAG_PILOT="1"
$env:TILLEGAL_ANSWER_PROVIDER="mock"
$env:TILLEGAL_RETRIEVAL_MODE="bm25"
.venv/Scripts/python -m uvicorn src.main:app --host 127.0.0.1 --port 8000
```

`.tmp/rag-integration-runtime` là bộ dependency cục bộ dùng để kiểm thử trong workspace này. Với môi trường AI Service đã cài dependency, chỉ cần hai checkout trên PYTHONPATH. Trong terminal thứ hai:

```powershell
$body = @{question="Đối thoại định kỳ"; top_k=3} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/pilot/legal-qa -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($body))
```

Endpoint dùng được khi bật pilot trong development với database integrations tắt. Chỉ phục vụ corpus thử nghiệm dùng chung, chạy trên loopback. Request có question và top_k (1–100). Middleware tạo hoặc echo request_id. Mỗi lần chạy có UUID run_id độc lập. Header từ client chỉ dùng cho correlation. API trả evidence_bundle nguyên vẹn, draft, citation ứng viên, kết quả đối chiếu trong bundle và giới hạn sử dụng. Kết quả rỗng trả NO_EVIDENCE.

Đổi `TILLEGAL_RETRIEVAL_MODE` sang `dense` hoặc `hybrid`. Đặt `TILLEGAL_RERANK=true` cùng hybrid để bật reranker. Có thể đặt đường dẫn manifest BM25 qua `TILLEGAL_INDEX`; factory vẫn kiểm tra identity của dense index liên kết. Cấu hình sai hoặc thiếu artifacts khiến startup thất bại.

Để dùng runtime local do operator quản lý, đặt `TILLEGAL_ANSWER_PROVIDER=local`, `TILLEGAL_ANSWER_MODEL=<model ID đã nạp>` và tùy chọn `TILLEGAL_LOCAL_PORT` (mặc định 8080), rồi khởi động lại. Adapter gửi đúng một yêu cầu POST tới 127.0.0.1/v1/chat/completions trên port đó, bỏ qua HTTP proxy, không theo redirect, không dùng API key. Chỉ trỏ tới runtime suy luận trên máy. Operator chịu trách nhiệm đảm bảo runtime không chuyển tiếp sang cloud. Chưa lựa chọn model sinh mới.

## Audit và implementation plan

Phân loại dưới đây áp dụng cho các hạng mục của yêu cầu bổ sung. Cột trạng thái đánh giá code trước tích hợp. Cột cuối ghi phần đã triển khai hoặc điều kiện chuyển sang giai đoạn sau.

| Yêu cầu | Trạng thái trước tích hợp | Quyết định và kết quả |
|---|---|---|
| I.1 Gateway và provider | Partially implemented | GenerationProvider, mock và client opt-in ở baseline đã có. Gateway/LiteLLM phía service là stub. Pilot đi qua gateway, hỗ trợ mock/local bằng cấu hình. Free-tier bên ngoài và paid provider thuộc giai đoạn sau, cần allowlist, quota và chính sách dữ liệu trước khi kích hoạt. |
| I.2 Model theo nhiệm vụ | Partially implemented | Answer generation có cấu hình riêng. Decomposition, judge, claim extraction, semantic verifier chưa chạy. Bổ sung profile cho từng nhiệm vụ khi triển khai agent tương ứng. |
| I.3 Chi phí và ngân sách | Missing and required now | Pilot mặc định mock, chỉ chấp nhận mock/local, không fallback. Giới hạn input/prompt theo baseline, output 1024 token cho local, một lần generate, không retry. Local báo usage nếu runtime trả số token. Chi phí điện/phần cứng chưa đo. |
| I.4 Đánh giá model mới | Deferred to later phase | Chưa thay model. Trước khi chọn LLM cần đo trên tiếng Việt pháp lý, structured output, evidence, context, latency, quota, chi phí, quyền xử lý dữ liệu và tool calling nếu workflow dùng. |
| II Encoder/reranker và index | Already implemented | Dùng lại make_retriever, pinned revisions, dimension 384, preprocessing, source/index checks và cấu hình của encoder. Bốn chế độ chạy độc lập. Index Supabase 1536 thuộc đường khác. Thay encoder cần thay deployment tương thích và dựng lại index. |
| III Tool và boundary | Partially implemented | ToolRegistry, ToolExecutor, PermissionPolicy và repository DB có sẵn. Đã đăng ký legal_retrieval read-only với schema, grant nội bộ, timeout và canonical EvidenceBuilder bundle. Citation lookup trong bundle theo ID. External search, lookup nguồn online và quyền theo tenant nằm ngoài pilot. |
| IV.1 Request isolation | Missing and required now | Mỗi lần invoke graph có state riêng; index/provider dùng chung theo worker. Test overlap buộc trả busy, sau đó kiểm tra evidence/request/run của từng lượt. |
| IV.2 Hội thoại và checkpoint | Deferred to later phase | Pilot stateless, không có API đọc/ghi lịch sử, không nhận user_id/conversation_id/thread_id/idempotency key. PostgresCheckpointer và idempotency store đã tồn tại phía framework. Trước khi thêm hội thoại phải gắn user xác thực với conversation/thread, kiểm tra quyền, version và xử lý write conflict. |
| IV.3 Scheduling | Partially implemented | Graph có hai node theo thứ tự cố định, không loop, tool deadline 30s, local socket timeout 25s, deadline request 60s. Một run/worker, quá tải trả 429 ngay. Lock riêng bảo vệ tài nguyên nếu caller hủy trong lúc native thread đang chạy. Không có quota theo user hay hàng đợi phân tán. |
| IV.4 Failures | Partially implemented | Startup từ chối config/index sai. Provider lỗi/rate limit, schema lỗi, timeout hoặc tool lỗi có HTTP error riêng. Thiếu evidence thì bỏ qua generate. Judge retry budget, restore checkpoint và resume giữa hai version cần thiết kế khi thêm các tính năng đó. |
| V Evidence và citation | Partially implemented | Giữ quote, hash, locator, phiên bản tài liệu, cảnh báo và ranking từ EvidenceBuilder. check_candidates dùng độc lập hoặc sau draft, so identity và quote với bundle tin cậy của run. Claim support, ngữ cảnh đủ, hiệu lực, khả năng truy cập và tính xác thực nguồn ngoài vẫn chưa xác minh. |
| VI Resource management | Partially implemented | Nạp index/model tại startup một lần/worker và giải phóng reference ở shutdown. Blocking work nằm ngoài event loop. Một worker là cấu hình đã thử. Đổi throughput lấy khả năng giới hạn contention/RAM. Nhiều worker sẽ nhân bản model; chưa đo peak RAM. |
| VII Baseline và đánh giá | Partially implemented | Giữ BasicRAG độc lập. So sánh kết quả trên cùng artifacts; tách unit/contract, HTTP integration, concurrency, retrieval parity, chất lượng và benchmark ở phần kiểm thử. Gold labels cần human review trước khi đánh giá chất lượng. |
| VIII Observability | Partially implemented | Dùng middleware, correlation context và structured logger hiện tại. Ghi backend/index, provider/model, token count nếu có, thời gian retrieval/draft, trạng thái evidence/verification, request/run và HTTP status. Tắt tracing LangSmith cho invocation. Error category chi tiết trả cho caller; dashboard, counters và quota telemetry chưa triển khai. |
| IX–X Triển khai | Missing and required now | P0 bảo toàn evidence và mặc định offline; P1 nối tool, gateway và graph; P2 đo baseline vận hành. P3 chỉ mở rộng sau quality gate và yêu cầu sản phẩm cụ thể. |

### Thứ tự milestone tiếp theo

1. Chạy real-generation trên runtime local được duyệt và bộ câu hỏi có người rà soát. Chấm groundedness, abstention, claim-to-citation và temporal applicability riêng. Đây là điều kiện để đánh giá câu trả lời pháp lý.
2. Khi phục vụ người dùng đã xác thực, tích hợp principal thực, tenant ACL, quota và versioned checkpoint trước khi lưu hội thoại. Thử cancellation, stale state và restore failure dưới tải.
3. Chỉ bật external provider khi đã duyệt xử lý dữ liệu, chi phí, token accounting và quota. Chỉ thêm retry/judge loop khi có regression/evaluation chứng minh lợi ích.

## Tái hiện kiểm thử

Chạy từ workspace root với PYTHONPATH như trên, trong terminal riêng đã bỏ biến TILLEGAL_RAG_PILOT (bộ test tự bật khi cần).

```powershell
$env:HF_HUB_OFFLINE="1"
$env:TILLEGAL_TEST_ML="1"
.venv/Scripts/python -B -m pytest -q tillegal-ai-main/tests
.venv/Scripts/python -B -m unittest discover -s tests -q
```

- Unit và contract: lựa chọn/khước từ provider, HTTP wire contract giả lập, rate limit, citation sai identity hoặc quote. Mock không suy luận pháp lý.
- Integration và concurrency: TestClient qua bootstrap/lifespan, middleware, LangGraph, permissioned tool và EvidenceBuilder; request chồng lấn, lỗi generation, input sai, gate môi trường và DB.
- Retrieval parity: ba truy vấn, top_k=3, cho từng BM25/dense/hybrid/hybrid+reranker. So sánh toàn bộ evidence_bundle (bao gồm rank, score, index/version, IDs, quote, warnings), candidate citations, request và trạng thái với BasicRAG. Dense và reranker chạy weights thật trên CPU. Parity trên mẫu này không đo precision/recall trên tập gold.
- Generation/citation quality: chưa chạy LLM sinh thật hoặc semantic verifier; contract tests và mock generation chỉ đánh giá logic. Chưa thử môi trường Python 3.12 hoặc dependency đúng từng version trong uv.lock; máy hiện tại dùng Python 3.14.2.

### Kết quả chạy trên workspace

- AI Service: 90 test đạt trong 103,13 giây, bật TILLEGAL_TEST_ML, gồm cả bốn cấu hình retrieval. Baseline: 189 test đạt trong 28,525 giây.
- Microbenchmark: TestClient ASGI cùng process, Windows/Python 3.14.2, index T4 đã nạp, một worker, BM25, mock, top_k=3, câu “đối thoại định kỳ”. Bỏ một lượt warm-up, năm lượt tuần tự mất 60,9 / 27,1 / 25,9 / 26,6 / 28,0 ms; trung vị 27,1 ms. Logging tắt cho phép đo này. Máy đồng thời chạy kiểm thử khác. Kết quả chỉ mô tả lần đo cục bộ, chưa đo chi phí mạng, real-generation, tail latency, throughput nhiều người dùng hoặc peak RAM.

Milestone tiếp theo đã bổ sung chế độ `workflow="multi_agent"` trên cùng endpoint. Xem [Multi-Agent Legal QA](multi-agent.md) để chạy thử, so sánh hai workflow và kiểm tra giới hạn verification.
