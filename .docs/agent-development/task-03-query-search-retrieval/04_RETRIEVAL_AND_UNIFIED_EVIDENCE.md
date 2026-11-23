# RetrievalService và UnifiedEvidence

Service mới sẵn interface text nên không cần legacy LegalRetrieval adapter hoặc EvidenceBuilder. `create_retrieval_service` compose SparseRetrievalRepository, ChunkRepository, SourceDocumentRepository, SparseIndexRepository, tokenizer. Dense opt-in inject E5QueryEncoder (384), vector repository và dense index reader. Hybrid/RRF và reranking thực thi tại service/helpers. Search truyền options, không tự chọn hay triển khai algorithm.

| Nhóm UnifiedEvidence fields | Ý nghĩa và xử lý |
|---|---|
| retrieval_chunk_id, source_document_id, document_structure_id, chunk_key | UUID/key nguồn lưu trữ; giữ chính xác; không bịa document_version_id legacy |
| content, content_sha256 | Stored retrieval chunk text và hash; content có thể gồm breadcrumb, không gọi verified raw quote |
| hash_check, content_representation | MATCHED_STORED/PAYLOAD_ONLY; representation retrieval_chunk_content; giữ nguyên mức bằng chứng |
| rank, raw_score, score_kind, retrieval_method | Rank và BM25/COSINE_SIMILARITY/RRF; không cộng score xuyên query; rerank metadata riêng |
| node_id, block_id, chunk_type | Cấu trúc gốc theo dữ liệu; null giữ null |
| start_offset, end_offset, chunk_metadata | Locator/metadata lưu trữ, không tự tạo normalized/source locator legacy hoặc suy offset unit |
| source_id, source_record_id, source_snapshot_id | Provenance theo source; unknown giữ None |
| title, source_url, language | Metadata nguồn; URL thiếu vẫn thiếu và warning service giữ |
| issued_on, effective_from, effective_to, effect_status_reported | Ngày và status nguồn báo cáo; không nâng thành legal validity |
| usage_policy, source_metadata | Policy/metadata nguyên vẹn, không tự thêm approval |

Không map sang EvidenceBundle. Legacy bundle yêu cầu quote, quote_sha256, ancestry, groups/context omissions, exact_citation_verified và hai locator với semantics khác. Những thông tin này có thể không tồn tại trong UnifiedEvidence; tạo giá trị giả sẽ làm sai provenance. Consumer tương lai phải dùng UnifiedEvidence hoặc thiết kế mapping được duyệt với unknown rõ ràng.

Responses giữ nguyên warnings, error category/code/stage/retryable, index identity, consistency và subclass fusion/reranking. SearchState chỉ phản ánh orchestration. Không đánh dấu evidence legally verified. BEST_EFFORT và metadata index không phải immutable DB snapshot.

Target vector schema/DTO hiện 384 chiều theo E5. Nhận định 1536 ở Task 0/2 thuộc checkout development cũ; đã đính chính. Task 3 không sửa schema, embedding hoặc migration.
