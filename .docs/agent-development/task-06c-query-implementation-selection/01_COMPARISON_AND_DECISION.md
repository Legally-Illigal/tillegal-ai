# Quyết định: publish Implementation A

Ngày 22/11/2026, Asia/Saigon. **Chọn duy nhất A làm Query Agent authoritative cho PR Query/Search hiện tại.** Không merge interface B, không tạo implementation thứ ba và không xóa WIP.

## Phạm vi và nguồn

- **A:** `D:/DOWNLOAD/tillegal-ai/tillegal-ai-main`, source export không có Git metadata. Public entrypoint `understand(question: str) -> dict`.
- **B:** `D:/DOWNLOAD/tillegal-ai/retrieval-publish`, branch `feature/retrieval-bm25-dense-hybrid`, HEAD `89a38931401d51ba8205bf5faf948c66a13adf3f`. Query files là local modifications/untracked tests, không phải implementation đã có trong HEAD.
- Official main được đọc bằng ls-remote, không fetch: `1158a6a40e85395bb91bed90f0d7b1967bbf8deb`. Cached origin/main của B trùng SHA này.

Dự án chỉ có một người phụ trách Query Agent theo thông tin người dùng. Không có cơ sở coi B là công việc của developer khác. Lý do bảo toàn B là giữ WIP của chính dự án và tránh mất lịch sử thử nghiệm, không phải suy đoán ownership.

B là **deterministic Query core đã có code và unit tests, nhưng WIP ở mức tích hợp**. Các functions thực tế là normalize_query12–14, extract_literal_references17–22, validate_plan_against_input25–39 và QueryAgent.plan51–130. Không gọi nó là pseudocode. Mục tiêu phù hợp với deterministic-core scope trong `.docs/development/query-search-design/06_implementation_roadmap.md`, phần “Very next task”. Tài liệu này cùng02_query_agent_design.md còn đề xuất assisted planning/Search sau đó; các đề xuất không tự là features đã implement. Không thể suy ra chính xác chat/lệnh/người tạo WIP từ source chưa commit. Những câu “implementation NOT authorized” trong tài liệu cũ là trạng thái lịch sử của tài liệu, không thay instruction audit hiện tại.

## Source legend

| Nhãn | Actual file |
|---|---|
| Aq | [A query/agent.py](../../../src/applications/tillegal/agents/query/agent.py) |
| As | [A search/agent.py](../../../src/applications/tillegal/agents/search/agent.py) |
| Ag | [A graphs/legal_qa.py](../../../src/applications/tillegal/graphs/legal_qa.py) |
| Ah | [A state/legal_qa_state.py](../../../src/applications/tillegal/state/legal_qa_state.py) |
| Ab | [A query_search_bootstrap.py](../../../src/query_search_bootstrap.py) |
| Bq | [B query/agent.py](<D:/DOWNLOAD/tillegal-ai/retrieval-publish/src/applications/tillegal/agents/query/agent.py>) |
| Bs | [B query/schemas.py](<D:/DOWNLOAD/tillegal-ai/retrieval-publish/src/applications/tillegal/agents/query/schemas.py>) |
| At | [A test_query_hardening.py](../../../tests/unit/applications/tillegal/test_query_hardening.py) |
| Ast | [A test_query_search.py](../../../tests/unit/applications/tillegal/test_query_search.py) |
| Amt | [A test_query_search_multimode.py](../../../tests/unit/applications/tillegal/test_query_search_multimode.py) |
| Agt | [A test_query_search_workflow.py](../../../tests/graph/test_query_search_workflow.py) |
| Bt | [B test_agent.py](<D:/DOWNLOAD/tillegal-ai/retrieval-publish/tests/unit/applications/tillegal/agents/query/test_agent.py>) |
| Bct | [B test_contracts.py](<D:/DOWNLOAD/tillegal-ai/retrieval-publish/tests/unit/applications/tillegal/agents/query/test_contracts.py>) |

