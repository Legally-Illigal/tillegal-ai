# 23 — Hướng dẫn kỹ thuật Query/Search và điều tra relevance

## 1. Luận điểm cần giải thích khi bảo vệ

Query biến câu hỏi thành kế hoạch tìm kiếm. Search thực thi kế hoạch qua RetrievalService và lưu nguồn gốc từng kết quả. Một lần chạy thành công chỉ chứng minh việc gọi, xác thực và chuyển dữ liệu đã hoàn tất; không chứng minh đoạn trích trả lời được câu hỏi hoặc pháp luật đó áp dụng cho tình huống. Đây là khác biệt cốt lõi giữa đúng về kỹ thuật, liên quan về nội dung và đúng về pháp lý.

Đợt này không viết lại prompt và không sửa production. Thí nghiệm thật cho thấy đổi truy vấn làm thay đổi thứ hạng nhưng chưa cải thiện ổn định; danh sách nguồn nhìn thấy thiếu bản ghi số hiệu cần tra cứu. Vì vậy thay đổi hợp lý là hoàn thiện công cụ điều tra và bằng chứng bàn giao, không thêm cơ chế lọc theo phỏng đoán.

## 2. Kiến trúc và thứ tự thực thi hiện tại

Các đường dẫn dưới đây tương đối so với `D:/DOWNLOAD/tillegal-ai/tillegal-ai-main`. Đây là đường dẫn mã đang tồn tại, không phải kiến trúc đề xuất.

|Thứ tự|File/hàm|Đầu vào|Đầu ra/trách nhiệm|
|---|---|---|---|
|1|src/query_search_bootstrap.py:create_query_search|SupabaseSettings, SearchOptions, semantic_mode|QuerySearch với planner và RetrievalService; mặc định deterministic|
|2|src/query_search_bootstrap.py:QuerySearch.search|question:str|Gọi planner rồi search; trả SearchState|
|3a|src/applications/tillegal/agents/query/agent.py:understand|Câu hỏi gốc|dict theo QueryPlan; kiểm tra đầu vào, tách deterministic|
|3b|src/applications/tillegal/agents/query/semantic.py:SemanticQueryAgent.understand|Câu hỏi và StructuredCompletion đã inject|Plan ngữ nghĩa đã qua Pydantic/grounding hoặc lỗi có mã|
|4|src/applications/tillegal/agents/query/context.py:parse_context|Văn bản NFC/trim|Danh sách LegalReference và TemporalContext có span|
|5|src/applications/tillegal/agents/search/agent.py:search|Plan, RetrievalService, SearchOptions|Requests/responses/evidence/warnings/errors/completeness|
|6|src/retrieval_bootstrap.py:create_retrieval_service|Cấu hình DB, checkpoint tùy chọn|Service nối các adapter read; không thay schema|
|7|src/application/services/retrieval_service.py:RetrievalService.search|RetrievalRequest|Response BM25/Dense hoặc subtype Hybrid/rerank|
|8|src/applications/tillegal/agents/search/agent.py:_finish|Plan và native responses|Gộp payload giống hệt, giữ occurrence/rank/issue liên quan|

Graph không thay đổi trong đợt điều tra. Có test graph/handoff để phát hiện hồi quy, nhưng không triển khai hay nối thêm Judge/Summary/Answer/Verification.

## 3. Deterministic Query làm gì?

`agent.py:understand` nhận chuỗi, kiểm tra kiểu, độ dài, ký tự điều khiển, chuẩn hóa NFC để phân tích, nhưng giữ nguyên đối số trong `original`. Nó nhận biết tra cứu trích dẫn, một số chủ đề lao động và các phần câu hỏi; trả clarification khi không có mục tiêu rõ hoặc có ngày không hợp lệ. Đây là tập quy tắc, không phải bộ suy luận pháp lý tổng quát.

QueryPlan chứa intent, domain, temporal_scope, subqueries, clarification, facts, issues, missing_information và bốn trường metadata mới đã có từ đợt trước. Tối đa4 subquery. Hiện domain chỉ có labour/unknown; không nên mô tả hệ thống như bộ phân loại đầy đủ mọi lĩnh vực pháp luật.

Chế độ này chạy offline không cần LLM. Search thật vẫn cần Supabase; chỉ các test dùng fake ports mới chạy không có DB. Offline Query và offline retrieval là hai khái niệm khác nhau.

## 4. Vì sao có Gemini và nó được bật thế nào?

