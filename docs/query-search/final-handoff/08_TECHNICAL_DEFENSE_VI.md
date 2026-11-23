# Tài liệu bảo vệ kỹ thuật Query/Search

## 1. Phạm vi và kết luận acceptance

Hai module được chấp nhận ở mức READY WITH LIMITATIONS để bàn giao kỹ thuật. Người khác có thể khởi tạo, gọi, đọc output và tích hợp theo hợp đồng đã ghi. Kết luận không có nghĩa hệ thống trả lời pháp luật hoàn chỉnh hoặc evidence luôn đúng. Đợt cuối chỉ kiểm chứng, không thiết kế lại và không sửa production.

Khi trình bày, nên tách ba câu hỏi: chương trình có chạy đúng hợp đồng không; đoạn trích có liên quan nhu cầu không; quy định đó có đúng và áp dụng được không. Unit tests và schema chủ yếu giúp câu đầu. Chấm relevance giúp câu thứ hai. Xác minh nguồn và hiệu lực cần cho câu thứ ba. Không được lấy kết quả của một câu hỏi thay cho hai câu còn lại.

## 2. Tại sao chọn deterministic kết hợp LLM?

Deterministic cho đầu vào có kiểm soát, tra cứu citation trực tiếp, hành vi offline và lỗi tái lập được. Nhưng quy tắc tách theo dấu câu không đủ hiểu mọi nhu cầu: Q040 có hai quan hệ vay và bảo lãnh; Q005 có nuôi con và chia tài sản. Gemini hỗ trợ phân tích ngữ nghĩa trong các tình huống đó.

LLM không quyết định luật đúng, không tự chọn quyền truy cập corpus, không tự sửa ngày áp dụng. Nó đề xuất SemanticAnalysis; mã deterministic kiểm tra grounding và tạo QueryPlan cuối. Đây là ranh giới tin cậy, không phải mô hình thứ hai đánh giá mô hình thứ nhất. Hệ thống hiện không có autonomous search loop hoặc second-LLM verifier.

## 3. Thứ tự thực thi với file/hàm thật

|Bước|File/hàm|Input|Output|
|---|---|---|---|
|1|src/query_search_bootstrap.py:create_query_search|settings, SearchOptions, semantic_mode|QuerySearch|
|2|QuerySearch.search|question:str|Gọi planner rồi search, trả SearchState|
|3|query/agent.py:understand|Câu hỏi|Plan deterministic/clarification|
|4 tùy chọn|query/semantic.py:SemanticQueryAgent.understand|Câu hỏi + completion|Plan semantic đã kiểm tra hoặc QueryAnalysisError|
|5|query/context.py:parse_context,classify_model_time,reconcile_missing|Văn bản, span, danh sách từ model|Citation/time/consistency metadata|
|6|search/agent.py:search|Plan, service, options|Native requests/responses|
|7|src/application/services/retrieval_service.py:RetrievalService.search|RetrievalRequest|Evidence, warnings, typed error|
|8|search/agent.py:_finish|Plan và các response đã chạy|Aggregate evidence và provenance|

Các đường dẫn query/search rút gọn trong bảng thuộc src/applications/tillegal/agents/. Không có route HTTP mới được tạo. Graph không đổi; chỉ chạy regression để phát hiện ảnh hưởng đến đường tích hợp đã có.

## 4. Đầu vào được kiểm tra thế nào?

understand kiểm tra type, độ dài, ký tự và chuỗi rỗng. Original giữ đúng chuỗi caller, còn phân tích dùng NFC/trimmed. Ngày lịch sai hoặc câu quá mơ hồ có thể cần clarification. Không phải mọi thiếu dữ kiện đều cản tìm quy định chung; missing_information khác clarification.

Domain hiện chỉ labour/unknown. Offline planner có nhánh employee-exit hẹp và một số mở rộng chủ đề lao động. Không nên nói nó đã hiểu đầy đủ mọi luật dân sự, gia đình và người tiêu dùng. Sparse facts trong deterministic không đồng nghĩa làm mất câu hỏi: original vẫn được giữ.