Ranges dưới đây là actual source hiện tại, có [AST index](evidence/source-symbols.json). Source-derived conclusions được phân biệt với runtime observations ở phần sau.

## Side-by-side comparison: 15 tiêu chí

| Tiêu chí | A: symbol/range và behavior | B: symbol/range và behavior | Tests/evidence, integration impact |
|---|---|---|---|
|1. Input validation |Aq understand31–39: str, raw length1..10000, reject Cc/Cs trừ tab/LF/CR, normalized blank reject |Bs Value.reject_blank_strings13–19, QueryAgentInput114–130: StrictStr, length/ID/context và typed trusted controls; không có guard Cc/Cs tương đương |At test_invalid_type11–13, test_length17–19, test_blank23–25, test_characters29–31; Bct test_invalid_input39–41. Probes NUL/NEL: A reject, B READY; không coi StrictStr là control-character sanitization |
|2. Unicode |Aq 37: NFC + strip; giữ raw original89; không collapse whitespace nội bộ |Bq normalize_query12–14: NFC + Unicode whitespace collapse; giữ original_query61, normalized_query62. Reference extraction109 dùng raw input |At test_unicode_and_original34–42; Bt test_original_normalization_and_literal_origins13–21. Probe NFC có reference, NFD không có reference ở B; không nói toàn bộ literal extraction canonically invariant |
|3. Intent |Aq 45–48, 90: quote_lookup khi prefix/topic/one-part; fallback legal_question |Bq 58–68, 122–128/Bs 175–197: không có intent classifier/field; single original query |At test_contract_and_regressions77–85, lookup probe. B không thay được purpose lookup behavior A; chỉ đổi tên interface không khôi phục rule |
|4. Domain |Aq 91: labour/unknown bằng bốn keyword patterns |Bs 182 defaults domains=(); Bq 122–128 không populate domains |Bt 20 assert domains empty; ordinary probe A labour, B empty. B có field không có nghĩa đã classify legal domain |
|5. Temporal |Aq 49–62, 72–73: regex mentions, datetime.date validate slash-date; invalid date clarification |Bs TemporalContext54–68 validate caller-supplied date/origin; Bq 89–107 kiểm provenance mention membership/unresolved; không parse lịch từ câu hỏi |At test_valid_date46–49, test_invalid_date53–57, test_temporal_semantics73–74; Bt 42–49. Invalid-date probe A clarify, B READY với trusted date hợp lệ. Trusted date khác user mention; A cũng không tự override SearchOptions.as_of_date |
|6. Subqueries |Aq 40–48, 74–87: split và bounded topic extraction; QueryPlan25 yêu cầu1..4 |Bq 127 chỉ tạo q1 original; Bs 203–204 bắt READY deterministic đúng1 query; schema189 có max3 cho contract rộng hơn |Bt 19 assert len1; multipart probe A3 queries, B1. Multi-query/assisted decomposition trong design chưa implement |
|7. Clarification |Aq 64–73: quá4parts, empty lookup, one token, fixed ambiguous phrases, invalid date; As 42–43 vàAg36–37 stop |Bq 89–121: unresolved date, unproven explicit expression, hai fixed dismissal phrases, >20references; queries rỗng theoBs231–236 |Bt 42–49, 79–82; Agt 92–110; cross-pattern probes cho kết quả khác nhau. Cả hai là heuristic, không general ambiguity understanding; B không có graph stop wiring |
|8. QueryPlan |Aq 20–26:6 fields; understand95 model_dump→dict |Bs 175–239:22 fields; Bq 51 trảtyped QueryPlan, extra forbid/frozen từValue21 |Bct 44–50, 64–68; two-way receiving probes reject. B thiếu cả6 keys A yêu cầu, không chỉ khác type class |
|9. Errors |Aq 11–12/31–39: QueryInputError với fixed codes; clarification làplan |Bq 53 có thể ValidationError; 55–56 ValueError cho clock; 69–88 classified FAILED/AgentError cho unsupported/deadline. Bs 24–45 typed errors |At 11–31; Bt 35–39; Bct 39–41. B không convert mọi invalid input thành FAILED. Adopting B cần đổi receiving/error contracts |
|10. Test scope |Existing regression320 cases mới chạy, bao gồm37hardening/12QuerySearch/41multimode/30 graph vàretrieval/framework |Hai independent unit files27 cases mới chạy; test import85–98 không load infrastructure |A JUnit vàB JUnit phía dưới. So sánh scope chứ không dùng320>27 làm tiêu chí chất lượng tuyệt đối |
|11. Search compatibility |As 40 validate A QueryPlan, 44 đọc subquery.text; Ab 20–21 truyềnunderstand output |B Search agent.py chỉ docstring1; B dump không cósubqueries/clarification tương ứng |Ast 31–43, Amt 139–182; probe B_dump_to_A_Search→ValidationError, 0retrieval calls. Cần thay adapter/schema để dùngB, ngoài scope |
|12. LangGraph/handoff |Ag 24–33 gọiunderstand, 36–37 route clarification, 39–54 tạoJudgeHandoff; Ah 27 typedA plan, 44–64 consistency |B graph/legal_qa.py vàstate/legal_qa_state.py đềuplaceholder1; B modulekhông export understand |Agt 62–165, 130–152 round-trip4 profiles. Thay B vào A làm import/call/schema path không tương thích; không tồn tại B graph integration test trong2files đã inspect |
|13. Retrieval compatibility |Ab 24–42 injectservice; As 47 awaitactualRetrievalService; service không bị Query thay thế |B import boundary chỉ schemas và stdlib; Bt 85–98 chủ đích kiểm không importretrieval. Service có trong B checkout nhưngkhông wiredvới B Query |Ast 31–43, Amt 139–182:realservice/fakeports; historicalTask4/5live táchriêng. Không có bằng chứng phải đổiRetrieval để publishA |
|14. Complexity/maintenance |Query module95lines, 3 classes gồmerror/schema, 1 public business function; callershiện có |Queryagent130+schemas239+init6=375lines, 15 classes; 3 module helpers, plan và constructor và clock/UUID injection |AST inventory. Đây là kích thước/phạm vi, không chứng minh class tốt/xấu. Với current requirements, A ít migration surface hơn; B đòi nhiềutrustedinputmodel chưa cóadmissionpath |
|15. Unimplemented/redundant |A không LLM/confidence/legal sufficiency; đúng prototype boundary |Bs 85–103, 160–172, 192–197 cómodelbudget/telemetry/follow-up types; Bq 72–77 refuseassisted/follow-up/ACL; facts/entities/domains đểempty; không provider/token-cost accounting |Bt 35–39, 67–76, 52–64; Bct 64–68. Deadlines có ích, IDs/date/policies phần nào đã ở A runtime/options. Schema rộng/proposal không phải capability đã chạy |

