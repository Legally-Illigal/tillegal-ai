# Real-generation và semantic verification — kết quả pilot

**Quyết định:** giữ semantic ở development. Đã chạy được LLM tiếng Việt thật qua loopback, sinh claim diễn giải, kiểm tra claim bằng evidence gốc và đo ba workflow. Chất lượng trả lời tự động còn thấp. Một nguồn biểu mẫu trống đã khiến model tự thêm số ngày. Một câu dẫn chưa có các trường hợp ngoại lệ được verifier chấm SUPPORTED theo nghĩa văn bản.

## Thực nghiệm

Bốn truy vấn X01–X04 trong scripts/compare_legal_qa.py là dữ liệu chẩn đoán công khai trong workspace, tách biệt T5. Cùng BM25/index pilot, top_k=1 mỗi search, cùng model sinh và cùng câu hỏi. Basic dùng chính lớp BasicRAG chưa sửa. Draft và semantic dùng cùng graph Query/Search/Judge và cùng prompt sinh. Chỉ semantic gọi bộ kiểm claim và áp dụng điều kiện công bố. Số lượt tìm có thể khác basic theo thiết kế. Mỗi ca/mode chạy một lần, cùng process cho các mode của từng experiment, sau khi nạp index; model phục vụ trên CPU riêng qua localhost, có cache. Thứ tự cố định. Đây là thời gian end-to-end gồm cả lỗi và abstention, chưa phải SLA hoặc hiệu ứng nhân quả của riêng verifier.

| Model local, 4 ca/mode | Có draft | Abstain / rỗng | Lỗi | Median ms | Tổng token input / output được backend báo |
|---|---:|---:|---:|---:|---:|
| BasicRAG | 0 | 1 | 3 | 6.453,5 | 8.509 / 299 |
| Multi-agent draft | 2 | 2 | 0 | 862,0 | 410 / 108 |
| Multi-agent semantic | 0 | 4 | 0 | 2.317,6 | 933 / 308 |

Ba lỗi BasicRAG bản đo cuối là INVALID_OUTPUT ở bước validate structured output. Basic dùng prompt/JSON parser ban đầu; hai mode mới dùng JSON-schema constrained decoding trên server local. So sánh này đánh giá các hệ thống cuối, không thể quy phần chênh lệch cho kiến trúc multi-agent đơn thuần. Các lượt sơ bộ cũng gặp timeout 25 giây. Khi backend không cung cấp usage, báo thiếu số liệu. Phép đo chạy lại có thể chênh lệch do cache, CPU và sampling/runtime.

**Mock, cùng bốn ca:** Basic trả 3 draft và 1 no-evidence, median 6,0 ms; multi draft trả 2 và abstain 2, median 21,8 ms; multi semantic abstain 4, median 23,8 ms. Mock không được cấp verdict semantic. **External API:** 0 lượt. Không dùng Gemini, billing hay API key.

## Chất lượng từng bước và lỗi có thể tái hiện

