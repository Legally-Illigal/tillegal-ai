# Bàn giao cho người viết study guide độc lập

## Nguồn và phạm vi

Authority duy nhất là checkout `D:/DOWNLOAD/tillegal-ai/tillegal-ai-main`, không dùng legacy checkout. Đây là source export không có Git metadata; phiên bản được neo bằng [baseline SHA-256 inventory](evidence/baseline.json), [symbol inventory](evidence/source-symbols.json) và kiểm tra cuối [quality checks](evidence/quality-checks.json). Không bịa commit SHA. Source còn nguyên; tài liệu này là synthesis/index, không thay phần giải thích từng block ở07.

Tài liệu dành cho sinh viên biết Python/ML căn bản và người biên soạn Word giai đoạn sau. Chưa tạo Word hoặc slide. Phạm vi kết thúc ở Query → Search boundary; không phát triển Search knowledge handoff hoặc giải thích Retrieval internals.

## Bản đồ nội dung authoritative

| Nhu cầu khi viết | Đọc trước | Nội dung phải giữ đúng |
|---|---|---|
| Định danh năng lực/architecture | [01](01_ARCHITECTURE_AND_CALL_GRAPH.md) |15 câu hỏi năng lực; deterministic, không Query LLM/model/database |
| Boundary và Unicode | [02](02_INPUT_VALIDATION_AND_UNICODE.md) |Raw type/length/control, NFC/strip, original riêng, error codes |
| Classification | [03](03_INTENT_AND_DOMAIN_RULES.md) |2 intents,2 domains, actual regex, priority/false positives |
| Date/time | [04](04_TEMPORAL_PROCESSING.md) |Mentions khác as_of_date và effective-date checks |
| Data model | [05](05_SUBQUERIES_AND_QUERYPLAN.md) |Full field table,1–4 subqueries, required nullable clarification |
| Clarification/errors | [06](06_CLARIFICATION_AND_ERRORS.md) |Priority, error ownership, invalid/clarify/no match |
| Source execution | [07](07_SOURCE_EXECUTION_TRACE.md) |12 blocks và FROM/CALL/INPUT/ACTION/RETURN/BACK TO |
| Concrete runtime | [08](08_OBSERVED_EXECUTION_TRACES.md) |17 traces chi tiết,52-case summary; labels observation/derivation |
| LangGraph | [09](09_LANGGRAPH_QUERY_NODE.md) |Query node gọi understand trực tiếp, updates/router/isolation |
| Search receiving side | [10](10_QUERY_SEARCH_CONTRACT.md) |Validate toàn plan trước clarification; request text + injected options |
| Verification | [11](11_TEST_MATRIX_AND_RESULTS.md) |120 existing tests, command/runtime; không cộng historical counts |
| Rationale | [12](12_RATIONALE_AND_LIMITATIONS.md) |Source fact vs engineering interpretation vs chưa đo |
| Pedagogy | [13](13_PEDAGOGICAL_QA_AND_GLOSSARY.md) |48 câu hỏi có đáp án;32 thuật ngữ; phản biện câu trả lời sai |
| Oral exam | [14](14_ORAL_EXPLANATIONS.md) |Script60s/3min và blackboard ownership |
| Gaps/discrepancies | [15](15_OPEN_QUESTIONS.md) |Missing historical docs và source/doc mismatch |
| Exact symbols/ranges | [16](16_SOURCE_SYMBOL_INDEX.md) |Verified AST index, entrypoint signatures |

## Những sự thật không được thay đổi khi diễn giải

1. Query Agent là `understand(question: str) -> dict` trong src/applications/tillegal/agents/query/agent.py29–95. Không có Agent class sở hữu model hoặc session bên trong nó. Các model QueryPlan/Subquery là validation schemas.
2. Runtime input phải str, raw length1–10000. Cc/Cs bị chặn ngoại trừ tab/LF/CR. Normalize NFC + strip trên local text, original giữ raw argument.
3. Public dict có đúng các fields do constructor tạo: original, intent, domain, temporal_scope, subqueries, clarification. Nội bộ QueryPlan là BaseModel; public value không phải JSON string. Lúc qua graph plan vẫn là dict.
4. intent là quote_lookup hoặc legal_question; domain là labour hoặc unknown. Prefix/parts quyết định quote_only; domain là regex substring bốn keywords. Không thêm taxonomy mới để bài học trông phong phú hơn.
5. temporal_scope là list[str] theo mentions, không resolve hiện nay và không auto-set as_of_date. Date slash đầy đủ được date() validate, ISO toàn phần không có parser.
6. Base parts lấy tối đa4; topic rules chỉ append nguyên cụm đã có khi còn chỗ và chưa seen. Base duplicates còn tồn tại. Mọi accepted plan có1–4 subqueries.
7. Clarification là trả plan có message, khác QueryInputError. Invalid_date có quyền ghi đè message ambiguity/too-many-parts. Graph skip Search theo clarification; direct Search cũng có guard sau schema validation.
8. QuerySearch.search gọi understand rồi Search; graph Query node gọi understand trực tiếp và Search chạy ở node kế tiếp. Không vẽ wrapper QuerySearch bên trong Query node.
9. Search đọc subquery.text để tạo request, options đến từ pipeline dependency. Query domain/time không được tự chuyển thành retrieval filter.
10. total=False trên LegalQAState là optional keys của TypedDict, không runtime validation hoặc checkpoint persistence. Task5 report có một table required không đúng với source hiện tại; không sao chép lỗi đó.