Gemini giúp nhận ra nhu cầu độc lập trong câu dài: ví dụ Q040 có người vay A và bên bảo lãnh B; Q005 có nuôi con và tài sản. Lợi ích kỳ vọng là phân tích ngôn ngữ, không phải thay cơ sở dữ liệu luật hay đảm bảo câu trả lời đúng.

`query/gemini.py:create_gemini_query_agent` chỉ đọc profile query_semantic ở configs/models.yaml và GOOGLE_API_KEY; GEMINI_MODEL có thể ghi đè tên model. Model đang cấu hình là gemini-3.5-flash-lite. `src/framework/llm/providers/gemini_adapter.py:GeminiStructuredCompletion.__call__` dùng LiteLLM, yêu cầu JSON với schema, timeout, num_retries=0, không cache và không log request. Đợt này không gọi Gemini mới; các plan C đều lấy từ kết quả thật đã lưu.

Bật rõ trong code ứng dụng hiện có:

```python
runner = create_query_search(settings, options, semantic_mode="gemini")
result = await runner.search(question)
```

Không in settings hay key. Khi không truyền semantic_mode, mặc định deterministic. Profile OpenAI dùng cho phần khác vẫn tồn tại; sự hiện diện của default_model OpenAI không có nghĩa Query semantic đang gọi OpenAI.

## 5. Gemini không được tin vô điều kiện

`SemanticQueryAgent.understand` luôn gọi deterministic trước. Nếu cần clarification hoặc là quote_lookup thì trả ngay, không gọi model. Với câu hỏi thông thường, agent truyền question, reference_spans, temporal_candidates và user_supplied_slots; model chỉ được trả intent legal_question theo schema.

Sau phản hồi, `SemanticAnalysis.model_validate_json` kiểm tra cấu trúc chặt. source_quote của fact phải có nguyên văn trong câu hỏi đã chuẩn hóa. Thời gian phải có căn cứ; số và citation mới không được tự xuất hiện trong nội dung sinh ra. Những kiểm tra này ngăn một số kiểu bịa nhưng không chứng minh mọi suy luận ngữ nghĩa đúng.

Q007 là ví dụ quan trọng: phản hồi chính không khớp source quote do dấu câu, nên agent trả QUERY_ANALYSIS_INVALID_RESPONSE. Không âm thầm dùng deterministic để làm lượt Gemini trông thành công. Lượt lặp cũ từng thành công chỉ cho thấy biến thiên; không được lấy nó thay lỗi chính. Đây là giới hạn phải báo cáo, không nên nới grounding chỉ để tăng điểm.

## 6. Phân biệt dữ kiện, lời cáo buộc và kết luận pháp lý

facts là thông tin được trích từ câu người dùng. Câu “một bài viết nói Điều35 cho nghỉ ngay mọi trường hợp” chứa một phát biểu cần kiểm chứng, không phải quy tắc đã được xác nhận. Q025 vẫn giữ phát biểu người dùng trong facts; downstream phải giữ ngữ cảnh original và yêu cầu kiểm chứng.

Planner tránh mang fact có citation hoặc dạng câu hỏi vào phần bối cảnh chung của mọi query, nhưng đây không phải bộ phân loại allegation hoàn chỉnh. Không được trình bày fact extraction như một bước xác minh sự thật.

`supplied_context` nhận diện một số slot hẹp như thời hạn hợp đồng, lý do nghỉ và thỏa thuận đào tạo. `reconcile_missing` loại một số câu hỏi lại dữ kiện đã có, giữ điều chưa biết. Cơ chế này không phải ontology pháp lý đa lĩnh vực. Benchmark trước còn có missing-info7/12 so với8/12 lịch sử; đợt này không thay thuật toán và không tuyên bố đã sửa hết.

## 7. Citation và thời gian khác nhau thế nào?

`context.py:parse_context` đánh dấu span cho số hiệu, điều/khoản/điểm, tên luật kèm năm; phân biệt ngày lịch, năm sự kiện, khoảng thời gian, mốc lịch sử và phủ định. `schemas.py:LegalReference` ghi user_supplied_unverified; `TemporalContext` có role, iso_date, negated. Ngày ISO được kiểm tra lịch; không suy ngày hiệu lực từ năm trong số hiệu.

Ví dụ45/2019/QH14 là định danh văn bản, không phải ngày áp dụng. Q025 có lần model đưa chuỗi này vào temporal_mentions; `classify_model_time` phân loại lại và cảnh báo MODEL_REFERENCE_RECLASSIFIED. Q019 có “không phải hiện nay”; mốc hiện nay vẫn có span negated nhưng không trở thành active temporal_scope.

