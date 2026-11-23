# Final Query Agent implementation selection

**Nên giữ và publish Implementation A — understand(question: str).** Nó đáp ứng current Query/Search contracts và đã được xác minh lại. B có deterministic core/unit tests hữu ích nhưng dùng public contract khác, chưa nối Search/LangGraph; giữ WIP và không đưa vào PR hiện tại. Không có cơ sở coi đây là hai developers độc lập.

- [So sánh 15 tiêu chí và quyết định](01_COMPARISON_AND_DECISION.md).
- [Manifest chính xác và kế hoạch commit an toàn](02_PUBLICATION_MANIFEST.md).
- [A: 320 regression tests](evidence/A-regression.xml), [B: 27 unit tests](evidence/B-query-unit.xml).
- [Commands/CWD/results](evidence/test-results.json).
- [13 paired cases,4 B control cases và compatibility probes](evidence/comparison-observations.json).
- [Publication manifest machine-readable](evidence/publication-manifest.json).
- [Source/symbol ranges](evidence/source-symbols.json),[baseline](evidence/baseline.json),[final verification](evidence/final-verification.json).

Ngày 22/11/2026, Asia/Saigon. A320 pass/4.83s, B27 pass/0.66s là executions mới, offline; không cộng số hai suites thành chất lượng so sánh. B dump gửi A Search bị ValidationError trước retrieval call. A clarification vẫn zero calls. Không chạy DB/model thật.

Source version dùng checksum inventory:444files A và332files B trong các scopes đã định nghĩa, không caches/bytecode hoặc audit directory mới. Git status/HEAD của B được snapshot trước/sau để xác nhận WIP giữ nguyên. Source executable ưu tiên hơn design docs lịch sử.

Chỉ tạo báo cáo/diagnostics trong audit-only directory này. Không sửa application/tests/config/old reports/WIP, không thay worktrees/branches, stage, commit, push hoặc PR. Kết thúc ở architecture decision; không implement adapter hay Query Agent thứ ba.
