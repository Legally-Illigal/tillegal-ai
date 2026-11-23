# Thuyết trình và vấn đáp

Luồng đã triển khai đi từ câu hỏi đến native RetrievalResponse và dừng ở SearchState. Query tổ chức ý định, Search orchestration, RetrievalService xử lý thuật toán và DB. Có một probe BM25 Supabase thực, phần model backends mới kiểm offline.

1. **Checkout nào là đích?** D:/DOWNLOAD/tillegal-ai/tillegal-ai-main chứa RetrievalService mới; checkout development cung cấp Query đã harden.

2. **Tại sao cần Search?** Để chuyển plan thành các request có runtime context rõ ràng, giữ lịch sử response và dừng có kiểm soát.

3. **Tại sao gọi service thay vì Supabase?** Service sở hữu readiness, tokenizer, embedding compatibility, hydration, deadlines và classified errors; gọi DB trực tiếp sẽ nhân đôi logic.

4. **Input Query là gì?** Một str, không client/credential. Original giữ đối số chính xác, nội bộ phân tích NFC.

5. **QueryPlan gồm gì?** original, intent, domain, temporal_scope, subqueries và clarification; output vẫn dict sáu trường.

6. **Request.query từ đâu?** Subquery.text đã phân tích, theo thứ tự plan, không sửa lại query ở Search.

7. **Ai cấp mode và top_k?** Trusted SearchOptions, không lấy từ domain hoặc suy từ câu hỏi.

8. **Ai cấp ngày?** Caller application phải truyền as_of_date; không mặc định today và không suy permission từ temporal text.

9. **Ai cấp policy?** Caller đã kiểm quyền; schema chỉ validate list hợp lệ, không phải authorization engine.

10. **Clarification có đọc DB không?** Search trả CLARIFICATION_REQUIRED với requests/responses rỗng trước gọi service.

11. **Ngày sai xử lý thế nào?** Query bỏ mention sai khỏi scope và yêu cầu làm rõ; không tự chuyển 31/02 thành ngày khác.

12. **Vì sao không EvidenceBundle?** UnifiedEvidence là stored chunk với schema khác, có thể thiếu ancestry/raw locator/omissions; mapping giả sẽ đổi ý nghĩa.

13. **Content có phải quote nguyên văn nguồn không?** Representation là retrieval_chunk_content, có thể chứa breadcrumb; chỉ hash stored/payload được service báo.

14. **Có dedup xuyên subqueries không?** Không. Giữ per-query responses để bảo toàn ranking/date/index và cảnh báo.

15. **FAILED có thành NO_MATCH không?** Không. Response FAILED được giữ và Search dừng; NO_MATCH là response hợp lệ không evidence.

16. **Failure ở query sau thì sao?** State FAILED giữ mọi response nhận trước đó cùng request đã gọi; chưa tạo legal answer.

17. **COMPLETED có nghĩa đúng luật không?** Chỉ đã xử lý hết subqueries, không đánh giá legal sufficiency hoặc correctness.

18. **Hash check có ý nghĩa gì?** MATCHED_STORED xác minh với hash lưu, PAYLOAD_ONLY có giới hạn khác; giữ nguyên status thay vì gọi verified citation.

19. **Ranking score có cộng với nhau không?** Search không cộng score. Service dùng BM25/cosine/RRF/rerank metadata theo contract.

20. **Dense dimension bao nhiêu?** Target mới 384 theo E5; 1536 là DTO của checkout cũ, không dùng để mô tả target.

21. **Có fallback về ai_core không?** Integration mới không import ai_core; service hiện hữu chịu failure policy, Search không thêm fallback.

22. **Bootstrap làm gì?** create_query_search gọi create_retrieval_service hiện có, chuyển dense path/hybrid/rerank config và timeout.

23. **Có tự tải model không?** Không; Dense/rerank cần đường dẫn local explicit, task live chỉ chạy BM25.

24. **State có serialize được không?** Nó giữ native models/UUID/date; JSON boundary tương lai phải dùng model_dump(mode=json) theo từng subclass để giữ fields.

25. **Có graph/HTTP ở target chưa?** Task cung cấp async application entrypoint; không xây graph/HTTP mới hoặc ghép legacy Judge.

26. **185 tests có phải live E2E?** Đó là offline service/port fixtures. Bằng chứng live là một BM25 QuerySearch request riêng trả 5 evidence.

27. **Cảnh báo live là gì?** TEMPORAL_METADATA_INCOMPLETE, giữ nguyên để caller biết dữ liệu thời gian chưa đầy đủ.

28. **Git version của target?** Source export không có .git, nên ghi SHA256 các source; không bịa branch main từ tên folder.

29. **Điểm chưa xác minh?** Live Dense/Hybrid/rerank, concurrency/load, temporal reconciliation với caller và consumer legal answer.

30. **Bước tiếp theo?** Xác minh model local và chạy Dense read-only qua entrypoint mới với explicit options.