Offsets theo bản NFC đã trim, không phải chỉ số byte của raw input. Original vẫn được giữ. Temporal_context thể hiện yêu cầu/ngữ cảnh người dùng; `SearchOptions.as_of_date` là ngày caller tin cậy cung cấp. Trong thử nghiệm Q019,2010-12-31 là mốc nghiên cứu được chỉ định, không phải ngày hệ thống tự suy ra giao dịch xảy ra.

## 8. Issue, objective và subquery

Issue là nhu cầu thông tin có thể tìm độc lập. Nhiều issue có thể dùng chung query nếu model đưa cùng chuỗi; `search_objectives` ánh xạ query_index tới issue_indices. QueryPlan kiểm tra chỉ số hợp lệ, không tham chiếu issue/query không tồn tại. Trùng query được loại đúng chuỗi; Search cũng cache truy vấn trùng hệt trong cùng lượt.

Q040 plan C có hai query: nghĩa vụ trả nợ và trách nhiệm bảo lãnh, mỗi query thêm bối cảnh A vay/B bảo lãnh/A không trả. Các dữ kiện có thể cần cho hiểu tình huống, nhưng với BM25 chúng cũng thêm từ làm lệch hạng. Không có quy luật “query càng dài càng tốt”.

Q004 C dài187/185 ký tự; D nghiên cứu dài62/52. Với query báo trước, chunk dẫn chiếu chuyển từ rank5 lên1. Tuy nhiên chunk đó là quy định hoàn trả hỗ trợ địa phương, không phải chính văn điều luật chung cần tra. Đây là thay đổi thứ hạng đã đo, chưa phải tăng relevance chuyên gia. Vì Q001 và Q040 không cải thiện ổn định, D không được đưa vào production.

## 9. Search truyền gì cho RetrievalService?

`SearchOptions` yêu cầu mode, top_k, as_of_date và allowed_usage_policies. Search xác thực options và plan, tạo RetrievalRequest cho mỗi subquery. Nó không để model tự chọn policy, không đổi ngày theo một năm tình cờ trong citation, không tự chuyển backend khi có lỗi.

`RetrievalService.search` chọn nhánh, kiểm tra index/config, tìm candidate, hydrate chunk/source, kiểm tra hash và metadata. Source ID/chunk ID giúp truy vết nội dung; hash đúng chỉ chứng minh nội dung khớp bản lưu, không chứng minh luật đúng hoặc áp dụng.

Một request Search có nhiều lệnh đọc DB/RPC phía dưới.28 lượt Search trong thí nghiệm không có nghĩa chỉ có28 HTTP request. Corpus luôn chỉ đọc, không upsert/migration/index rebuild.

## 10. Bốn phương pháp retrieval đóng góp gì?

BM25: `SparseRetrievalRepository.search` gọi RPC search_sparse_legal_chunks. `vbpl_markdown_indexing_service.py:tokenize_sparse_text` tách token Unicode, lowercase/NFC, giữ dấu và số. SQL trong repository cộng điểm theo term frequency/document frequency và chuẩn hóa độ dài. Đây là bag of tokens, không phải cơ chế bắt buộc nguyên cụm pháp lý hay đúng số hiệu nguồn. Từ “hiệu lực”, “hợp đồng” có thể đẩy mẫu hợp đồng đào tạo lên cao.

Dense: `E5QueryEncoder.encode_query` dùng checkpoint multilingual-e5-small local CPU, prefix query:, vector384 chiều chuẩn hóa. `SupabaseVectorRepository` tìm gần trong index tương ứng. Tương đồng vector tìm ngữ nghĩa gần nhưng không xác thực loại quan hệ pháp lý; hợp đồng mẫu vẫn có thể gần câu hỏi về hợp đồng dân sự.

Hybrid: `hybrid_retrieval.py:search_hybrid` chạy hai nhánh tuần tự, kiểm tra cùng ngữ cảnh và index. `rank_fusion.py:reciprocal_rank_fusion` cộng1/(60+rank) trong cấu hình thí nghiệm, gộp theo chunk ID đã kiểm tra integrity; không cộng trực tiếp BM25 với cosine. Nếu cả hai nhánh cùng ưu tiên nguồn sai mục tiêu, RRF vẫn có thể đưa nguồn đó lên đầu.

Reranking: `LocalCrossEncoder.score_pairs` chấm cặp query/passage bằng checkpoint local. `application/services/reranking.py:search_reranked` lấy candidate từ Hybrid rồi dùng `reranker.py:select_candidates` sắp lại. Native evidence raw_score vẫn mang ý nghĩa RRF, điểm cross-encoder ở metadata riêng; người dùng downstream phải theo rank/order cuối, không tự sort raw_score. Operational fallback phải có trạng thái/cảnh báo rõ.

