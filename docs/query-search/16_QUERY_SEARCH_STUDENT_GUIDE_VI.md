# Hướng dẫn bảo vệ học phần: Query/Search hiện tại

## 1. Trách nhiệm và giới hạn

Query tạo kế hoạch tìm thông tin; Search thực hiện và tổ chức bằng chứng; RetrievalService tìm chunk bằng pipeline đã có. Các thành phần này không kết luận câu trả lời pháp luật hoặc chứng cứ đủ/chính xác. Judge/Summary/Answer/Verification và graph không được sửa.

Gemini giúp diễn giải nhu cầu đa vấn đề và ngôn ngữ tự nhiên. Rules vẫn cần cho input, literal source spans, schema, deadline, bounds và provenance—không thể giao việc bảo vệ source identity cho model hoàn toàn. Ngược lại rules không bao phủ mọi lý do, ngoại lệ hay quan hệ pháp luật. Benchmark cho thấy không thể khẳng định Gemini tốt hơn deterministic tổng thể.

## 2. Thứ tự gọi hàm thật

| Bước | File / hàm | Input → output |
|---|---|---|
|1|src/query_search_bootstrap.py::create_query_search|Settings/options + semantic_mode → QuerySearch; Gemini bật cho đường trực tiếp, graph vẫn deterministic|
|2|query/gemini.py::create_gemini_query_agent|Profile + GOOGLE_API_KEY hiện có → SemanticQueryAgent; không ghi key|
|3|QuerySearch.search → query/semantic.py::understand|Question → validation deterministic → một lần structured model → validated QueryPlan|
|4|query/agent.py::understand|String → kiểm type/length/control, NFC, legacy planning và context metadata; original giữ nguyên|
|5|query/context.py::parse_context|NFC/trimmed analysis text → LegalReference/TemporalContext theo span|
|6|src/framework/llm/providers/gemini_adapter.py::__call__|Model/system/user/schema → LiteLLM → Gemini → JSON object text; không retry/fallback|
|7|SemanticAnalysis validation + classify_model_time|Model JSON → facts exact, known temporal/reference roles hoặc lỗi|
|8|supplied_context/reconcile_missing + objective mapping|Supplied spans + missing questions/model issues → MI consistency, bounded queries, issue indices|
|9|search/agent.py::search|QueryPlan + trusted SearchOptions → native RetrievalRequests/Responses và SearchState|
|10|src/application/services/retrieval_service.py::search|Request → BM25/Dense/Hybrid/(configured rerank) → native evidence/outcome|
|11|search/agent.py::_finish|Native responses → source-payload groups + every query occurrence/issue_indices + warnings/completeness|

Các đường dẫn query/... và search/... trong bảng nằm dưới src/applications/tillegal/agents/. Nội dung pháp luật/prompt ở application layer; provider SDK ở framework provider adapter. Shared gateway placeholder vẫn nằm ngoài phạm vi thay đổi.

## 3. Citation không phải thời gian áp dụng

45/2019/QH14 là định danh người dùng cung cấp;2019 ở đây không tự thành thời điểm áp dụng. Điều35, Khoản2, điểm b là reference spans. “Bộ luật Lao động2019” được giữ như tên/tham chiếu văn bản, không tự suy ra số hiệu còn thiếu hoặc ngày hiệu lực.

TemporalContext phân biệt ngày sự kiện, ngày người dùng muốn tra áp dụng, ngày công bố/ban hành, ngày hiệu lực nếu nêu rõ, tham chiếu lịch sử, tương đối, khoảng thời gian, hiện hành và chưa rõ. Chỉ ngày đầy đủ hợp lệ có iso_date; năm đơn lẻ không tạo ngày01/01 hay31/12. Những ngày do người dùng nói chưa được kiểm chứng với nguồn luật bên ngoài.

Ví dụ “hợp đồng ký15/03/2024 theo Luật45/2019/QH14”: reference giữ45/2019/QH14; event_date giữ15/03/2024. Nếu model đưa số hiệu vào temporal_mentions, classify_model_time nhận đúng literal source span và ghi MODEL_REFERENCE_RECLASSIFIED. Nó không xóa đoạn đó khỏi original. Nếu model bịa ngày2027 không có trong câu hỏi thì vẫn lỗi.

