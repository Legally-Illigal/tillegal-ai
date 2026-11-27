# Giới hạn, ownership và bước tiếp theo

> Ghi chú publication: tài liệu ghi lại implementation/acceptance Phase A. Candidate PR được kiểm thử lại độc lập trên main sau V2; trạng thái Git/CI mới nhất được ghi trong FINAL_MAIN_INTEGRATION_REPORT.md (local). Source links đã đổi sang đường dẫn tương đối để review trên GitHub.

**Phase A sẵn sàng review/tích hợp về kỹ thuật.** Compiled graph async thực sự await injected existing SemanticQueryAgent, giữ deterministic path và Search/handoff. Bằng chứng mới: 22 case Phase A, graph 52, V2 43, focused 670 và full 776 PASS trên V2 base sạch; development full 732 PASS. Ruff/import PASS. Không dùng kết quả lịch sử thay cho lần chạy này.

## Phạm vi đã hoàn tất

Một file production graph, một file test hiện có và sáu Markdown. Không tạo planner thứ hai, không gọi facade.search trong graph, không hardcode model/read key/per-request provider construction, không thêm fallback/retry. Async .ainvoke/.astream/Workflow.execute hoạt động theo DI; sync semantic .invoke từ chối rõ bằng LangGraph TypeError.

Original sync query, route và Search methods giữ AST; toàn bộ function/class test cũ giữ AST. Native SearchState/score/provenance/subtypes, QueryPlan/SemanticAnalysis/V2/JudgeHandoff và provider prompts/config không đổi. Kết quả kiểm tra hash/scope cuối ghi ở dưới.

## Những việc chưa được làm

- Completion trong test là mock; chưa live Gemini hoặc Supabase validation, không đo semantic/legal quality. Trace NO_MATCH là fake read fixture, không kết luận corpus thật thiếu luật.
- Graph vẫn kết thúc sau Query/Search và technical handoff. Judge/Summary/Verify chưa có node; không có feedback loop/history/budget controller mới.
- Contract V2 vẫn opt-in facade riêng; Phase A không tự trả SearchEnvelopeV2 từ graph hoặc đổi LegalQAState.
- Deterministic guard lookup/clarification trong SemanticQueryAgent vẫn có thể không gọi model; không phải fallback sau error.
- Sync workflow QA không được quảng cáo hỗ trợ: Search vốn async, semantic query mới cũng async; dùng async API.

## Ownership

Query/Search sở hữu DI seam ở query node và test compiled graph. Judge owner giữ sufficiency/feedback contract; Summary owner giữ native-compatible draft/citation input; orchestrator giữ retry/history/stop policy; corpus/retrieval owner giữ source identity/representation; runtime sở hữu credentials/composition. Không sửa source của các owner đó trong Phase A.

## Blockers cho Phase B/C, không chặn acceptance Phase A

Audit cross-branch đã xác nhận hai retrieval/contracts.py có API khác nhau; không merge bằng đè một bên. SearchState/V2 chưa phải Judge input; cần projection với stable I/E IDs, trusted date, warnings/errors/partial retention. Empty issues cần policy được duyệt. Summary hiện yêu cầu EvidenceBuilder normalized bundle khác native retrieval_chunk_content, cần owner mở boundary hoặc corpus bridge thật; không bịa version/location/hash/representation.

Provider Judge/Summary dùng API/cấu hình riêng; Phase A không chuyển Query sang provider của nhánh đó. Judge next_queries typed có thể làm nền cho loop theo issue nhưng missing_items vẫn list[str]; C cần follow-up API giữ original/registry và controller budgets, không gửi next query như original mới. Verify/exact resolver/web/PDF deferred; support/lookup không thành resolved.

## Bước nhỏ tiếp theo

Review Phase A diff độc lập, sau đó yêu cầu riêng cho Phase B0/B1 và phối hợp Summary owner ở B2. Giữ test single-pass unified QA với mocks làm gate trước khi thêm loop C. Không mở rộng nhiệm vụ hiện tại thành implementation của Judge/Summary.

Tài liệu mô tả acceptance trước publication; trạng thái PR/merge được ghi ở báo cáo tích hợp cuối. Main/nhánh đồng đội không được ghi. Chưa sửa audit lịch sử hoặc provider credentials/configuration.

## Scope và bảo toàn đã xác minh cuối

Snapshot trước sửa có 728 đường dẫn: chỉ graph và test thuộc allowlist thay đổi; 726 đường dẫn còn lại giữ nguyên SHA-256, gồm V1/V2 contracts, Judge/Summary, prompt/config/.env và unrelated work. Chỉ thêm đúng sáu Markdown trong graph-phase-a. Hai file Phase A giống byte giữa development và integration worktree. Index cả hai vẫn rỗng, HEAD gốc và base worktree không đổi; không commit/push/merge.

Đã kiểm tra 19 source link theo file/line, Markdown fences/whitespace, known-secret/token scan và git diff --check: PASS. Snapshot, logs, actual controlled trace, AST compatibility evidence, final verification và patch review lưu ngoài project tại D:\DOWNLOAD\tmp\tillegal-graph-phase-a-20261127. Patch chỉ chứa hai file code/test Phase A; sáu tài liệu đã mirror riêng để review trong worktree.
