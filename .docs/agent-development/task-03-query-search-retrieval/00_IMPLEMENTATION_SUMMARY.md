# Kết quả Task 3

IMPLEMENTED — Query/Search tích hợp trực tiếp RetrievalService trong đúng source `D:/DOWNLOAD/tillegal-ai/tillegal-ai-main`.

VERIFIED offline — 185 passed, 2.62s, không fail/skip. Gồm test Query hardening, Query/Search với real service + fake read ports và regression RetrievalService sparse/dense/hybrid/reranking.

VERIFIED real Supabase — một query BM25 read-only qua QuerySearch trả COMPLETED, một response OK, 5 UnifiedEvidence và 5 warning TEMPORAL_METADATA_INCOMPLETE. Không suy legal correctness từ kết quả này. Dense/Hybrid/reranking live NOT TESTED.

Không dùng ai_core trong integration mới. Query chuyển riêng một file đã harden từ checkout development; Search tại đích được hoàn thiện từ stub vì contract UnifiedEvidence khác legacy EvidenceBundle. Không copy thư mục hoặc sửa Retrieval algorithms. State mới giữ response objects nguyên vẹn.

Các lựa chọn Task 3: typed SearchOptions bắt buộc do application cấp; tuần tự tối đa 4 queries theo QueryPlan; dừng ở FAILED và giữ các response đã nhận; NO_MATCH vẫn là response hợp lệ. COMPLETED chỉ nghĩa đã xử lý mọi subquery, không nghĩa đã có đủ evidence hay đủ căn cứ pháp lý.
