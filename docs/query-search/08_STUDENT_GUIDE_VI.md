# Hướng dẫn sinh viên: đánh giá Query/Search bằng bằng chứng thực thi

## 1. Query cần hiểu điều gì?

Query không giải bài toán pháp luật thay người dùng. Nó xác định cần tìm quy định nào và giữ các dữ kiện có liên quan. Câu hợp đồng hai năm, làm sáu tháng, muốn nghỉ có ít nhất hai mục tiêu tìm: báo trước và bồi thường. Chỉ tách theo dấu hỏi có thể giữ nguyên cả đoạn thành một truy vấn dài. Ngược lại, tách quá nhiều có thể mất bối cảnh hoặc thêm vấn đề không cần thiết.

`src/applications/tillegal/agents/query/agent.py::understand` là đường deterministic: kiểm tra type/length/control characters, chuẩn hóa NFC, giữ original nguyên vẹn, nhận ngày/citation lookup và lập plan offline hẹp. Nó không phải model ngữ nghĩa tổng quát. Ngoài labour, trường domain hiện chỉ có unknown; không suy ra hệ thống đã có classifier đa ngành.

## 2. Gemini được gọi thế nào?

`src/query_search_bootstrap.py::create_query_search(... semantic_mode="gemini")` gọi `query/gemini.py::create_gemini_query_agent`. Factory đọc provider/profile và GOOGLE_API_KEY hiện có, rồi tạo SemanticQueryAgent với GeminiStructuredCompletion. Model thực tế đã kiểm tra là gemini-3.5-flash-lite, timeout 30 giây. Không đổi key hoặc đưa key vào prompt/log.

Trong `QuerySearch.search`, lời gọi `SemanticQueryAgent.understand` chạy validation trước. Nếu câu cần clarification hoặc lookup nguyên văn, nó trả nhãn deterministic và không gọi API. Câu thường được gửi qua `src/framework/llm/providers/gemini_adapter.py::__call__`, LiteLLM route gemini/, yêu cầu JSON theo schema, không retry/fallback.

`query/schemas.py::SemanticAnalysis` gồm intent, domain, facts, issues, missing_information, temporal_mentions, clarification. Mỗi issue có issue/search_query; mỗi fact có text/source_quote. Schema có max counts/lengths và cấm extra fields. Hai trường fact phải giống hệt và là span trong câu hỏi. Tên điều luật/số liệu mới do model thêm bị guard từ chối. JSON đúng cấu trúc chưa đủ: baseline có JSON hợp lệ nhưng intent sai nên không được Search tiếp nhận.

## 3. Dữ kiện khác thông tin cần hỏi thế nào?

“Hợp đồng 2 năm” là dữ kiện đã nêu; “có thỏa thuận đào tạo không” có thể là thông tin còn thiếu. Nếu câu đã nói không có thỏa thuận đào tạo thì hỏi lại là thừa. `missing_information` dùng để mô tả dữ kiện còn thiếu nhưng vẫn có thể tìm quy định chung; `clarification` khác hẳn, nó chặn Search vì chưa đủ rõ mục tiêu.

Model có thể hỏi thừa, bỏ sót hoặc gộp mục tiêu dù schema đúng. Benchmark dùng alias terms để phát hiện dấu hiệu, không có quyền coi đó là chấm điểm pháp lý hoàn hảo. Một mục hỏi “thỏa thuận đặc biệt” có thể bị proxy nhầm là hỏi lại loại hợp đồng: phải đọc raw response, không chỉ nhìn số.

## 4. QueryPlan được Search dùng ra sao?

`QueryPlan` giữ original, intent, domain, temporal_scope, subqueries, clarification và các trường phân tích. `search/agent.py::search` validate plan/options, sau đó tạo RetrievalRequest cho từng subquery với mode/top_k/as_of_date/policy do caller đưa vào. Gemini không tự được quyền đổi filter ngày/policy. temporal_scope là ghi nhận ngôn ngữ; caller phải chọn ngày áp dụng đúng, nhất là câu lịch sử.

Search cache query giống hệt trong một lần chạy. Dù dùng lại response, các slot plan/request/response vẫn giữ vị trí để tương thích handoff. Không gộp query chỉ vì có vẻ gần nghĩa. Khi một response FAILED, Search dừng, giữ kết quả trước lỗi và trả completeness PARTIAL/FAILED cùng skipped indices. Không báo hoàn thành giả. Cancellation và lỗi lập trình bất ngờ tiếp tục truyền lên runtime.

## 5. RetrievalService và Supabase

`src/retrieval_bootstrap.py::create_retrieval_service` tạo client và read repositories; không chạy ASGI worker, crawl hoặc migrations. `src/integrations/database/repositories/rpc.py::SupabaseRpcRepository.call_rpc` gọi các RPC hiện hữu trong worker thread.

BM25 dùng tokenizer cùng index, gọi search_sparse_legal_chunks, nhận chunk IDs/scores rồi hydrate bằng chunk/source repositories. RetrievalService kiểm tra index trước/sau, source/date/policy và content hash. Dense cần E5 local, thêm query prefix, tạo vector rồi gọi vector repository/RPC. Hybrid gọi hai nhánh và RRF đã có. Rerank là lựa chọn thêm trên hybrid, cần cross-encoder local; chỉ khi metadata nói APPLIED mới khẳng định inference đã chạy. Không gọi hybrid là đã rerank.