## Runtime comparison mới

[comparison-observations.json](evidence/comparison-observations.json):13 paired synthetic cases +4 B control cases và receiving probes. Không paid model/DB. B được load từ path gốc dưới package alias để tránh module collisions; B unit tests bên dưới chạy riêng CWD B với canonical imports. Alias không sửa/copy implementation.

| Input/case OBSERVED | A | B | Ý nghĩa |
|---|---|---|---|
|Trích dẫn: đối thoại |quote_lookup, lookup text đối thoại |READY, query nguyên prefix |A giữ lookup rule đang tích hợp |
|thuế; nghỉ phép; tiền lương |3subqueries |1original query |B cố ý single-query core |
|Có được không? |Clarification |READY |Fixed ambiguity sets khác nhau |
|Tôi bị cho nghỉ, có đúng không? |Khôngclarification |Clarification, 0 queries |B có một pattern hữu ích A chưa có; không chứng minh B semantic superiority |
|Quy định ngày 31/02/2024 |Date clarification |READY |B trusted temporal context không validate date mention trongtext |
|NUL/NEL trong text |QUERY_INPUT_CHARACTER |READY |Validation contracts khác nhau |
|Khoản 1 Điều 35, NFC/NFD |Queryanalysis NFC ổn định |Reference NFC có, NFD empty |Raw literal extraction của B có Unicode limitation |
|B dump→A Search |N/A |ValidationError, 0 calls |Contract không drop-in |
|A clarification→A Search |CLARIFICATION_REQUIRED, 0 calls |N/A |Current stop condition vẫn hoạt động |

