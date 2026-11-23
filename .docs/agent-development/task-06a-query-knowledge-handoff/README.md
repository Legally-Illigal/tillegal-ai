# Task6a — Query Agent technical knowledge handoff

Authority: `D:/DOWNLOAD/tillegal-ai/tillegal-ai-main`. Ngày bàn giao21/11/2026 theo Asia/Saigon. Checkout là source export không có .git; không có commit SHA có thể xác minh. Không dùng legacy checkout làm source.

Version evidence: [baseline](evidence/baseline.json) ghi SHA-256 của380 files hiện có thuộc src/tests/configs, dependency manifests và historical reports (không gồm folder Task6a mới). SHA-256 của chính baseline: `2a6acc2ab3a794e885a31eaec90aefe2934a5fbf3df9580e6023fdf996b73849`. [Final verification](evidence/quality-checks.json) đối chiếu hashes, inventory, ranges/signatures và links. Đây là fingerprint tập files kiểm tra, không phải Git revision hoặc checksum mọi artifact trong checkout.

## Cách đọc

Đọc01→02→03→04→05→06 để hiểu contracts/rules;07 là phần bắt buộc để hiểu source chạy từng bước;08 đối chiếu runtime. Sau đó09→10 cho graph/boundary;11→12→15 cho evidence/limitations.13→14 dùng luyện vấn đáp.16 tra symbol,17 dành cho người biên soạn study guide độc lập. Tất cả giải thích bằng tiếng Việt; tên symbol/type tiếng Anh giữ theo source.

| Tài liệu | Nội dung |
|---|---|
| [01_ARCHITECTURE_AND_CALL_GRAPH.md](01_ARCHITECTURE_AND_CALL_GRAPH.md) | Kiến trúc và call graphs |
| [02_INPUT_VALIDATION_AND_UNICODE.md](02_INPUT_VALIDATION_AND_UNICODE.md) | Input/Unicode |
| [03_INTENT_AND_DOMAIN_RULES.md](03_INTENT_AND_DOMAIN_RULES.md) | Intent/domain |
| [04_TEMPORAL_PROCESSING.md](04_TEMPORAL_PROCESSING.md) | Date/time |
| [05_SUBQUERIES_AND_QUERYPLAN.md](05_SUBQUERIES_AND_QUERYPLAN.md) | Subqueries/QueryPlan |
| [06_CLARIFICATION_AND_ERRORS.md](06_CLARIFICATION_AND_ERRORS.md) | Clarification/errors |
| [07_SOURCE_EXECUTION_TRACE.md](07_SOURCE_EXECUTION_TRACE.md) | Source-level trace |
| [08_OBSERVED_EXECUTION_TRACES.md](08_OBSERVED_EXECUTION_TRACES.md) | Observed executions |
| [09_LANGGRAPH_QUERY_NODE.md](09_LANGGRAPH_QUERY_NODE.md) | LangGraph |
| [10_QUERY_SEARCH_CONTRACT.md](10_QUERY_SEARCH_CONTRACT.md) | Query/Search boundary |
| [11_TEST_MATRIX_AND_RESULTS.md](11_TEST_MATRIX_AND_RESULTS.md) | Tests |
| [12_RATIONALE_AND_LIMITATIONS.md](12_RATIONALE_AND_LIMITATIONS.md) | Rationale |
| [13_PEDAGOGICAL_QA_AND_GLOSSARY.md](13_PEDAGOGICAL_QA_AND_GLOSSARY.md) | Hỏi–đáp/glossary |
| [14_ORAL_EXPLANATIONS.md](14_ORAL_EXPLANATIONS.md) | Oral scripts |
| [15_OPEN_QUESTIONS.md](15_OPEN_QUESTIONS.md) | Gaps |
| [16_SOURCE_SYMBOL_INDEX.md](16_SOURCE_SYMBOL_INDEX.md) | Source index |
| [17_TECHNICAL_AUTHOR_HANDOFF.md](17_TECHNICAL_AUTHOR_HANDOFF.md) | Author synthesis |

## Cấp độ bằng chứng

- **OBSERVED:** chạy được trong focused tests hoặc diagnostic evidence; nêu fixture/fake khi có.
- **SOURCE-DERIVED:** kết luận từ source/AST/call graph, không giả là số đo runtime.
- **ILLUSTRATIVE:** ví dụ giảng giải, không claim đã thực thi.

[120-test JUnit](evidence/focused-junit.xml), [52 diagnostic cases](evidence/query-traces-complete.json), [boundary probes](evidence/boundary-probes.json), [160-symbol index data](evidence/source-symbols.json), [historical inventory](evidence/historical-documents.json). Initial query-traces.json gồm42 case là subset trước bổ sung, không cộng vào52. Scripts diagnose_query.py/supplement_diagnostics.py chỉ dùng synthetic inputs và FakeRetrieval, không dùng Supabase/model/API. Các script thuộc documentation evidence mới, không phải application code/tests mới.

17 traces chi tiết ở08;48 hỏi–đáp và32 glossary entries ở13. Các code range được kiểm trên source checkout này; relative links tới source và symbol index16 cho phép xem lại. Nếu source đổi sau bàn giao phải kiểm lại checksum/ranges trước khi tái dùng.

Không chỉnh source/tests/config/dependencies/old reports; không DB migration, Supabase write, LLM inference, model download, Git init/commit/push. Chỉ tạo docs và diagnostics trong folder Task6a này. Không tạo Word/slides và không tiếp tục Search knowledge handoff.