## Cấu trúc study guide gợi ý

Mở đầu bằng trách nhiệm/giới hạn, sau đó data contracts và transformations, tiếp theo rules theo thứ tự thực thi, rồi hai call paths. Dùng07 làm xương sống chương source walkthrough; dùng08 cho bài tập trace và13 cho vấn đáp từ cơ bản đến khó. Kết thúc bằng graph boundary, errors, test evidence và limitations. Đây là hướng biên soạn, chưa phải nội dung Word được tạo.

Khi trích code, lấy nguyên block/range ở07 hoặc source hiện tại với16 để kiểm lại. Không chỉ chép Mermaid rồi bỏ qua việc values thay đổi qua từng statement. Đặc biệt giải thích raw question/text/parts/topic/queries/subqueries khác nhau ở đâu.

## Dẫn chứng runtime nên dùng

[08](08_OBSERVED_EXECUTION_TRACES.md) chứa ordinary question, explicit lookup, ambiguous phrase, invalid calendar date, leap day, year, NFC/NFD equivalence, multipart, multi-rule,5parts, clarification override, empty prefix, duplicates, ISO, tab-only và punctuation-only. Dữ liệu đầy đủ ở [52-case JSON](evidence/query-traces-complete.json).

Mỗi trace đã ghi intermediate locals lấy bằng diagnostic và final QueryPlan. Domain keyword re-evaluation được ghi SOURCE-DERIVED khi không phải captured local. `post_validation` trong diagnostic nghĩa đã qua raw type/length/control guards, chưa mặc định qua normalized-empty check. Các graph routes chạy với FakeRetrieval; NO_MATCH không phải kết quả truy vấn corpus thật. Không đổi nhãn các giá trị thành OBSERVED nếu chỉ suy ra từ code.

## Evidence và giới hạn phép kiểm

120 tests pass,0 failed/skipped,2.23s theo JUnit;52 diagnostic cases là tập riêng, không phải52 tests mới hoặc thêm vào120. Initial42 JSON là subset của complete52; không cộng thành94.17 detailed traces là lựa chọn từ52, không phải17 runs độc lập mới. Source-level line visits giúp kiểm nhánh quan trọng, không chứng minh100% branch coverage.

Không có live Supabase query, model download, paid inference, benchmark semantic accuracy hoặc production latency trong task này. Không suy từ offline fixtures ra database production readiness. Task0–2 docs vắng trong target; chỉ Task3–5 được dùng làm historical support.

## Các phát biểu bị cấm vì vượt evidence

- Query dùng E5/LLM, tự gọi Supabase hoặc kiểm chứng citation.
- Query paraphrase bằng nghĩa, tự thêm luật liên quan hoặc hiểu đầy đủ bối cảnh.
- Domain match là bảo đảm pháp lý; confidence là field hiện có.
- temporal_scope là trusted date hoặc resolved effective interval.
- Clarification không có subqueries; optional nullable field luôn có default.
- Tất cả duplicates đã được loại; min_length luôn ngăn whitespace-only.
- Mọi graph lỗi biến thành final EXECUTION_FAILED state hoặc framework tự tạo persistent checkpoint.
- HTTP422 đã được implement trong current Query API; target chat route còn stub.
-120 tests chứng minh mọi câu hỏi pháp luật chính xác hoặc tất cả integration production đã được đo.

## Điểm cần hỏi lại trước task thay đổi hành vi

Xác định policy cho punctuation/invisible-only và tab-only clauses, supported time formats/resolution, ambiguity criteria, dedup/context preservation, strict/schema versioning, actual API contract và semantic benchmark. Xem15 để phân biệt gaps với hành vi đã xác minh. Không tự sửa các giới hạn khi soạn guide.
