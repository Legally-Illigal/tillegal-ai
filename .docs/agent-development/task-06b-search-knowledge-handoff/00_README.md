# Task 6B — Search Agent complete technical knowledge handoff

Nguồn authoritative duy nhất: `D:/DOWNLOAD/tillegal-ai/tillegal-ai-main`. Ngày hoàn tất: **22/11/2026**, timezone Asia/Saigon. Checkout là source export không có `.git`; không có branch, commit SHA hoặc quan hệ PR có thể xác minh. Không dùng checkout legacy làm nguồn.

## Phiên bản và phạm vi

[Baseline](evidence/baseline.json) ghi SHA-256 của **409 file hiện có** thuộc src, tests, configs, dependency manifests và historical agent reports, bao gồm Task 6a. Không bao gồm Task 6B mới, cache hoặc bytecode. SHA-256 của chính baseline: `938b2fae4433908bc4105aa4cdb761706597423d245af681b04b81e785dd1f24`.

[Final quality audit](evidence/quality-checks.json) kiểm inventory, hashes, paths, signatures, ranges, schemas và links. Fingerprint này định danh tập file được rà soát, không thay thế một Git revision hay kiểm kê toàn bộ ổ đĩa.

Chỉ tạo tài liệu và sanitized diagnostics trong thư mục Task 6B. Không sửa source, tests, config, dependencies hoặc báo cáo cũ; không gọi live DB, tải model, chạy paid inference, migration hoặc Git write. Không tạo Word/slides và không implement Judge/Answer.

## Reading order và tài liệu

Đọc 01–07 để hiểu contracts và execution. Chương 10 là source walkthrough bắt buộc, chương 11 dùng đối chiếu runtime. Chương 08–09 giải thích graph và packet; 12–15 cùng 19 giải thích failures, lifecycle, evidence và giới hạn. Dùng 16–17 luyện vấn đáp, 18 tra symbols, 20 bàn giao cho tác giả Word ở giai đoạn sau.

| File | Nội dung |
|---|---|
| [01_SEARCH_ARCHITECTURE.md](01_SEARCH_ARCHITECTURE.md) | Kiến trúc, trách nhiệm và call graphs |
| [02_SEARCH_INPUT_CONTRACTS.md](02_SEARCH_INPUT_CONTRACTS.md) | Input contracts và trusted options |
| [03_QUERYPLAN_VALIDATION.md](03_QUERYPLAN_VALIDATION.md) | Receiving QueryPlan và thứ tự validation |
| [04_SUBQUERY_EXECUTION.md](04_SUBQUERY_EXECUTION.md) | Thực thi nhiều subqueries |
| [05_RETRIEVAL_REQUEST_CONSTRUCTION.md](05_RETRIEVAL_REQUEST_CONSTRUCTION.md) | Xây dựng RetrievalRequest |
| [06_RETRIEVAL_SERVICE_BOUNDARY.md](06_RETRIEVAL_SERVICE_BOUNDARY.md) | RetrievalService call boundary |
| [07_SEARCH_OUTPUT_AND_EVIDENCE.md](07_SEARCH_OUTPUT_AND_EVIDENCE.md) | SearchState, typed responses và evidence |
| [08_LANGGRAPH_SEARCH_NODE.md](08_LANGGRAPH_SEARCH_NODE.md) | LangGraph Search node |
| [09_JUDGE_HANDOFF.md](09_JUDGE_HANDOFF.md) | JudgeHandoff v1 |
| [10_SOURCE_EXECUTION_TRACE.md](10_SOURCE_EXECUTION_TRACE.md) | Source walkthrough và call boundaries |
| [11_OBSERVED_RUNTIME_EXAMPLES.md](11_OBSERVED_RUNTIME_EXAMPLES.md) | Các trace thực thi đã quan sát |
| [12_ERROR_AND_FAILURE_MATRIX.md](12_ERROR_AND_FAILURE_MATRIX.md) | Error và failure matrix |
| [13_BOOTSTRAP_AND_DEPENDENCIES.md](13_BOOTSTRAP_AND_DEPENDENCIES.md) | Bootstrap, dependency injection và lifecycle |
| [14_TEST_MATRIX_AND_RESULTS.md](14_TEST_MATRIX_AND_RESULTS.md) | Test matrix và kết quả |
| [15_RATIONALE_AND_LIMITATIONS.md](15_RATIONALE_AND_LIMITATIONS.md) | Rationale, alternatives và limitations |
| [16_PEDAGOGICAL_QA_AND_GLOSSARY.md](16_PEDAGOGICAL_QA_AND_GLOSSARY.md) | 50 câu hỏi–đáp và 46 thuật ngữ |
| [17_ORAL_EXPLANATIONS.md](17_ORAL_EXPLANATIONS.md) | Giải thích miệng và blackboard walkthrough |
| [18_SOURCE_SYMBOL_INDEX.md](18_SOURCE_SYMBOL_INDEX.md) | Source/symbol index |
| [19_OPEN_QUESTIONS.md](19_OPEN_QUESTIONS.md) | Discrepancies và câu hỏi mở |
| [20_HANDOFF_FOR_DOCUMENT_AUTHOR.md](20_HANDOFF_FOR_DOCUMENT_AUTHOR.md) | Bàn giao cho tác giả study guide |