## 5. Gemini được nối qua đâu?

create_query_search với semantic_mode="gemini" gọi query/gemini.py:create_gemini_query_agent. Hàm đọc profile query_semantic ở configs/models.yaml, provider gemini và biến GOOGLE_API_KEY. Model cấu hình hiện tại là gemini-3.5-flash-lite, có thể ghi đè bằng GEMINI_MODEL; deadline bằng QUERY_LLM_TIMEOUT_SECONDS. Factory không tự load hay ghi.env.

GeminiStructuredCompletion ở src/framework/llm/providers/gemini_adapter.py dùng LiteLLM acompletion với prefix gemini/, response schema, timeout, num_retries=0, caching=False và no-log. Cấu hình OpenAI của module khác vẫn tồn tại; nó không làm Query semantic dùng OpenAI. Tên model là cấu hình được xác nhận bằng source và artifact lịch sử, không phải lời khẳng định remote model hiện đang sẵn sàng vì acceptance này không gọi provider mới.

Có thể inject SemanticQueryAgent qua query_agent để replay/mock. Không truyền đồng thời query_agent và semantic_mode="gemini", vì factory sẽ báo xung đột. Đây là cách test dependency injection mà không giả lập sai thuật toán planner.

## 6. Structured output được kiểm tra ra sao?

SemanticAnalysis có intent/domain/facts/issues/missing_information/temporal_mentions/clarification. SemanticModel dùng extra=forbid; facts phải có text giống source_quote. Agent còn yêu cầu quote xuất hiện nguyên văn trong câu hỏi NFC. Nó chặn citation hoặc số mới trong issue/query/missing/clarification, kiểm tra thời gian có căn cứ và giới hạn kích thước phản hồi.

Pydantic chỉ là một lớp. Fact có trong câu người dùng có thể vẫn là lời người khác nói sai. Ví dụ Q025 trích lời bài viết “cho nghỉ ngay mọi trường hợp”: trích đúng câu không có nghĩa xác nhận quy định đó đúng. Các thành phần sau phải xem đây là allegation cần kiểm chứng.

Q007 response chính bị từ chối vì source-quote/dấu câu không khớp. Không có fallback im lặng sang deterministic để lượt Gemini trông thành công. Timeout và provider error có mã riêng; cancellation vẫn truyền lên. Không cố gây lỗi thật hoặc gọi lại provider chỉ để có một kết quả thuận lợi.

## 7. Citation không phải temporal applicability

parse_context tách LegalReference như45/2019/QH14, Điều35, khoản/điểm và một số tên luật kèm năm. source=user_supplied_unverified nhắc rằng đây là literal người dùng nêu. Số2019 trong số hiệu không được biến thành ngày áp dụng2019.

TemporalContext ghi text/start/end/role/iso_date/negated. Role là nhận diện theo cue: ngày sự kiện, áp dụng, ban hành, hiệu lực, lịch sử, duration hoặc mốc tương đối. Q019 nói không phải hiện nay: negated được giữ trong span, nhưng không trở thành active temporal_scope. Offsets áp dụng bản NFC/trimmed, không phải byte offset của raw input.

SearchOptions.as_of_date do caller đáng tin cậy cung cấp. Ví dụ ngày2010-12-31 trong thí nghiệm Q019 là anchor nghiên cứu, không phải agent khẳng định giao dịch diễn ra đúng ngày đó. Unknown effective dates vẫn phải được báo là chưa rõ.

## 8. Issues, missing information và subqueries

Issue là nhu cầu thông tin, không phải phán quyết. Model trả issue và search_query; planner deduplicate chuỗi query giống nhau, tạo search_objectives với chỉ số query và issue. Một query có thể phục vụ nhiều issue; các issue liên quan có thể dùng chung nguồn.

