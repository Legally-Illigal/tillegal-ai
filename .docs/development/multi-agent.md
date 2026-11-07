# Milestone Multi-Agent Legal QA

## Chạy pilot

Từ workspace chứa checkout AI Service và checkout RAG, làm theo phần **Chạy thử** trong [pilot-rag.md](pilot-rag.md) để khởi động Uvicorn trên loopback. Giữ `APP_ENV=development`, `TILLEGAL_RAG_PILOT=1`, database tích hợp tắt. Chọn workflow cho từng POST. Mặc định `basic` giữ hợp đồng JSON cũ; `multi_agent` có response schema riêng.

```powershell
$body = @{workflow="multi_agent"; question="Trích dẫn: đối thoại"; top_k=1} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/pilot/legal-qa -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($body))
```

Để thử nhánh refinement, dùng câu “đối thoại; nghỉ phép”. Để so baseline, giữ question/top_k và đổi `workflow="basic"`. Backend chọn bằng `TILLEGAL_RETRIEVAL_MODE=bm25|dense|hybrid`. Hybrid + reranker cần `TILLEGAL_RERANK=true`. CPU, artifacts và Python path theo tài liệu pilot.

| Mode của Response Agent | Cấu hình trước khi khởi động |
|---|---|
| Mock | Mặc định; chọn nguyên văn một đoạn đã qua Judge bằng code. Token usage rỗng. |
| Local | `TILLEGAL_RESPONSE_PROVIDER=local`, `TILLEGAL_RESPONSE_MODEL=<id đã nạp>`, `TILLEGAL_LOCAL_PORT=<port>`. Runtime trên 127.0.0.1 cần trả JSON theo contract bên dưới. Model/port do người vận hành cung cấp. |
| Gemini | `TILLEGAL_RESPONSE_PROVIDER=gemini` từ chối startup với `GEMINI_DISABLED` trong bản pilot. API key hoặc tên model riêng lẻ không chứng minh được project thuộc free tier. |

Profile RESPONSE kế thừa ANSWER khi không có override. Query/Judge dùng quy tắc offline. Search dùng retriever, verification dùng đối chiếu dữ liệu. Chỉ Response cần model sinh ở mode local.

## Graph và contracts

```text
START → query → search → judge ──→ response → verify → END
                  ↑         │
                  └─ REFINE ┘
```

