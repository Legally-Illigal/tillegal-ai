# Bàn giao cho người biên soạn study guide tiếng Việt

## Authority và cách sử dụng

Chỉ checkout `D:/DOWNLOAD/tillegal-ai/tillegal-ai-main` là authoritative. Export không có Git metadata; dùng [baseline 409 file](evidence/baseline.json), [source/symbol inventory](evidence/source-symbols.json) và [final quality audit](evidence/quality-checks.json) để định danh phiên bản. Không bịa branch, commit hoặc PR. Executable source ưu tiên hơn reports Task 3–6a khi có khác biệt.

Đây là synthesis/index cho tác giả viết Word độc lập ở giai đoạn sau. Nó không thay [source walkthrough chương 10](10_SOURCE_EXECUTION_TRACE.md). Task 6B không tạo Word/slides và không sửa application/test code.

## Bản đồ tài liệu authoritative

| File | Vai trò khi viết study guide |
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

## Essential source files

- `src/applications/tillegal/agents/search/agent.py`: SearchOptions 13–28, SearchState 31–35, async search 38–56.
- `src/applications/tillegal/agents/query/agent.py`: Subquery 15–17, QueryPlan 20–26, understand 29–95; chỉ giải thích đủ receiving boundary, không lặp toàn bộ Query handoff.
- `src/query_search_bootstrap.py`: QuerySearch 16–21, create_query_search 24–42.
- `src/retrieval_bootstrap.py`: create_retrieval_service 22–70; dùng các Supabase read adapters hiện có, không dùng legacy ai_core/LegalRetrieval.
- `src/application/services/retrieval_service.py`: search 192–305; dispatch BM25/Dense/Hybrid, optional reranking trong Hybrid.
- `src/applications/tillegal/retrieval/contracts.py`: Request 23–44, UnifiedEvidence 65–110, Response 113–149. Hybrid/reranked extensions nằm trong hybrid_models.py và reranking_models.py.
- `src/applications/tillegal/graphs/legal_qa.py`: node Search 39–54, compiler 57–66, workflow 69–95.
- `src/applications/tillegal/state/legal_qa_state.py`: JudgeHandoff 18–93, LegalQAState 96–103.
- `src/framework/runtime/executor.py`: execution, lifecycle và cancellation 28–102; ExecutionContext/binding ở execution_context.py.

[Chương 18](18_SOURCE_SYMBOL_INDEX.md) có clickable paths, actual signatures và AST ranges đầy đủ. Không dùng line numbers từ historical report thay source index hiện tại.

## Exact contracts phải giữ đúng

Search nhận `plan: dict`, `retrieval: RetrievalService`, `options: SearchOptions`, trả `SearchState`. QueryPlan có sáu fields: original, intent, domain, temporal_scope, subqueries, clarification. Subqueries có text/purpose, cardinality 1–4. Clarification nullable nhưng vẫn required key.

SearchOptions có bốn required fields: mode enum bm25/dense/hybrid; top_k StrictInt 1–50; as_of_date date; allowed_usage_policies tuple StrictStr với ít nhất một value. Policies được strip và dedup giữ thứ tự. Không có implicit defaults tại SearchOptions. Application cung cấp trusted options; user text không tự chọn governance policy hoặc trusted date.

RetrievalRequest chỉ có query, mode, top_k, as_of_date và allowed_usage_policies. Không forward original, domain, temporal_scope, purpose hoặc graph IDs. Query giữ nguyên subquery text; nonblank validator chỉ dùng strip để kiểm. Service có query_used riêng. Request.top_k có default 10 nhưng Search luôn supply explicit value.

SearchState gồm raw plan object, typed request tuple, native response tuple và status CLARIFICATION_REQUIRED/COMPLETED/FAILED. Không flattened global evidence ranking hoặc legacy EvidenceBundle. Full field inventory của RetrievalResponse/UnifiedEvidence ở chương 07; không lược provenance, time/policy metadata, hash hoặc score semantics khi viết contracts.

JudgeHandoff v1 gồm schema_version, request_id, run_id, question, typed plan/options, typed requests/responses, search_status và status. Explicit response union giữ Hybrid/reranked extension fields qua JSON. Warnings/errors là derived properties, không tự thành top-level JSON fields; nested responses vẫn giữ data. Object identity trong process khác value equality sau JSON.

## Complete execution path và intermediate objects

Standalone: application question → QuerySearch.search → understand → QueryPlan.model_dump dict → Search → parsed plan/options → eager request tuple → sequential service calls và response append → SearchState → caller.