- **Query/Search:** X01 nhận ra chủ đề nghỉ hằng năm nhưng kết quả chuyển sang Response là dòng trống của biểu mẫu. X03 có hit và bundle ASSEMBLED nhưng Judge không tìm thấy cụm hỏi trong body phù hợp. Với X04 vô nghĩa, refinement thêm từ khóa pháp lý rồi tìm ra văn bản. Đây là nhiễu, không tạo được bằng chứng trả lời.
- **Judge:** Trong X02 câu hỏi cần định nghĩa làm thêm giờ, Judge cho chọn câu dẫn về một trường hợp đặc biệt. Hệ thống có thể báo không bỏ chunk nào theo EvidenceBuilder nhưng tập được chọn cho Response vẫn thiếu nội dung theo sau dấu hai chấm. Cần đánh giá riêng recall của điều kiện/ngoại lệ trong context cuối.
- **Response:** X01 trả “10 ngày” từ dòng biểu mẫu không chứa số ngày; X02 chủ yếu sao chép câu dẫn và chưa trả lời định nghĩa. Đây là nhận xét kỹ thuật khi đọc nguồn/trace, chưa phải nhãn groundedness do chuyên gia duyệt. Mọi claim có ID riêng; alias ngắn E1… được map về evidence ID canonical trong run. ID lạ làm fail schema/contract, danh sách rỗng cho phép abstain.
- **Verifier:** xét từng claim bằng một chunk gốc đã kiểm hash. Giữ source version/chunk/hash, offsets Unicode trên normalized chunk, rationale, usage, elapsed time và version prompt. SUPPORTED và CONTRADICTED cần span khớp chính xác, định vị duy nhất. Mismatch, lý do giữ chỗ hoặc lỗi provider trả NOT_EVALUATED. Temporal applicability và source reachability vẫn tách riêng. Claim chỉ được công bố trong semantic nếu SUPPORTED và vượt qua kiểm tra source chưa hoàn chỉnh/biểu mẫu trống/câu dẫn thiếu danh sách. Đây là heuristic bảo thủ có thể loại cả quote hợp lệ; nó không phát hiện được mọi ngoại lệ bị bỏ sót.
- **Ablation:** chạy lại verifier trên chính các claim và source đã lưu của nhánh draft, không sinh lại. Cả hai claim đã xuất của X01/X02 đều bị giữ lại khỏi final answer. So sánh main graph có bước sinh độc lập nên draft giữa hai lần gọi có thể khác.
- **Kiểm tra độc lập:** ba fixture phi pháp lý có quan hệ do người viết test xây dựng (không phải legal gold). Model trả đúng nhãn quy ước ở ca giữ 12 ngày và ca đổi 12 thành 3. Model gán CONTRADICTED thay vì INSUFFICIENT_EVIDENCE khi claim nói về hồ sơ đỏ nhưng nguồn chỉ nói về hồ sơ xanh. Do đó một span đúng vị trí vẫn có thể đi cùng verdict sai. Cùng model sinh và chấm là nguồn sai lệch cần kiểm tra ở milestone tiếp theo.
- Bộ 4 ca đã được dùng để chẩn đoán và chỉnh prompt/publication gate. **Không sử dụng nó như held-out test.** Các bản *-v1 và *-before-publication-check cho thấy những lỗi dẫn tới thay đổi; main results là local.json / mock.json / paired.json.

## Gold và chỉ số chất lượng

[Annotation guideline và kết luận từng câu T5](annotation-quality.md) · [audit identity/span](quality-results/readiness.json). Sáu ca có đoạn ứng viên đủ rõ để đưa vào vòng duyệt trước. Sáu ca cần xử lý điều kiện, ranh giới hoặc lỗi nguồn. Cả 12 vẫn pending; chưa công bố Recall/MRR/nDCG trên corpus. Runner frozen chạy xuyên suốt trên fixture tổng hợp và đo latency. Review về groundedness, answer relevance, claim/citation correctness và unsupported rate thật cần người đọc độc lập. Script score_answer_reviews.py tính các tỷ lệ đó khi có scorecard khớp checksum. Trường chưa có nhãn trong báo cáo local/mock là null. Không đồng nhất unsupported với hallucination: nhiều claim chỉ thiếu nguồn.

## Chạy lại

Sử dụng môi trường và PYTHONPATH trong [pilot-rag.md](pilot-rag.md), từ workspace chứa baseline và thư mục service. File output cần là file mới. Weights, binary và tests đều chạy local. Runtime và weights dưới .tmp/quality-llm chỉ phục vụ thử nghiệm trên máy, không đóng gói hoặc phân phối.

