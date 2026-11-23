# Hướng dẫn thuyết trình và vấn đáp

Bắt đầu bằng câu hỏi live Trích dẫn: hợp đồng dân sự. Cho xem plan chung, request mode khác nhau và response native. Trình bày BM25 keyword ranking, E5 query vector384, Hybrid rank fusion và Cross-Encoder reordering. Sau đó cho xem Dense timeout đầu và repeat thành công để giải thích vì sao sample latency không phải benchmark ổn định.

Đọc theo thứ tự 01 kiến trúc → 02 contracts → 03 source trace → 04/05/06 algorithms → 07 matrix → 08 evidence. Không trình bày test kỹ thuật thành chứng minh hiệu lực pháp lý.

1. **Vì sao có Query Agent?** Nó chuẩn hóa/kiểm input và tổ chức câu hỏi thành plan để Search có câu truy vấn có cấu trúc; không cần DB để chạy rules.

2. **QueryPlan có gì?** Sáu trường original, intent, domain, temporal_scope, subqueries, clarification. Hàm tạo model Pydantic rồi trả dict.

3. **Original khác query text thế nào?** Original giữ đối số; subquery có thể bỏ prefix lookup/dấu câu và dùng NFC. Test giữ nguyên ý định theo rules, chưa semantic guarantee.

4. **Vì sao tách Search?** Search sở hữu orchestration requests, trusted context và response propagation; các thuật toán retrieval nằm ở service.

5. **Search dùng domain để phân quyền không?** Không. Policy/date/mode/top_k do caller tin cậy cấp; schema validation không tự cấp quyền.

6. **Clarification có gọi model hoặc RPC không?** QuerySearch gọi Query trước Search; khi clarification, Search trả tuples rỗng. Test trên4 profiles xác minh zero service calls.

7. **Ngày31/02 xử lý sao?** Calendar check tạo clarification; không reinterpret thành ngày hợp lệ, không gửi retrieval request.

8. **Ai chọn ngày tra cứu?** Runtime as_of_date explicit. Temporal mentions trong QueryPlan không tự ghi đè ngày hoặc policy.

9. **BM25 chạy ở đâu?** Service tokenize rồi gọi Supabase sparse RPC, hydrate chunks/sources và kiểm index. Search không viết lại scoring.

10. **BM25 so với direct call thế nào?** Cùng request, whole response khớp khi bỏ UUID request và timestamp; cùng observed index nhưng không có transaction snapshot.

11. **E5 model nào?** intfloat/multilingual-e5-small,local snapshot revision614241f622f53c4eeff9890bdc4f31cfecc418b3,dimension384.

12. **Query prefix để làm gì?** Encoder thêm query: theo indexing contract query/passages; prompt rỗng ở encode tránh thêm default prompt lần nữa.

13. **Tokenizer có bỏ dấu không?** E5 giữ case/dấu; Query NFC. Sparse tokenizer lowercase nhưng giữ dấu/số, tách theo regex Unicode.

14. **Pooling là gì ở đây?** Checkpoint config dùng mean token pooling với mask; module tính tổng token weighted/masked chia tổng mask, không CLS pooling.

15. **L2 normalization ở đâu?** Normalize module local và encode(normalize_embeddings=True); service kiểm norm gần1 và dimension384 trước vector RPC.

16. **Có dùng1536 không?** Current model/index/query DTO là384; SQL mới hỗ trợ variable dimensions với nhánh384. Không dùng contract cũ để suy model hiện tại.

17. **Vector Supabase nhận dạng gì?** Repository serialize float tuple thành chuỗi vector .9g, gửi search_legal_chunks cùng index/top_k/date/policies.

18. **Index ready được xác minh gì?** Source kiểm READY,model/dimension/cosine/prefix/normalized; live metadata đọc thấy cùng contract và postflight kiểm thay đổi quan sát được.

19. **Dense có thành công mọi lần không?** Không. First attempt timeout encoding30s; repeat16.22s thành công. Hai kết quả đều lưu, chưa phân rã startup causes.

20. **Hybrid gọi branch đồng thời không?** Code hiện SEQUENTIAL: BM25 rồi Dense dưới shared30s deadline; không mặc định parallel.

21. **RRF công thức gì?** Tổng1/(k+rank) theo backend có chunk, mặc định k60; không cộng raw BM25/cosine scores.

22. **RRF dedup thế nào?** Chunk UUID; duplicates trong backend hoặc same-ID content/provenance conflict là error, không extra vote.

23. **Hybrid nhánh lỗi thì sao?** STRICT failure, final evidence/ranking rỗng và typed error. NO_MATCH không error được xử lý khác branch failure.

24. **Candidate20/20 nghĩa là gì?** Mỗi backend lấy tối đa20 candidate theo config; fusion giữ final top_k5 trong probe, không bắt hai con số bằng nhau.

25. **Reranking là mode mới?** Không. Request vẫn hybrid, config.enabled bật stage. SearchOptions mode rerank bị từ chối.

26. **Reranker model nào?** cross-encoder/mmarco-mMiniLMv2-L12-H384-v1,revision1427fd652930e4ba29e8149678df786c240d8825,CPU classifier một logit.

27. **Cặp input rerank là gì?** Query.strip ghép từng stored content passage; batch4,max_length512,truncation only_second; không cắt content lưu trong evidence.

28. **Điểm rerank âm có lỗi không?** Không. Raw logit không sigmoid có thể âm, không phải xác suất hay legal confidence.

29. **Raw_score sau rerank còn là gì?** Vẫn RRF score, cross_encoder_score ở metadata riêng. Consumer dùng order/rank cuối, không sort raw_score lại.

30. **Model rerank thiếu có bị che không?** Fallback RRF với reranking.status=FALLBACK/failure_code/warning. Live Task4 đã APPLIED; missing model chỉ được test offline.

31. **Giữ UnifiedEvidence bằng cách nào?** Search append chính response object, không projection qua schema legacy; tests identity/parity kiểm mọi fields/subclasses.

32. **Có giả citation/source không?** Unknown metadata giữ None; stored chunk content không nâng thành verified raw quote. Task chưa có citation verifier.

33. **Warning temporal nghĩa là gì?** Metadata thời gian nguồn thiếu; vẫn phải hiển thị hạn chế, không coi score cao là đã xác minh hiệu lực.

34. **275 tests là live không?** Đó là offline fake ports/components. Live probes riêng có Supabase/model thật và logs JSON/status/runtime riêng.

35. **Có thể so top5 giữa modes không?** Có thể quan sát, không đòi cùng chunk hoặc cùng score. BM25/Dense lần này shared0; không kết luận mode nào tốt hơn khi chưa gold.

36. **Timeout có dừng native inference ngay không?** Không bảo đảm. Coroutine timeout trả response; threading lock giữ tới worker xong. Process watchdog chỉ là giới hạn test cleanup.

37. **Đã có Judge chưa?** Task chỉ xác minh retrieval. Judge tương lai đánh giá sufficiency/applicability/gaps, khác trạng thái COMPLETED và ranking score.

38. **Sẵn sàng LangGraph chưa?** Có prototype boundary và test evidence cho Task5; cần giữ trusted options/subclasses/deadline/fallback, chưa production readiness.