Các input exact, raw outputs vàerrors trongJSON; table rútgọn không thay literal inputs. Không trình bày source-derived graph ImportError consequence như một runtime graph đã cố thay files.

## Tests mới và reproducibility

- **A:**320 passed, 0failed/errors/skipped, pytestconsole4.83s. Có Search actualservice/fakeports, 4 profiles, graph routing, handoff subtype/JSON, timeout/cancel, isolation. [A JUnit](evidence/A-regression.xml).
- **B:**27 passed, 0failed/errors/skipped, 0.66s. Independent core/schema tests; không Search/graph/DB integration. [B JUnit](evidence/B-query-unit.xml).
- Exact commands vàCWD ở[test-results.json](evidence/test-results.json). Cùng Python3.12 environment hiện có, không install dependencies; pyproject A/B giống nhau.
- A live evidence chỉ lịch sử:Task4standaloneBM25/Dense-repeat/Hybrid/rerank; Task5graphBM25. Không chạy Supabase mới; không claim livegraph allmodes.

## Quyết định theo7 criteria

| Criterion | Đánh giá cho release hiện tại |
|---|---|
|Correctness với current requirements |A giữinput/intent/domain/temporal/subqueries/clarification đang được Search sử dụng; B phục vụcontractkhác |
|Verified Search integration |A mới passreceiving/service/graph tests; B dumpbị receiving reject |
|Contract stability |GiữA không đổicallers; B thay6-field contractbằng22-field model |
|Regression results |Cả hai suites đều green trongscope riêng; Acover current component integration boundary |
|Maintainability |A đãcósource handoff/tests; B core có ích nhưngphảibổ sung admission/adapter/graph contracts để dùng |
|Simplicity |Achỉthaystubs vàthêmwrapper/tests; không mangbudget/assistedfuturecontractvào release |
|Retrieval/graph break risk |A không đổialgorithms/contracts Retrieval; B adoption cần migrationkhôngđược yêu cầu |

**Kết luận duy nhất: A là bản nên publish.** Không có source/test evidence cho một lý do đáng kể phải đổi sang B để hoàn thành Query/Search PR hiện tại. Lựa chọn không dựa trên số test lớn hơn hay ưu thế của function so với class; dựa trên behavior phù hợp và receiving contracts đã kiểm chứng.

## B disposition và optional future work

Giữ WIP B nguyên trạng, loại khỏi PR. Có thể học các ý tưởng trong task riêng sau release:literal-reference provenance từ context, explicit admitted request controls, strict schema validation, deadline injection và một sốclarification patterns. Cần tests/benchmark và migration design riêng trước khi thay contract A. B extractionNFD vàcontrol-character acceptance cần được kiểm lại nếu tái sử dụng.

Không cần thêmQueryAgent thứhai hoặcbridge22→6 fields trongtask này. IDs/date/policy không nên bịcopy thành nguồn quyền thứhai cạnh A ExecutionContext/SearchOptions. Model budgets/assisted/follow-up chỉ làpassivecontracts/unsupportedpaths hiện tại, không đưa vào PR như features đã hoàn thành.

Xem [publication manifest](02_PUBLICATION_MANIFEST.md) để biết chính xác files vàcáchcommit antoàn sau khi được phép. Chưa stage/commit/push/worktree/PR hoặc sửa source.