- **Query.** QueryPlan có original, intent, domain, temporal_scope, clarification và tối đa bốn subquery có purpose/text. Tách câu theo dấu câu và một số mẫu tiếng Việt, nhận diện chủ đề từ chính câu hỏi. Nhánh làm rõ bỏ qua mọi tool call. Phân tích rule-based có chủ đích; domain ngoài danh mục được ghi unknown.
- **Search.** Gửi lần lượt question, request_id, top_k qua ToolExecutor với grant read-only. Mỗi lần gọi trả nguyên bundle của EvidenceBuilder. Danh sách bundles giữ lịch sử từng query và omissions. Map dùng evidence_id do builder tạo từ index/chunk/hash; row trùng ID nhưng khác nội dung gây lỗi. Search trace chứa query, identity index/bundle, trạng thái và thời gian. Trace thuộc HTTP response của lượt đó. Exception từ source hủy workflow, HTTP 503; policy 403; timeout 504; quá tải 429.
- **Judge.** Decision phân biệt SUFFICIENT (phạm vi tác vụ trích dẫn), INSUFFICIENT và UNCERTAIN. Coverage cho biết subquery nào xuất hiện nguyên văn trong chunk ngoài heading. Judge xem omitted context, phạm vi pháp luật, dấu hiệu ngoại lệ, nhiều version cùng tài liệu và khoảng hiệu lực được ghi nhận khi có ngày/năm cụ thể. Metadata ngoài khoảng là lý do loại; metadata trong khoảng chưa xác nhận văn bản còn hiệu lực. Phát hiện mâu thuẫn nội dung giữa các quy định và áp dụng luật vào vụ việc cần đánh giá chuyên môn.
- **Refinement.** Judge tạo query tìm điều kiện/ngoại lệ, loại query đã hỏi. SEARCH_BUDGET (biến `TILLEGAL_SEARCH_BUDGET`, mặc định 4, miền 1–6) tính tổng mọi tool call. `TILLEGAL_SEARCH_ROUNDS` mặc định 2, miền 1–3. Stop reason ghi trong mỗi judgment, gồm budget, iteration limit, thiếu thông tin, không có evidence/query mới và đủ cho exact lookup. Chính sách khi hết budget là sang Response với kết quả giới hạn.
- **Response.** Provider nhận system + question và tối đa ba cặp evidence_id/quote đã chọn. Một lần sinh, tối đa 1024 output tokens, payload giới hạn. Contract strict JSON `{"claims":[{"text":"<nguyên văn toàn chunk>", "evidence_id":"<id>"}]}`. JSON sai trả 502; output không hợp lệ không biến thành câu trả lời. Mock chọn dữ liệu theo quy tắc. Câu trả lời cuối tách claims, citation ứng viên, diễn giải phạm vi và giới hạn. Nhánh partial chỉ công bố trích đoạn qua kiểm tra. Khi cần làm rõ, thiếu căn cứ hoặc toàn bộ claim bị loại, kết quả là ABSTAINED.
- **Verification.** verify_claims chạy độc lập hoặc làm node cuối. Kiểm tra ID thuộc tập evidence được chọn trong run, document version trong bundle, quote và SHA256 so với evidence đáng tin của lượt truy xuất, cùng quan hệ bằng nhau giữa claim và toàn bộ quote. Claim không đạt bị loại trước khi ghép answer. Đối chiếu này không xác nhận bản gốc bên ngoài hoặc hàm ý pháp lý. Check ghi riêng claim_support, temporal_applicability, source_reachability; semantic/legal verification và external reachability chưa chạy.
- **Scheduling.** Chung semaphore, tool executor, index/model và generation lock với basic. Một run/worker, quá tải trả 429; deadline 60s; tool timeout 30s; socket provider 25s. Mỗi invoke có run_id mới và state riêng. Thread native có thể hoàn tất sau khi caller hủy; khóa tài nguyên giữ đến khi thread thoát. Graph state chỉ chứa dữ liệu có thể serialize, provider/tool ở closure. Pilot sử dụng graph không có persistence, chưa kiểm thử resume/checkpoint và ACL cho hội thoại.

## Gemini và chi phí

Adapter có wire contract generateContent và xác thực output/usage. Bootstrap không cài FreeTierPolicy. Chọn Gemini từ environment vì vậy dừng trước khi đọc key hoặc mở kết nối. Nếu team tích hợp policy tin cậy sau này, adapter đọc GOOGLE_API_KEY trong process, truyền key qua header HTTPS tới host cố định, cấm fallback và không đưa key vào kết quả. Mỗi lần gọi phải có quota reservation theo key fingerprint/project, model allowlist, billing tắt, data permission và token budget do policy kiểm tra. Adapter còn giới hạn tối đa 1 lần/phút và 5 lần/24h cho mỗi instance. Quota theo project, xác minh billing và điều khoản dữ liệu là công việc mở trước khi bật; counters trong bộ nhớ chỉ là lớp bổ sung. Thử nghiệm contract offline không dùng key.