Planner gắn một phần bối cảnh đã grounding vào query. Việc đó giữ tình huống, nhưng query dài có thể thêm token làm lệch BM25. Thí nghiệm cũ Q004: query C187/185 ký tự, D62/52; dẫn chiếu chuyển từ rank5 lên1 ở query báo trước nhưng vẫn không phải chính văn cần tra. Không có bằng chứng để bỏ facts trên toàn hệ thống.

reconcile_missing chỉ xử lý một số slot như thời hạn, lý do nghỉ, thỏa thuận đào tạo. Nó không kiểm tra đầy đủ mọi điều kiện pháp lý. Điểm missing-info proxy lịch sử7/12 so với8/12 trước đó còn là giới hạn. Acceptance giữ nguyên thay vì viết lại prompt không có bằng chứng mới.

## 9. Public contracts có điểm gì dễ nhầm?

QueryPlan có6 field bắt buộc: original,intent,domain,temporal_scope,subqueries,clarification; các metadata khác có default để đọc legacy plans. clarification có thể null nhưng key vẫn bắt buộc. UnifiedEvidence có nhiều field nullable nhưng vẫn required. “Optional về giá trị” không đồng nghĩa “có thể bỏ key”.

SearchOptions có4 field bắt buộc và strict: mode, top_k, as_of_date, allowed_usage_policies. Nó cấm extra fields. QueryPlan dùng BaseModel mặc định extra-ignore, không phải mọi field đều strict. SearchState là TypedDict/plain dict, chứa tuple và Pydantic model; muốn JSON dùng TypeAdapter(SearchState) với serialize_as_any=True để giữ fusion/reranking, không gọi state.model_dump(). Khi đọc JSON mở rộng phải khôi phục subtype trước, như helper ở05. Probe hiện tại xác nhận mặc định serializer làm mất metadata mở rộng, dù Python SearchState vẫn giữ subtype.

Probe mới của acceptance: plan tự dựng có citation kết thúc ở suffix, truyền end145 thay vì45 vẫn có thể qua phép kiểm tra slice. Parser chuẩn sinh end45, không gặp lỗi này. Vì vậy parse được QueryPlan không có nghĩa một plan bên ngoài đã qua toàn bộ grounding. Đây là giới hạn boundary không blocking đường chuẩn; đã ghi cụ thể thay vì sửa production ngoài phạm vi acceptance.

## 10. Search làm gì và không làm gì?

Search nhận plan/options, tạo RetrievalRequest cho từng subquery rồi gọi RetrievalService tuần tự. Nó cache đúng chuỗi query trong cùng lượt, giữ response subtype và fail-fast khi gặp FAILED. Nó không tự đổi backend, không cộng điểm giữa các query, không kết luận relevance.

timeout_seconds của create_query_search mặc định30 là budget RetrievalService; Search có timeout per-query45 riêng, không phải global request timeout. Một request nhiều subquery có thể dài hơn45 giây. Caller có thể đặt deadline ngoài bằng asyncio.timeout. Local cold model loading còn ảnh hưởng thời gian.

## 11. Retrieval đóng góp gì?

BM25 dùng token Unicode và index đảo; nó phù hợp lexical overlap nhưng không bắt buộc đúng cụm điều luật/identity nguồn. Dense dùng E5 query: với vector384 chiều để tìm tương đồng, không xác minh quan hệ pháp lý. Hybrid chạy hai nhánh và cộng Reciprocal Rank Fusion1/(k+rank), không cộng trực tiếp BM25 với cosine. Reranker chấm cặp query/passage trong pool có sẵn.

Files thật: integrations/database/repositories/sparse_retrieval_repository.py, supabase_vector_repository.py; integrations/embeddings/e5_query_encoder.py và cross_encoder_reranker.py; application/services/hybrid_retrieval.py và reranking.py; applications/tillegal/retrieval/rank_fusion.py và reranker.py. Các module này không đổi trong acceptance.