LangGraph: Workflow.execute tạo fresh state và context IDs → GraphExecutor bind context → Query node gọi understand → router chọn clarification END hoặc Search node → existing Search function → JudgeHandoff.from_search và context validation → state/status/error-code update → END.

Query node và Search node gọi underlying functions trực tiếp. Không gọi toàn QuerySearch.search bên trong Search node, không chạy Query lần hai. Search function không tự tạo JudgeHandoff; graph node làm việc đó.

Khi viết source chapter, dùng chương 10 làm xương sống. Giải thích từng variable: raw plan, parsed plan, options, requests, responses, response, result và handoff. Phân biệt synchronous model validation/Query/factory calls với asynchronous service/runtime boundaries; không chỉ chép diagrams rồi bỏ execution details.

## Critical rules và consequences

1. Plan validation chạy trước options, rồi clarification guard, request prebuild và I/O.
2. Tất cả requests phải hợp lệ trước call đầu. Một tab-only query ở vị trí hai có thể làm toàn batch có zero calls.
3. Processing tuần tự; top_k per query; duplicate text vẫn tạo duplicate calls; không cross-query dedup/fusion.
4. NO_MATCH tiếp tục. FAILED được append rồi dừng, giữ prior responses. Unexpected exception propagate, không return partial SearchState.
5. Native responses giữ nguyên content, ranking, metadata, warnings và error; Search không nâng verification flags.
6. Packet validator kiểm original, order, options, response echo, failure sequence và statuses. Search function chưa tự kiểm response context.
7. READY chỉ nghĩa nonfailed Search có ít nhất một evidence. Graph map nó thành SEARCH_COMPLETED; chưa đánh giá legal sufficiency.
8. Classified retrieval failure có thể đi cùng executor lifecycle SUCCEEDED. Outer exception/timeout/cancellation có propagation và lifecycle khác.

## Runtime và test evidence

Chương 11 trình bày 18 detailed traces từ [35 direct Search cases và 9 graph invocations](evidence/search-traces.json): một query cho mỗi profile, multi-query, clarification, malformed plan, empty/tab-only text, no-match, first/partial failure, exception, duplicate calls, whitespace retention, extras, context mismatch và normalized options. Handoff ở direct diagnostic cases do harness gọi tường minh; graph cases mới là packet do node tạo.

Lượt focused regression mới: **320 passed, 0 failed/skipped, pytest console 4.80s**. Command, environment, assertions và JUnit ở chương 14. Diagnostics không cộng vào pytest count; 18 detailed traces là tập con trình bày, không thêm executions.

Historical Task 3 chỉ live standalone BM25; Task 4 bổ sung BM25/Dense-repeat/Hybrid/rerank, vẫn giữ initial Dense timeout riêng. Task 5 chỉ live graph BM25. Không biến historical live thành execution mới của Task 6B hoặc lấy standalone live làm bằng chứng graph live mọi mode. APPLIED với fake scorer không phải inference Cross-Encoder thật trong lượt mới.

Snapshot line events là giá trị trước statement ở dòng đó thực thi. Source-derived values không được gắn nhãn runtime observation. Hash integrity, type validation và test-suite runtime không thay semantic/legal quality hoặc production latency benchmark.

## Unsupported claims phải tránh

- Search là LLM agent, tự tính embeddings/BM25/RRF hoặc trực tiếp gọi Supabase.
- Query temporal_scope tự override date/policies; Search tự chọn trusted mode.
- Có global top_k, multi-query fusion/dedup hoặc parallel fan-out.
- Mọi exception được sanitize và chuyển thành response FAILED.
- Hash MATCHED_STORED chứng minh raw quote hoặc đúng luật; READY là Judge approval.
- Search function tự tạo packet; graph đã chạy Judge/Answer.
- Frozen models deep immutable hoặc TypedDict tự validate missing keys runtime.
- Mọi base-type serializer giữ subtype giống explicit union packet.
- Production HTTP, ACL, lifecycle, durable checkpoint hoặc throughput đã được verify.
- Task 4 standalone live chứng minh graph live mọi backend.

## Thứ tự Word study guide đề xuất

Trách nhiệm/giới hạn → hai call paths → contracts/trust boundary → validation/request construction → multi-subquery execution → service boundary → typed output/provenance/ranking → failure matrix → graph/handoff → bootstrap/lifecycle → worked examples → test evidence/limitations → oral exam/glossary.

Giữ một chương source walkthrough đầy đủ; summary này không thay nó. [Chương 19](19_OPEN_QUESTIONS.md) liệt kê các quyết định còn mở: direct response validation, global budget/fusion, exception history, ACL, lifecycle/warmup, metadata JSON policy và future Judge criteria. Không tự triển khai các thay đổi khi soạn guide.