Theo Google, tier và billing được kiểm tra theo project/account, và bật billing có thể chuyển sang paid tier. [Billing](https://ai.google.dev/gemini-api/docs/billing) · [generateContent](https://ai.google.dev/api/generate-content)

## File thay đổi trong AI Service

| Đường dẫn tương đối trong checkout team | Mục đích |
|---|---|
| src/applications/tillegal/agents/{query,search,judge,response}/agent.py | Bốn agent có logic chạy độc lập. |
| src/applications/tillegal/graphs/multi_agent.py | State, topology, budgets, routing và tạo output. |
| src/applications/tillegal/graphs/{legal_qa,citation_verification}.py | Chia sẻ tài nguyên với basic; kiểm tra claim trước khi hiển thị. |
| src/api/routes/chat.py | Chọn workflow và phân loại lỗi permission. |
| src/framework/llm/gateway.py, src/framework/llm/providers/gemini.py | Profile theo tác vụ, local/mock và Gemini có gate. |
| tests/integration/{test_multi_agent,test_pilot_rag}.py | Test từng agent, graph/HTTP, timeout, concurrency và so bundle với baseline. |
| scripts/benchmark_pilot_agents.py | Benchmark ASGI cục bộ so hai workflow. |
| .docs/development/multi-agent.md, pilot-rag.md | Báo cáo milestone và hướng dẫn chọn mode. |

## Kiểm thử và đánh giá

Dùng PYTHONPATH và môi trường như pilot-rag.md; bộ test tự bật pilot. Với TILLEGAL_TEST_ML=1 và HF_HUB_OFFLINE=1:

```powershell
.venv/Scripts/python -B -m pytest -q tillegal-ai-main/tests
.venv/Scripts/python -B -m unittest discover -s tests -q
.venv/Scripts/python -B tillegal-ai-main/scripts/benchmark_pilot_agents.py
```

- Unit/contract: query decomposition, ngày/số hiệu, time window, jurisdiction, nhiều version, omitted exception, structured output sai, ID ngoài run, unsupported claim, wire format và rate limit. Integration: đủ cho exact lookup, làm rõ, rỗng, refinement, budget, backpressure, request isolation, tool/provider timeout và policy denial.
- Retrieval regression: so bundle đầu tiên của Multi-Agent Search với BasicRAG trên cùng search text, top_k và index cho cả BM25, dense, hybrid, hybrid+reranker. Các test parity có trước tiếp tục so ba truy vấn với basic pilot. Dense/reranker chạy model thật; Query/Judge dùng luật; generation trong test dùng mock hoặc giả lập lỗi.
- Chất lượng: T5 có 8 câu dev và 4 câu test đang pending human review. T7 đánh dấu TECHNICAL_ONLY_NO_APPROVED_GOLD. Chưa có Recall@k/MRR trên gold đã duyệt. Exact-quote check, rejected claim và abstention được test theo fixture. Chưa có điểm groundedness, entailment, citation correctness pháp lý hoặc tỷ lệ abstention trên câu hỏi thực. Cache hiện có embedding/reranker; chưa chạy local generative model thật hay Gemini, chưa có token usage quan sát được từ model sinh thật.
- Rủi ro: topical phrase match có thể bỏ sót paraphrase hoặc chọn đoạn có cùng từ nhưng khác ngữ cảnh. Refinement dùng mẫu từ khóa có thể thêm nhiễu. Phản hồi có thể lớn vì giữ nguyên các bundle. Corpus pilot còn quarantine, người vận hành phải giữ endpoint nội bộ.
- Tiếp theo: phê duyệt gold theo document version/locator, gắn nhãn ngoại lệ, thời điểm và claim support; đánh giá semantic verifier riêng với supported/contradicted/insufficient và trace tới span. Đánh giá generation tiếng Việt trên runtime được duyệt trước khi cho phép diễn giải tự do. Trước production cần xác thực người dùng, ACL hội thoại/checkpoint, kiểm thử cancellation/resume và stale versions, load/peak RAM, giám sát quota/billing và chính sách dữ liệu.

### Kết quả đo

AI Service đạt **102/102 test**, 121,11 s. Baseline đạt **189/189 test**, 23,782 s. Chạy trên Windows/Python 3.14.2 với artifacts local. Chưa lặp lại trên Python 3.12 theo lockfile team.

Benchmark cuối chạy sau khi các suite đã kết thúc. Cùng worker đã nạp BM25, ASGI TestClient, mock, top_k=1, logging tắt. Mỗi câu chạy 1 warm-up/mode rồi 5 lượt/mode, xen kẽ thứ tự basic/multi-agent. Thời gian tính qua HTTP test client, bao gồm serialize response và toàn bộ retrieval.

| Câu hỏi | Basic median | Multi-agent median | Retrieval calls basic / multi | Kết quả multi |
|---|---:|---:|---:|---|
| Trích dẫn: đối thoại | 21,1 ms | 23,1 ms | 1 / 1 | EXTRACTIVE_DRAFT |
| đối thoại; nghỉ phép | 19,6 ms | 42,9 ms | 1 / 4 | PARTIAL |

Case thứ hai bao gồm decomposition, refinement và nhiều evidence bundle hơn. Các thời gian này mô tả hai đường chạy cụ thể với mock; chưa đo p95, throughput nhiều worker hoặc chi phí suy luận LLM.