Hybrid+rerank vẫn dùng mode="hybrid" với RerankConfig(enabled=True), không có enum mode="rerank". Reranker không tìm toàn bộ corpus và không thể đưa vào chunk chưa có trong pool. Operational fallback phải có trạng thái/cảnh báo, khác với fallback im lặng của Query vốn không tồn tại.

## 12. Aggregation và provenance

_finish gộp payload nguồn giống hệt, bỏ các field phụ thuộc query như rank/score/method khỏi khóa. Source/structure/snapshot/content/hash/dates/metadata vẫn nằm trong khóa. Cùng ID nhưng payload khác cảnh báo conflict; phiên bản khác không bị hòa làm một.

Occurrence giữ query, response_index, request_id, native rank/raw_score/score_kind và issue_indices. Aggregate chỉ có representative payload của lần xuất hiện đầu, không có global rank. Nếu consumer sort representative raw_score giữa các query hoặc sort rerank bằng retained RRF raw_score, consumer sẽ hiểu sai output.

Legacy plan không có search_objectives thì occurrence.issue_indices rỗng. Không đoán rằng mọi evidence hỗ trợ mọi issue. Liên kết có mặt chỉ chứng minh provenance, không phải semantic support. Audit cũ57 occurrence đều được giữ; acceptance hiện kiểm tra fixture và regression, không gọi corpus mới.

## 13. Failures và completeness

CLARIFICATION_REQUIRED/NOT_STARTED: không đọc DB. COMPLETED/COMPLETE: thực thi hết, có thể không có kết quả. FAILED/PARTIAL: trước lỗi đã có response không failed, có thể chỉ là NO_MATCH; không đảm bảo luôn có evidence. FAILED/FAILED: chưa có phần thực thi hữu dụng trước lỗi. skipped_subqueries ghi chỉ số query chưa chạy.

Search bắt lỗi timeout/classified RetrievalServiceError; lỗi lập trình bất ngờ và cancellation truyền lên. warnings trong SearchState là code; warning chi tiết có message/chunk ID nằm trong response. Không được nuốt lỗi rồi tạo câu trả lời như đầy đủ chứng cứ.

## 14. Dẫn chiếu không xác nhận đúng nguồn

Q022 yêu cầu Điều35 Bộ luật Lao động45/2019/QH14. Chunk2973a693-2276-4e4f-a233-f7038e4717e0 trong Nghị quyết25/2026/NQ-HĐND có nhắc khoản2 Điều35, nhưng vị trí thật là Điều5 Khoản2 Điểmb của nghị quyết. Cả4 mode trong thí nghiệm lịch sử xếp nó đầu; điều đó không biến chunk thành chính văn Bộ luật.

EXACT_LOOKUP_SOURCE_IDENTITY_UNCONFIRMED là kiểm tra literal số hiệu trong tiêu đề nguồn cho quote_lookup khi có evidence. Nó không xác thực authoritative identity/article, không áp dụng chắc chắn cho legal_question Q025 và không lọc nguồn. Không có warning không đồng nghĩa nguồn đã đúng.

## 15. Temporal uncertainty và corpus

Inventory lịch sử có58 source nhìn thấy/2609 chunks, thiếu stored document_number45/2019/QH14; literal trong chunk chỉ thấy dẫn chiếu. Đây là scope đã kiểm tra, không chứng minh mọi nguồn bên ngoài vắng mặt. Các truy vấn literal0 match cũng không chứng minh semantic absence với mọi cách diễn đạt.

Q019 anchor2010 nhận nguồn issued2026-08-05 có effective_from/to null. Later consolidation có thể mô tả quy tắc cũ; không tự loại chỉ vì năm xuất bản. Nhưng null dates cũng không chứng minh áp dụng năm2010. Cần metadata và xác minh riêng, không sửa datefilter hoặc corpus trong acceptance.

## 16. Kiểm thử hiện tại và nguồn gốc bằng chứng