Cùng một năm có thể xuất hiện trong tên luật và trong sự kiện: parser xét các lần xuất hiện, không xóa mọi số2019. Câu “năm2010, không phải hiện nay” giữ span hiện nay với negated=true nhưng không dùng nó làm active temporal_scope. Mọi offset là trên bản phân tích NFC/trimmed; original Unicode/whitespace được giữ nguyên. Khi bảo vệ, phải nói rõ hệ tọa độ này.

## 4. Facts không đồng nghĩa sự thật pháp lý đã xác minh

Facts là span được người dùng nói. text và source_quote phải giống hệt và xuất hiện trong analysis text. Q007 bị chặn vì một trường có dấu chấm, trường kia không có; Q037 từng paraphrase số tiền/đến hạn. Guard không tự sửa cách diễn đạt thành một dữ kiện có vẻ đúng.

Người dùng có thể nhắc nhận định của bài viết hoặc một giả thiết. Copy chính xác không chứng minh nhận định đó đúng. Citation.source ghi user_supplied_unverified. Quyền/nghĩa vụ trong issue/query vẫn cần nguồn và đánh giá khác; parser không trở thành Verification Agent.

## 5. Tách vấn đề và giữ bối cảnh

LegalIssue có nhãn issue và search_query. Model được hướng dẫn mỗi mục là nhu cầu độc lập, không tách theo câu hoặc từ khóa. Một issue có thể cần nhiều query, nhiều issue có thể dùng chung query/nguồn. Chỉ tối đa4 query, không mở vòng tìm tự chủ.

SemanticQueryAgent gộp query giống hệt, tạo SearchObjective với query_index và issue_indices, rồi thêm bối cảnh từ exact selected fact spans. Với hợp đồng2 năm, làm6 tháng, hai truy vấn báo trước/bồi thường đều giữ bối cảnh. Context có giới hạn; dữ kiện gắn với citation/nhận định pháp luật không được dùng như scenario facts đã xác nhận.

Q005 mới có hai truy vấn riêng về nuôi con/cấp dưỡng và chia tài sản; Q040 có truy vấn về người vay và bên bảo lãnh. Điều này không tự chứng minh đã phủ hết nhu cầu. Proxy one-to-one keyword có thể đánh giá thấp một tìm kiếm dùng chung; phải xem nhu cầu thực và evidence.

## 6. Đã cho, còn thiếu và blocking clarification

supplied_context chỉ có ba nhóm slot nhỏ đã có bằng chứng lỗi: thời hạn hợp đồng, lý do nghỉ nêu rõ và một số biểu thức thỏa thuận đào tạo. Đây không phải ontology toàn bộ luật.

reconcile_missing bỏ câu hỏi chung về thời hạn khi hợp đồng đã nói2 năm, nhưng giữ câu hỏi ghép về thỏa thuận đặc biệt/đào tạo. Không được xóa cả câu chỉ vì nó có chữ “loại hợp đồng”: có thể nó đang hỏi một điều khoản chưa biết. Với người lao động muốn nghỉ, lý do/đào tạo có thể được bổ sung thành thông tin tùy chọn khi chưa nêu. Không suy ra đã có đào tạo hoặc phải bồi thường.

missing_information là follow-up nhưng vẫn tìm quy định chung; clarification là mơ hồ chặn Search. Không dùng hai trường này thay nhau để nâng acceptance. Regex chỉ hỗ trợ một số cách diễn đạt; kết quả matched vẫn còn bỏ sót missing information ở lĩnh vực khác.

## 7. Search và RetrievalService

Search validate plan/options. Mode/date/top_k/policy do ứng dụng truyền rõ; Gemini không thay filter. Literal historical year không tự đổi as_of_date. Dataset lịch sử dùng ngày mốc nghiên cứu được khai báo, không nói đó là ngày duy nhất hợp pháp.

Search cache exact query trong một request, giữ positional requests/responses và dừng tại lỗi đầu tiên. PARTIAL/FAILED cùng skipped indices diễn tả phần chưa chạy. NO_MATCH không được biến thành chứng cứ đúng. Không có fallback sang backend khác sau lỗi model hoặc retrieval.

RetrievalService qua Supabase read repositories: BM25 dùng tokenizer/index hiện hữu và hydrate chunk/source; Dense dùng E5 local rồi vector RPC; Hybrid dùng RRF của hai nhánh; Rerank nếu được cấu hình dùng cross-encoder local. APPLIED mới xác nhận rerank thực thi. Task này chỉ dùng BM25 cho so sánh relevance để giữ cùng điều kiện và tiết kiệm máy; không sửa bốn thuật toán. Các lần chạy real modes trước đây là bằng chứng lịch sử, không phải đã chạy lại tất cả trong phase mới.

