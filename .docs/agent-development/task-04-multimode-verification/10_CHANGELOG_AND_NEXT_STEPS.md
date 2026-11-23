# Changelog và readiness

Thêm `tests/unit/applications/tillegal/test_query_search_multimode.py` gồm41 cases. Thêm12 Markdown Task4, evidence/live_probe.py, source_before/after/delta.json, model-and-index.json,5 live reports,cross-mode.json và offline-junit.xml. Staging ở workspace `.tmp/task4-verification` chỉ phục vụ ghi các file kiểm chứng vào target được user chỉ định; không lấy legacy runtime source làm authoritative.

Runtime src, configs, pyproject và uv.lock không thay đổi. Không có integration defect mới buộc sửa Query/Search/Service. Reranker fallback vốn là designed behavior và được giữ. Đã ghi đúng hậu quả deadline Dense cold-start, không tăng timeout. Không migration/indexing/model download/crawler/Git write.

VERIFIED REAL SUPABASE cho một sample mỗi successful profile; PARTIAL cho cold-start stability và coverage thực tế. BM25 direct parity chỉ cùng observed index BEST_EFFORT. Chưa kiểm held-out legal quality, concurrency/resource contention hoặc phục hồi process. Model revision indexing chưa được pin/attest trong index metadata ngoài model/dimension/prefix. Datetime/policy trust boundary cần caller thực thi khi nối API/graph.

## Readiness Task 5

Contracts đủ cơ sở bắt đầu thiết kế/nối LangGraph gọi QuerySearch theo task riêng: plan dict, options explicit, typed native responses, clarification zero calls và failures giữ trạng thái. Readiness ở mức prototype có test, không production readiness. Task5 phải giữ subclasses fusion/reranking khi state serialize, không tạo EvidenceBundle legacy hoặc legal verification flags giả, và xử lý deadline/fallback rõ ràng.

Khuyến nghị Task5 tiếp theo duy nhất: graph tối thiểu Query→Search→END dùng entrypoint/service hiện tại, test fake trước, bảo toàn states và stop conditions. Cần xem chính source task mới trước triển khai. Task4 dừng tại verification; chưa tạo graph, HTTP, Judge, Answer/Summary hoặc Citation Verification.