## Coverage matrix

| Trách nhiệm | Source authority | Bằng chứng | Chương |
|---|---|---|---|
| Identity và ownership | Search 3–56, service 192–305 | Source và existing tests | 01 |
| Validate plan/options | Search 40–41 và schemas | Tests và malformed-input diagnostics | 02–03 |
| Clarification skip | Search 42–43, graph 36–37 | Tests mọi profile và graph stream | 03, 08 |
| Request mapping | Search 44, Request 23–44 | Mapping, normalization và tab-only probes | 05 |
| Multi-query order/budget/duplicates | Search 44–56 | Call events, duplicate và 3-query cases | 04, 11 |
| Failure và exception | Search 48–55 | Partial failure, exception và graph tests | 12 |
| Delegation mọi mode | Service 192–305 | Real service/fake ports; historical live Task 4 | 06, 14 |
| Native evidence preservation | Search 48, 53, 56 | Identity, parity và metadata assertions | 07 |
| Handoff subtype/JSON | State 15–93 | Round-trip và type checks cho 4 profiles | 09 |
| Graph statuses, reducers, END | Graph 39–66, WorkflowState | Node/graph/stream tests | 08 |
| IDs và state isolation | Workflow 84–95, context binding | Repeated/concurrent fake invocations | 08, 13 |
| Timeout/cancellation | Service và executor | Typed timeout, outer deadline, token/task cancellation | 12 |
| Bootstrap/reuse | QuerySearch và retrieval bootstrap | Factory mocks, adapter source | 13 |
| Source execution | 29 actual blocks, 361 AST symbols | Exact snippet/range verification | 10, 18 |
| Học liệu | Contracts hiện tại | 50 Q&A, 46 terms, oral scripts | 16–17 |

## Evidence labels và giới hạn

- **OBSERVED:** execution mới của Task 6B; ghi rõ synthetic service hoặc real service với fake ports.
- **HISTORICAL_OBSERVED_NOT_RERUN:** artifacts live Task 4–5 đã inspect và đối chiếu hash, không chạy lại trong Task 6B.
- **SOURCE-DERIVED:** kết luận từ code/call graph hoặc upper bound có điều kiện.
- **ILLUSTRATIVE:** ví dụ giảng giải, không khẳng định đã thực thi.

Bằng chứng: [320-test JUnit](evidence/focused-junit.xml), [35 Search cases và 9 graph invocations](evidence/search-traces.json), [supplemental probes](evidence/supplemental-probes.json), [standalone/graph parity](evidence/standalone-graph-parity.json), [historical live summary](evidence/historical-live-summary.json), [environment](evidence/environment.json).

18 traces chi tiết ở chương 11 là tập con được trình bày, không phải thêm 18 runs độc lập. Diagnostics không được cộng vào pytest count. Fake model/backend không được đổi thành real execution claim. Nếu source thay đổi sau bàn giao, phải kiểm lại checksum và ranges trước khi tái sử dụng.