Task này không sửa bốn thuật toán trên. Có checkpoint trên đĩa chưa có nghĩa model đã được nạp. Cold Dense thực tế timeout lúc encoding; Hybrid kế tiếp báo MODEL_BUSY vì worker chưa xong. Sau khi harness nạp model riêng và đo initialization, cả bốn mode trả kết quả thật. Vì vậy khi đọc latency phải tách bootstrap, load model và search, không vội quy lỗi database.

## 6. Evidence và provenance

`search/agent.py::_finish` gom bằng chứng bằng toàn bộ payload nguồn, chỉ bỏ rank/score/method cục bộ khi tạo key. Chunk ID, source_document_id, structure ID, snapshot, ngày, hash và metadata khác nhau thì không tự gộp. Bản đại diện có rank của lần xuất hiện đầu, không phải global rank.

`search/schemas.py::EvidenceOccurrence` giữ subquery_index, response_index, query, request_id, rank/raw_score/score_kind. Có thể lần từ một nhóm evidence về đúng query và native response, rồi xem fusion/reranking metadata. Không cộng BM25 với cosine/RRF hoặc sort lại rerank bằng RRF score. Những điều này đã được kiểm tra bằng ID/hash thực từ Supabase, không chỉ bằng mock.

Q004 thực tế có sáu lần xuất hiện được gom còn bốn hoặc năm nhóm tùy plan. Tất cả liên kết occurrence và SHA-256 đều khớp trong các run thành công. Nhưng một chunk đúng hash có thể không liên quan hoặc thiếu hiệu lực: provenance không thay cho Judge/Verification.

## 7. Benchmark đo gì và không đo gì?

`evaluation/query_search/cases.json` có 45 câu, 15 nhóm, ground truth được viết trước model. `scripts/evaluate_query_search.py` lưu raw synthetic-case responses, plan, lỗi, usage, latency, prompt/dataset hash và metric theo nhóm. `score` kiểm facts/citations/times và proxy từ vựng; `objective_assignment` chỉ ghép một query với một objective trong phép đo phân rã. Mọi kết quả semantic vẫn cần người có chuyên môn rà soát.

Benchmark không chứng minh điều luật tồn tại/áp dụng, không tạo đáp án pháp lý, không đo chính xác pháp lý trên toàn bộ luật Việt Nam. Không có corpus relevance judgments, nên không có Recall@K/Precision@K/NDCG đáng tin. Không lấy output Gemini làm ground truth. Phải đọc số lỗi cùng coverage: coverage 1.0 trong 12 plan được nhận không có nghĩa 15/15 thành công.

## 8. Bài học từ before/after

Baseline Gemini nhận 12/15 plan. Prompt dài thử nghiệm sửa ba lỗi ban đầu nhưng làm giảm thông tin cần hỏi và phân rã mục tiêu, mất số hiệu văn bản và thêm lỗi fact paraphrase. Vì vậy prompt đó không được đưa vào mặc định. Nó vẫn nằm trong artifact để người khác kiểm tra, không bị xóa khỏi lịch sử.

Code giữ lại hai thay đổi nhỏ: schema gửi provider chỉ cho legal_question ở nhánh semantic vốn không nhận quote_lookup; và với một objective, khôi phục literal citation user đã đưa nếu model bỏ sót. Không rải mọi citation vào các objective không liên quan. Các guard cũ vẫn chặn sai khác facts/ngày/số liệu; không nới validation để có bảng điểm đẹp.

Mẫu cuối nhận 5/6 plan, và trên năm câu có baseline tương ứng là 4/5 so với 2/5. Đây là mẫu nhỏ nhắm lỗi, không phải chứng minh toàn benchmark đã cải thiện. Q025 còn đưa số hiệu văn bản vào temporal_mentions và bị chặn. Cả lỗi và proxy regression đều được báo cáo. Không kết luận semantic đã cải thiện relevance tổng thể: consumer real retrieval còn proxy 0/2.

## 9. Đọc và chạy lại theo thứ tự

1. Đọc 01_EVALUATION_DESIGN.md và cases.json để hiểu ground truth/denominator trước khi nhìn kết quả.
2. Đọc 02_BASELINE_RESULTS.md và raw gemini-before.json; phân biệt raw schema valid với plan accepted.
3. Đọc 03_REAL_RETRIEVAL_E2E.md và các native response để lần QueryPlan → request → occurrence → source.
4. Đọc 04_FAILURE_ANALYSIS.md, 05_IMPROVEMENTS.md, 06_BEFORE_AFTER.md để biết thay đổi nào giữ lại và thử nghiệm nào bị loại.
5. Đọc 07_FINAL_VERIFICATION.md để xem lệnh/count thực tế. Chạy script bằng `python -m scripts.evaluate_query_search ...` hoặc `evaluate_query_search_retrieval ...` với output filename mới. Gemini dùng quota thật; replay plans vào retrieval không gọi model lại. Đặt offline flags để không tải E5/cross-encoder.

Graph hiện hữu vẫn dùng Query deterministic. Không thay Judge/Summary/Answer/Verification hoặc graph để biến đánh giá này thành toàn bộ hệ thống đa agent. Các bước tiếp theo là human relevance review, dataset rộng hơn, xử lý thời gian phù hợp và đánh giá model theo ngân sách riêng; chưa được coi là tính năng đã hoàn tất.