- Model [Qwen2.5-1.5B-Instruct-GGUF](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/tree/91cad51170dc346986eccefdc2dd33a9da36ead9), Q4_K_M, SHA256 `6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e`. Chọn model nhỏ để kiểm tra CPU/JSON; chưa đánh giá đủ để chọn cho tư vấn pháp luật.
- [llama.cpp b12125](https://github.com/ggml-org/llama.cpp/releases/tag/b12125), archive win-cpu-x64 SHA256 `968091ccb8c230e0cf7e0eed386310703bebae4a4fd4375f0c57db53958307d8`.

```powershell
.\.tmp\quality-llm\runtime\llama-server.exe -m .tmp/quality-llm/qwen.gguf --host 127.0.0.1 --port 18963 -a qwen-pilot -c 8192 -t 4 -np 1 --temp 0 --offline
```

Trong terminal khác:

```powershell
$env:PYTHONPATH="$pwd/.tmp/rag-integration-runtime;$pwd/tillegal-ai-main;$pwd"
.venv/Scripts/python tillegal-ai-main/scripts/compare_legal_qa.py --provider local --model qwen-pilot --port 18963 --output .tmp/comparison-new.json
.venv/Scripts/python tillegal-ai-main/scripts/replay_claim_verification.py .tmp/comparison-new.json .tmp/replay-new.json --model qwen-pilot --port 18963
.venv/Scripts/python tillegal-ai-main/scripts/probe_semantic_verifier.py --model qwen-pilot --port 18963 --output .tmp/probes-new.json
.venv/Scripts/python tillegal-ai-main/scripts/compare_legal_qa.py --provider mock --output .tmp/mock-new.json
```

Để thử POST, đặt TILLEGAL_RAG_PILOT=1, TILLEGAL_ANSWER_PROVIDER=local, TILLEGAL_ANSWER_MODEL=qwen-pilot, TILLEGAL_LOCAL_PORT=18963 trong environment development và khởi động AI Service như hướng dẫn pilot. Chọn workflow **draft** để xem nhánh nghiên cứu có thể trả nội dung thiếu căn cứ, hoặc **semantic** để chạy verifier. VERIFIER và RESPONSE có profile riêng, mặc định kế thừa ANSWER. Các mode basic và multi_agent giữ hợp đồng cũ.

## Thay đổi và milestone kế tiếp

- Code ứng dụng: graphs/semantic.py thêm structured claims, verifier, fail-closed và publication gate; multi_agent.py, legal_qa.py, chat.py nối mode mới; gateway.py thêm structured decoding cho local. BasicRAG, retrieval, EvidenceBuilder, weights embedding và indexes giữ nguyên.
- Công cụ: evaluate_frozen_retrieval.py, compare_legal_qa.py, replay_claim_verification.py, probe_semantic_verifier.py, score_answer_reviews.py và test_semantic_quality.py. Các runner so sánh chỉ cung cấp mock hoặc loopback local. Không can thiệp production, migration hay Git remote.
- Bước tiếp theo: chuyên gia duyệt T5 và scorecard cấp claim; thêm một bộ văn bản/câu hỏi độc lập có paraphrase, dẫn chiếu và các cặp “mâu thuẫn”/“không đề cập”. Đánh giá context cấp điều kiện, giữ đủ danh sách theo sau câu dẫn và lọc biểu mẫu theo legal intent trước khi generate. So sánh verifier khác model với chuyên gia trên cùng claim/span. Chỉ xét mở rộng phục vụ khi có accuracy, selective coverage/abstention và latency theo tải được duyệt.

[Trace so sánh local](quality-results/local.json) · [Đối chứng mock](quality-results/mock.json) · [Replay cùng claim](quality-results/paired.json) · [Probe verifier](quality-results/verifier.json)

## Kiểm thử cuối và lỗi giới hạn số học

Bản cuối đạt **117/117 AI Service tests trong 123,53 giây**, bật model retrieval thật ở cả bốn mode. Baseline được xác minh ở đầu milestone với **189/189 test trong 25,761 giây**. Runner frozen được chạy xuyên suốt trên fixture tổng hợp, nDCG khớp phép tính tay; nhãn của corpus thật vẫn pending.

Hai request HTTP chẩn đoán cùng top_k=3 cho thấy một claim giữ đúng giới hạn tối thiểu và một claim làm mất từ “ít nhất”. Trước sửa, verifier chấm cả hai SUPPORTED. Bản cuối bổ sung numeric_bounds và bốn test min/max, ghi NUMERIC_BOUND_REQUIRES_REVIEW nếu claim có cùng số nhưng làm mất/đổi hướng giới hạn. HTTP thật sau sửa giữ một draft và abstain ở ca còn lại, dù verdict mô hình vẫn được lưu nguyên để audit. Đây là quy tắc bảo thủ cho một số cách viết tiếng Việt và chữ số, chưa bao phủ số viết bằng chữ, mọi phủ định hoặc quan hệ giữa nhiều mệnh đề.

[Trace HTTP bản cuối](quality-results/diagnostic-http-bounds.json). Hai ca này được chọn sau khi đọc nguồn để chẩn đoán, cùng chủ đề với D01; chúng không phải dữ liệu độc lập. Benchmark bốn ca local/mock được đo trước khi thêm numeric-bound guard. Đã kiểm lại các claim lưu trong benchmark bằng guard mới và xác nhận quyết định công bố của bốn ca không đổi. Thời gian trong bảng vẫn là thời gian đo trước guard.
