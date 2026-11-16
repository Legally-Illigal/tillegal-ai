# Retrieval — sổ tay đọc source và vấn đáp

Đọc theo thứ tự:

1. BM25: query → postings → điểm → evidence (historical/local reference; not included in this Task 8 publication).
2. Dense E5: query → tensor → vector search → evidence (historical/local reference; not included in this Task 8 publication).
3. Hybrid RRF: hai nhánh → hợp nhất thứ hạng → response (historical/local reference; not included in this Task 8 publication).
4. [Cross-Encoder reranking: Hybrid pool → pair scoring → final evidence](04_RERANKING_TECHNICAL_WALKTHROUGH.md).

Chương04 bổ sung implementation và actual local/Supabase technical E2E ngày16/11/2026. Các ghi chú snapshot/giới hạn ở ba chương01–03 dưới đây giữ nguyên theo phiên viết lịch sử; xem chương04 cho optional reranking và source ranges mới. Chưa có quality evaluation với human judgments.

## Cách dùng và giới hạn bằng chứng

Đối chiếu source ngày 15/11/2026, chỉ trong `tillegal-ai-main/`. Mọi đường dẫn source và số dòng trong ba báo cáo tính từ thư mục này; số dòng là 1-based tại thời điểm viết. `ai_core/` và `retrieval-publish/` không phải bằng chứng implementation hiện tại.

Mỗi báo cáo độc lập, có giải thích cơ chế, ví dụ tính tay, trace caller/callee và câu hỏi vấn đáp. Học cơ chế trước, dùng bảng source trace cuối báo cáo để mở đúng đoạn code sau. Các ví dụ dữ liệu đều ghi **ILLUSTRATIVE**: không phải kết quả query thật và không phải kết luận pháp lý.

Không đọc credentials, không kết nối database, không chạy crawler, migration, indexing hay tải model. Vì vậy tên bảng, RPC, index và các bộ lọc được xác nhận từ source/migrations; chưa xác nhận trạng thái schema triển khai, số record, READY hay execution plan thực tế trên Supabase. Model config công bố được kiểm tra từ nguồn chính thức của checkpoint; bản model local chưa được quan sát. Không có benchmark trong bộ tài liệu này.

## Ranh giới công việc cần nói đúng khi bảo vệ

| Phạm vi | Cách mô tả có căn cứ |
|---|---|
| Phần Retrieval bạn phụ trách theo mô tả nhiệm vụ | Điều phối BM25/Dense/Hybrid, query preprocessing/encoding, gọi read adapters, RRF, hydration/integrity validation và response; các file cụ thể được trace trong từng báo cáo |
| Thành phần có trong repo và được Retrieval sử dụng | Tokenizer từ indexing service; sparse/vector repositories; RPC SQL; chunk/source readers; index metadata/lifecycle infrastructure |
| Upstream | Chuẩn bị source documents, parse/chunk, ghi chunks, tạo postings/thống kê BM25, passage embeddings và duy trì trạng thái index |

Source snapshot chứng minh cơ chế và dependency, **không tự chứng minh tác giả từng dòng code**. Không có lịch sử Git trong bản thư mục khảo sát để quy quyền tác giả. Khi nói “tôi triển khai”, giới hạn theo phạm vi công việc bạn xác nhận; nói “tôi tích hợp/sử dụng” đối với hạ tầng có sẵn, và “pipeline upstream tạo” đối với document indexing. Không nhận việc tạo model E5, pgvector, crawler hay toàn bộ SQL infrastructure là của mình.

## Ba điểm rất dễ nói sai

- BM25 dùng regex Unicode và giữ dấu tiếng Việt; không có word segmentation tiếng Việt.
- Dense dùng checkpoint yêu cầu 384 chiều đã kiểm tra từ code/config, không suy đoán từ tên E5. Query encoder và passage embedder là hai implementation riêng.
- Hybrid thực tế **tuần tự, STRICT, hydrate trước fusion**. Không có một hydration pass mới sau RRF và không có fallback khi một nhánh lỗi.

Entry point đã thấy là `scripts/search_legal_chunks.py` → `src/retrieval_bootstrap.py` → `RetrievalService.search`. File `src/applications/tillegal/tools/legal_retrieval.py` hiện chỉ có docstring; không nên tuyên bố nó đã nối Retrieval vào một HTTP/agent tool hoàn chỉnh.