Thí nghiệm dùng10 candidates mỗi nhánh, rerank pool10. Reranker không đọc toàn corpus; nó không thể đưa vào một chunk chưa có trong pool được truyền cho nó. Cả3 phản hồi rerank thật đều APPLIED, không phải chạy fallback mà ghi thành công giả.

## 11. Search gộp evidence ra sao?

`_finish` dùng payload nguồn đầy đủ làm khóa, bỏ các trường rank/raw_score/score_kind/retrieval_method vốn phụ thuộc truy vấn. Cùng chunk nhưng version, snapshot, metadata hoặc content khác thì không gộp. Mỗi occurrence giữ query, response_index, request_id, rank, score và issue_indices.

Trong15 saved run thành công,57 occurrence native đều còn nguyên trong aggregate. Q004 deterministic có một payload lặp giữa hai truy vấn; aggregate gộp payload nhưng giữ cả hai occurrence. Những khoản khác nhau của cùng văn bản không phải duplicate chỉ vì giống chủ đề. Search không có chức năng đa dạng hóa kết quả và không tự loại các khoản tương tự.

Khi một query thất bại, Search dừng các query sau, giữ evidence trước đó và ghi PARTIAL/skipped_subqueries. COMPLETE có nghĩa thực thi đủ, không có nghĩa đủ chứng cứ pháp lý. Các test giả lập kiểm chứng lỗi từng phần, cancellation, phiên bản xung đột và NO_MATCH; thí nghiệm thật đợt này không cố gây outage.

## 12. Ví dụ phân biệt nguồn đúng và dẫn chiếu

Q022 yêu cầu Điều35 Bộ luật Lao động45/2019/QH14. Chunk2973a693-2276-4e4f-a233-f7038e4717e0 thuộc nguồn60c5be9f-20d9-4897-977e-2059f2c59ff2, Nghị quyết25/2026/NQ-HĐND. Vị trí thực là Điều5 Khoản2 Điểmb của nghị quyết, nội dung nhắc khoản2 Điều35 của bộ luật.

Cả BM25, Dense, Hybrid và rerank đều xếp chunk này đầu. Đó là mismatch nguồn đã quan sát; không cần suy đoán thuật toán để thấy rằng dẫn chiếu không phải chính văn cần tra. Search hiện cảnh báo EXACT_LOOKUP_SOURCE_IDENTITY_UNCONFIRMED khi quote_lookup có số hiệu không xuất hiện trong tiêu đề nguồn trả về. Cảnh báo không đổi ranking và không kiểm chứng pháp lý. Nó không bao phủ mọi legal_question như Q025; thiếu cảnh báo không phải xác nhận nguồn.

## 13. Coverage được kiểm tra và giới hạn ra sao?

`investigate_query_relevance.py:metadata` đếm và phân trang source_documents theo id. Thực tế58 unique row, count trước/sau đều58; có2609 chunk. Toàn bộ metadata trước/sau thí nghiệm giống nhau. Đây là phạm vi đầy đủ với credential hiện tại ở thời điểm đọc, không phải snapshot transaction hay chứng minh mọi DB trên thế giới.

Không có bản ghi document_number45/2019/QH14 trong58 row; equality probe cũng trả0. Trong chunk content, literal số hiệu lại có1 match chính là nghị quyết dẫn chiếu. Vì thế có thể nói thiếu identity trong scope đã kiểm tra; không thể nói tuyệt đối không có một đoạn trích/paraphrase tương ứng dưới identity khác.

Các literal “bảo lãnh”, “ly hôn”, “giao dịch dân sự” trả0 visible chunk. Đây là kết quả substring query, không phải semantic search exhaustive: cách diễn đạt, Unicode và nguồn ngoài scope vẫn có thể khác. Literal “nghĩa vụ trả nợ” có1 match nhưng là nội dung tuyên truyền tín dụng chính sách, không phải đầy đủ nghĩa vụ trong vụ A/B.

## 14. Tại sao ngày hiệu lực là blocker riêng?

Không source nào có effective_from được ghi nhận<=2010;2 source để null. Q019 dùng date2010 nhưng nhận văn bản issued_on2026-08-05 có effective_from/to null. Local RPC cho phép null ngày hiệu lực đi qua. Nó giữ dữ liệu chưa rõ; không hề chứng nhận văn bản có hiệu lực năm2010.

