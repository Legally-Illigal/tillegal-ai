# Changelog và giới hạn

Thay đúng hai stub src/applications/tillegal/agents/{query,search}/agent.py. Source Query lấy nguyên implementation đã harden từ development checkout. Thêm src/query_search_bootstrap.py và hai test tests/unit/applications/tillegal/test_query_hardening.py, test_query_search.py. Guard trước ghi kiểm agent còn đúng docstring stub; file mới phải chưa tồn tại. Không copy directory, không merge Git, không sửa retrieval/dependency/database/graph/Judge/Response.

Documents mới ở .docs/agent-development/task-03-query-search-retrieval. Source target ngoài writable roots nên write/test đi qua approval escalation. Target không có Git metadata, không thể cung cấp branch/HEAD/diff hoặc chứng minh toàn working tree clean. Development checkpoint b2be67e và existing dirty files được giữ nguyên. Staging scripts/files.json trong .tmp/task3-integration của workspace chỉ phục vụ write-set hữu hạn.

Chưa có HTTP hoặc LangGraph workflow nối QuerySearch ở target, vì graph target còn stub và scope dừng tại Query/Search/Retrieval. Caller có thể dùng create_query_search(settings, options) rồi await pipeline.search(question). Kết quả là SearchState native response, không tương thích trực tiếp legacy Judge dùng EvidenceBundle; không nối nhầm consumer cũ.

Options do caller tin cậy cấp. Nếu user nêu thời điểm khác options, QueryPlan vẫn giữ temporal mentions nhưng chưa có resolver reconciliation. COMPLETED với toàn NO_MATCH vẫn không có căn cứ pháp lý. Failure sau một số calls giữ lịch sử đã nhận; không tự publish evidence partial như legal answer.

PROPOSED Task tiếp theo duy nhất: chạy read-only Dense qua QuerySearch với model directory local được xác minh và chính options explicit, so response contract/hash/identity; tiếp đó mới đánh giá Hybrid/rerank theo task riêng. Không tự chọn/download model.