Đợt này rerun578 focused và667 full tests, Ruff check/format17 file đều pass.5 state kiểm soát gồm deterministic, saved raw semantic replay, no-match, partial/skipped và citation uncertainty;4 lỗi gồm invalid input/structured output/provider timeout/provider error. Hoàn toàn0 new Gemini và0 new Supabase call.

tests/contract hiện chỉ là placeholder; executable contract coverage nằm ở retrieval/test_contracts.py và tests Query/Search/graph. Test tên “real_retrieval” vẫn có thể là real service với fake ports; không gọi đó là live Supabase. Artifact raw Gemini và28 Search calls thật là bằng chứng lịch sử được liên kết riêng. Replay trả raw cũ qua code hiện tại, không phải phản hồi provider mới.

## 17. Câu hỏi bảo vệ và gợi ý trả lời

**Tại sao không cho LLM tự gọi Search lặp đến khi đủ?** Kiến trúc hiện có một planner bounded và Search có hợp đồng rõ. Chưa có bằng chứng cần vòng lặp; nó thêm chi phí và làm mờ failure semantics. Acceptance không thêm khả năng chưa triển khai.

**JSON hợp lệ có nghĩa nội dung đúng không?** Không. Schema kiểm tra cấu trúc và một số invariant. Grounding kiểm tra quote/số/citation/thời gian, nhưng không chứng minh completeness hay pháp lý. QueryPlan manual probe cho thấy không nên coi schema là toàn bộ trust boundary.

**Tại sao Gemini không chạy khi tra citation?** Deterministic exact path đã có đủ mục tiêu, giữ literal và tránh thêm suy diễn. semantic_mode gemini không bắt buộc mọi câu đều gọi provider.

**COMPLETE mà evidence rỗng có mâu thuẫn không?** Không. COMPLETE là đủ lượt thực thi; NO_MATCH là kết quả tìm kiếm. Hai khái niệm độc lập với đủ căn cứ trả lời.

**Tại sao không so điểm BM25 với cosine?** Thang đo khác. RRF dùng thứ hạng để kết hợp; occurrence giữ score_kind để tránh diễn giải sai.

**Tại sao rank đầu vẫn sai chủ đề dù reranker APPLIED?** APPLIED chỉ nói mô hình chấm thành công trên candidate pool. Pool có thể thiếu nguồn cần thiết; ranking không phải xác minh luật. Q022 là ví dụ cụ thể.

**Có thể khẳng định corpus không có Bộ luật không?** Chỉ có thể nói metadata đầy đủ trong scope credentials được kiểm tra không có stored number đó, và literal probe có một dẫn chiếu. Không khẳng định mọi corpus hoặc mọi identity/paraphrase đều không có.

**667 pass có đủ kết luận ready không?** Đủ hỗ trợ acceptance kỹ thuật cùng source audit/fixture path, chưa đủ legal/relevance acceptance. Verdict phải có phạm vi và limitations.

**Ai chịu trách nhiệm phần còn lại?** Query/Search giữ giới hạn grounding/slot/domain/manual-plan boundary; corpus owner chịu metadata/coverage đã chứng minh; Retrieval owner đánh giá ranking với relevant ground truth; future consumer xử lý partial/evidence verification. Không gán lỗi thuật toán khi chưa có bằng chứng.

**Tại sao không sửa end offset ngay?** Nó là giới hạn manual-plan ingestion được kiểm chứng, không xuất hiện ở parser chuẩn và chưa blocking đường dùng được bàn giao. User chỉ cho sửa production khi blocking; acceptance ghi rõ để tích hợp đúng ranh giới, không mở vòng tối ưu mới.

## 18. Cách tái lập an toàn

Từ project root, chạy scripts.verify_query_search_handoff với output mới. Xem05 để chạy fixture tự chứa và khởi tạo thật; xem06 cho exact pytest/Ruff commands. Không overwrite raw/human annotations, không in key/headers, không cài model hoặc ghi DB. Phiên bản code hiện không có Git metadata; dùng source manifests để so scope, không bịa branch/HEAD.