Không nên tự loại mọi tài liệu xuất bản sau sự kiện, vì văn bản hợp nhất sau này có thể ghi lại quy tắc cũ. Cũng không nên tự coi null là áp dụng mọi thời điểm. Cần metadata và kiểm chứng pháp lý riêng do owner phụ trách. Đợt này không sửa filter hay dữ liệu.

## 15. Thiết kế thí nghiệm tránh tự đánh lừa

Ưu tiên dữ liệu cũ:57 dòng và plan thật đã lưu. Không gọi Gemini để chọn đáp án thuận lợi. Chọn trước4 case cho A/B/C/D, thêm3 case đại diện cho4 mode, chạy tuần tự để không chồng inference CPU. D chỉ là biến nghiên cứu. Các cấu hình policy/date/index/candidate budget giữ cố định; không vừa đổi corpus vừa đổi truy vấn.

Mỗi lần chạy lấy depth10 và xem prefix3/5/10. Không gọi chúng là ba thí nghiệm top-k độc lập.30 dòng schedule gồm28 call thật và2 alias query giống hệt. Timing load E5=15.746s và CE=3.252s được tách khỏi query latency; thời gian từng request vẫn gồm mạng, hydrate và inference. Không lấy median3 case để kết luận mô hình nào nhanh hơn nói chung.

## 16. Nhãn relevance và artifact review

`build_review` tái dùng57 review_id và full chunk, bổ sung issue/objective/query/mode/rank/temporal metadata. Nhãn, reviewer, reason đều null. `HUMAN_REVIEW_QUEUE.md` có bản đọc được; human_review.json có bản máy đọc.280 candidate occurrence mới của thí nghiệm nằm riêng experimental_review.json, cũng null.

Rubric0: không liên quan;1: có chủ đề rộng nhưng chưa đúng mục tiêu;2: liên quan một phần;3: trực tiếp với objective. Đây là rubric relevance, không chứng nhận đúng luật.19 nhận xét assistant-provisional cũ giữ riêng, không trở thành nhãn chuyên gia. Khi không có người chấm, P@K/NDCG chuyên gia phải để null.

Một lỗi evaluator được sửa: Q022 hai variant có query giống nhau nên ghép chỉ theo text sẽ lẫn nguồn variant. Nay dùng blind_variant_token có sẵn kết hợp query/chunk/rank. Draft human_review.initial_join.json được giữ và đánh dấu superseded. Không sửa dữ liệu gốc để che lỗi, không nhầm lỗi evaluator này thành lỗi Search.

## 17. Kiểm thử chứng minh gì?

10 test mới trong test_relevance_investigation.py kiểm tra không lẫn variant khi query giống nhau, không biến nhãn provisional thành human, fail khi không xác định được identity, phát hiện đổi rank/score/chunk/issue link và giữ blocked plan. Bộ focused578 pass; toàn bộ667 pass; Ruff pass. Các test cũ kiểm tra contract, source version, provider failure, JSON, timeout và graph handoff.

Test pass chứng minh hành vi đã đặc tả trên các fixture/case đó.28 lượt Search thật chứng minh kết nối và các mode hoạt động với cấu hình hiện tại. Không kết quả nào tự biến thành bằng chứng legal correctness, corpus đủ hoặc Gemini hơn deterministic toàn diện.

## 18. Cách chạy lại và bảo vệ kết luận

Từ project root, chạy offline để tái tạo báo cáo từ raw đã giao:

```powershell
.\.venv\Scripts\python.exe -m scripts.investigate_query_relevance --analyze-only
```

Lệnh live, checkpoint paths, options và command test đầy đủ ở tài liệu18/21. Dùng thư mục output mới, không ghi đè raw. Không in key/header; không crawler/DB write/model download. Công cụ không gọi LLM.

Khi được hỏi “sao không chỉ sửa prompt?”, trả lời bằng Q022: số hiệu cần tra không có bản ghi trong visible metadata, còn kết quả là dẫn chiếu; đổi prompt không bổ sung nguồn. Khi được hỏi “có phải Retrieval sai?”, nêu rằng đã thấy ranking chưa phù hợp nhưng chưa có relevant ground truth chứng minh lỗi thuật toán. Khi được hỏi “hệ thống sẵn sàng chưa?”, dùng bảng22 theo từng khả năng: contracts/execution có thể READY; relevance chuyên gia, corpus adequacy và applicability còn BLOCKED.

Điểm cần bàn giao tiếp: người chấm relevance; corpus owner xác minh identity và ngày; Retrieval owner đánh giá candidate recall/ranking trên chunk đúng đã xác định. Những việc đó chưa được triển khai trong đợt này. Không có production Query/Search change, không thay graph và không commit/push.