## 8. Grouping, version và rank

_finish gộp theo toàn source payload, chỉ bỏ rank/raw_score/score_kind/retrieval_method trong khóa. Source/chunk/structure/snapshot/hash/ngày/metadata khác không bị gộp tùy tiện. Evidence đại diện giữ rank của lần đầu; không phải global ranking giữa các query.

EvidenceOccurrence giữ query, index, request_id, rank/score và giờ thêm issue_indices từ mapping được validate. Có thể truy từ một nhóm evidence về đúng issue/query/native response. Plan cũ không có mapping được giữ mapping rỗng, không đoán tùy ý. Reranking/fusion metadata vẫn trong response gốc; không cộng điểm BM25 với cosine/RRF.

Nếu user tra đúng document number nhưng source titles chỉ là nghị quyết khác dẫn chiếu, Search ghi EXACT_LOOKUP_SOURCE_IDENTITY_UNCONFIRMED. Đây là metadata check, không kết luận source vô ích hay luật sai. Không bỏ evidence, sửa rank hoặc làm Judge. Warning nằm trong SearchState; graph/handoff ngoài scope không được thiết kế lại.

## 9. Relevance khác legal correctness

Một đoạn đúng hash, có URL và chứa đúng số điều vẫn có thể chỉ dẫn chiếu hoặc nói chủ đề khác. Rubric0–3 đánh giá mức liên quan với câu hỏi/objective, không xác nhận hiệu lực, tính đầy đủ hoặc nội dung hỗ trợ kết luận pháp lý.

Pool có57 dòng từ8 câu, cùng BM25/options giữa biến thể, giữ full text/source identity/native rank. Bộ template chưa có nhãn human/expert.19 nhận xét rank-one riêng do assistant hỗ trợ là provisional, có lý do và bất định; không được gọi expert-reviewed. Phần còn lại chưa được đánh giá. Null không phải relevance0. Không có expert Precision@K/Recall@K/NDCG; đặc biệt Recall cần biết tài liệu liên quan còn chưa được truy xuất.

Ví dụ full-text: hỏi nuôi con sau ly hôn nhưng kết quả là định nghĩa người nuôi liệt sĩ; hỏi hiệu lực hợp đồng nhưng kết quả là danh hiệu Anh hùng. Đây là dấu hiệu lệch chủ đề, không phải chỉ thiếu từ khóa. Tuy vậy không thể kết luận corpus hoàn toàn không có nguồn đúng chỉ từ top3.

## 10. Đánh giá và trả lời trong buổi bảo vệ

Ground truth45 câu không đổi. Mẫu matched15 lịch sử nhận12 plan, lần đầu hiện tại13, sau một retry rate-limit có ghi nhận là14. Q007 primary vẫn fail; một repeat pass chỉ chứng minh biến thiên. Không lấy repeat tốt thay vào primary. Bảng14 dùng denominator đầy đủ, failed plan tính0, không giấu lỗi sau conditional score.

Citation/time và source-role được kiểm tra bằng regressions, raw replay và real Gemini Q025. Decomposition/context/MI có hành vi mục tiêu được kiểm thử, nhưng missing-info proxy còn giảm so với baseline. Relevance overall chưa có kết luận chuyên gia. Câu trả lời đúng khi bảo vệ là “đã sửa những invariant/lỗi có bằng chứng, còn chất lượng tổng thể chưa được chứng minh”, không phải “test pass nên AI hiểu luật đúng”.

## 11. Chạy lại và đọc code

Đọc09→10→11 để hiểu nguyên nhân/thiết kế;12 cho relevance/label integrity;13 cho source changes;14 cho denominators;15 cho lệnh và test count. Xem raw data trong evaluation/query_search/semantic_v2/.

`python -m scripts.validate_query_semantics --mode summarize` tái lập matched postprocessing từ outputs thật đã lưu, không gọi model. `--mode replay` kiểm tra raw artifacts cũ. Live mode dùng ledger chung25 request và từ chối batch vượt phần còn lại trước khi gọi API; không reset tự động. Collector relevance gọi DB chỉ đọc, không gọi Gemini.

Không crawl, rebuild index, migrate, download model, đổi API key, commit/push hoặc thay graph trong task này. Bước tiếp theo là reviewer chuyên môn gán nhãn, kiểm coverage corpus và đánh giá thêm theo ngân sách riêng; không mô tả những bước đó như đã hoàn thành.
