# Hybrid và RRF

Request mode hybrid, không có query expansion mới. HybridConfig thực tế mặc định rrf_k=60, bm25_candidates=20,dense_candidates=20, mỗi nhánh1–50. Final user top_k độc lập. Execution SEQUENTIAL, failure_policy STRICT.

Service dựng branch request giữ query/date/policy, thay mode và candidate top_k. Chạy BM25 trước rồi Dense; một lỗi ở BM25 thì không chạy Dense. Dense lỗi không trả partial BM25 như kết quả Hybrid thành công. NO_MATCH ở một nhánh vẫn hợp lệ nếu không error; nhánh kia có evidence vẫn có thể tạo OK. Hai nhánh rỗng → NO_MATCH.

RRF score cho chunk c là tổng `1/(60 + rank_backend(c))` trên các nhánh có chunk đó. Raw BM25/cosine không dùng làm trọng số, nhưng được lưu RankContribution. Dedup theo retrieval_chunk_id UUID, mỗi backend chỉ một vote. Same ID phải khớp toàn nội dung/provenance ngoài rank/score/method. Hash content phải MATCHED_STORED và SHA256 đúng; conflict tạo typed integrity failure. Sort theo (-RRFscore, canonical UUID string), giữ top_k và đánh lại rank liên tục. Code `reciprocal_rank_fusion` không gọi DB/model.

Hybrid validate branch context: cùng query, mode/top_k/date/policy, query_used và selected index; index READY. Pre/post trong từng branch và closing reads sau cả hai detect observed metadata change, chưa tạo transaction snapshot. BranchObservation và FusionMetadata giữ requested/returned candidates, per-branch errors/index và contributions. Warnings chỉ giữ warning thuộc final IDs hoặc không gắn chunk; dedup warning bằng equality.

Timeout chung30s bao cả hai branch/closing/fusion; branch có deadline riêng cũng30s nhưng shared outer deadline ngăn tổng60s. Timeout → HYBRID_TIMEOUT, không fallback silently; cancellation không cưỡng chế dừng native thread ngay.

Offline tests xác minh candidate limits khác nhau, conflicts/duplicates, branch errors, timeout và no-match. New QuerySearch tests assert response subtype và object identity, metadata parity với direct service, cả hai branches được gọi. Live Hybrid OK sau20.964112s, trả5 final evidence, mỗi branch request20/return20, RRF mặc định60. Không inference reranker ở mode này. Khác top5 BM25/Dense là bình thường; chưa có human gold để đánh giá ranking nào tốt hơn.
