# Hướng dẫn học Query Agent và Search Agent

> Cập nhật Gemini ngày 23/11/2026: adapter và kiểm chứng live đã có. Xem [GEMINI.md](GEMINI.md). Các đoạn dưới đây nói “chưa có provider/adapter” mô tả snapshot redesign trước bước kết nối Gemini; không còn là trạng thái tích hợp mới nhất.

Tài liệu mô tả code đã triển khai trong `D:/DOWNLOAD/tillegal-ai/tillegal-ai-main`, ngày 23/11/2026. Ví dụ không phải tư vấn pháp luật. Không có LLM hoặc database thật được gọi trong kiểm thử.

## 1. Hai agent chịu trách nhiệm gì?

Query chuyển lời người dùng thành mục tiêu tìm kiếm. Search thực hiện các mục tiêu đó, giữ nguồn và tổ chức kết quả. RetrievalService chịu trách nhiệm chọn phương pháp tìm kiếm, kiểm tra index, lấy chunk, hydrate nguồn và giữ ý nghĩa điểm số. Việc đánh giá bằng chứng đủ để kết luận pháp lý hay chưa thuộc thành phần khác, chưa triển khai trong thay đổi này.

Query cũ không hoàn toàn yếu: nó đã giữ nguyên câu hỏi, chặn input lỗi, chuẩn hóa Unicode và kiểm tra ngày. Search cũ cũng đã giữ nguyên response, lỗi có phân loại và metadata nguồn. Điều thiếu được xác minh là phân tích vấn đề pháp lý và lớp tổng hợp bằng chứng; không nên mô tả nhầm rằng hệ thống cũ không có provenance.

Với câu “Tôi ký hợp đồng lao động 2 năm, mới làm được 6 tháng nhưng muốn nghỉ việc. Tôi có phải báo trước không và có phải bồi thường không?”, chỉ tách tại dấu hỏi thường giữ nguyên cả đoạn thành một mục tiêu. Cần tìm riêng nghĩa vụ báo trước và hệ quả/bồi thường, nhưng vẫn gắn cả hai với bối cảnh hợp đồng người dùng đã nêu. Việc tìm “trái pháp luật”, “miễn báo trước”, “chi phí đào tạo” chỉ là hướng tìm các trường hợp có thể liên quan, không khẳng định người dùng vi phạm hoặc đã có thỏa thuận đào tạo.

## 2. Vì sao chọn hybrid?

Rules phù hợp cho kiểm tra dữ liệu và hành vi có thể kiểm chứng chính xác. Rules không đủ để hiểu mọi tình huống đa lĩnh vực, phủ định, đại từ và vấn đề ngầm. Một LLM có khả năng tiếng Việt có thể phân tích những điều đó tốt hơn, nhưng trả JSON đúng cấu trúc không đồng nghĩa với hiểu đúng pháp luật.

Vì vậy có hai đường chạy được ghi nhãn rõ:

1. `understand(question)` đồng bộ: offline, deterministic. Giữ quy tắc hiện hữu, bổ sung nhận diện tra cứu Điều/Khoản, gộp mục tiêu trùng và planner hẹp cho nghỉ việc theo hợp đồng lao động. Chỉ planner này thêm facts/issues/missing_information; câu hỏi ngoài phạm vi vẫn sử dụng cách tách hiện hữu. Không quảng bá rules như khả năng hiểu pháp luật tổng quát.
2. `SemanticQueryAgent.understand(question)` bất đồng bộ: kiểm tra deterministic trước; với câu hỏi thường đủ rõ, gọi một lần cổng model do ứng dụng truyền vào. Validation kết quả trước khi tạo QueryPlan. Không tự retry, không lặp suy luận, không âm thầm dùng rules khi gọi model thất bại.

`llm_gateway.py` và adapter LiteLLM dùng chung hiện chỉ có docstring. Vì vậy không tự chọn một nhà cung cấp, không gắn SDK riêng trong agent. `StructuredCompletion` là integration boundary đã có thể kiểm thử. Ứng dụng phải cung cấp adapter và model cụ thể; khả năng tiếng Việt, JSON/schema và chất lượng cần được đánh giá trước khi chọn model production. Chuỗi `fixture/structured-model` trong test là tên giả.

## 3. Đọc code theo thứ tự nào?

| Thứ tự | File / hàm | Input → output |
|---|---|---|
| 1 | `agents/query/agent.py::understand` | `str` → dict QueryPlan; input lỗi → QueryInputError |
| 2 | `agents/query/schemas.py::SemanticAnalysis` | JSON model → schema chặt: facts/issues/missing/time/clarification |
| 3 | `agents/query/prompts.py::SYSTEM_PROMPT` | Chỉ dẫn phân tích, không trả lời hoặc tạo bằng chứng |
| 4 | `agents/query/semantic.py::SemanticQueryAgent.understand` | question + injected completion → QueryPlan có `analysis_method=llm`, hoặc QueryAnalysisError |
| 5 | `src/query_search_bootstrap.py::QuerySearch.search` | question → chọn Query được cấu hình → `search(plan, retrieval, options)` |
| 6 | `agents/search/agent.py::search` | plan + trusted SearchOptions + RetrievalService → SearchState |
| 7 | `src/application/services/retrieval_service.py::RetrievalService.search` | RetrievalRequest → native RetrievalResponse hoặc subtype hybrid/reranked |
| 8 | `agents/search/agent.py::_finish` | Các native response theo vị trí → evidence groups, occurrences, completeness, warnings/errors |

Các đường dẫn `agents/...` trong bảng là tương đối với `src/applications/tillegal/`. `QueryPlan` và `Subquery` vẫn ở `query/agent.py` để giữ tương thích các import cũ. File `query/schemas.py` chứa schema ngữ nghĩa mới; `search/schemas.py` chứa schema tổng hợp bằng chứng.

Graph có sẵn ở `graphs/legal_qa.py` vẫn gọi `understand` đồng bộ. Inject `query_agent` vào `QuerySearch` chỉ ảnh hưởng lời gọi trực tiếp `QuerySearch.search`; không bật LLM cho graph. Đây là giới hạn được giữ có chủ đích để không sửa orchestration. Handoff hiện chỉ giữ native responses; lớp evidence tổng hợp nằm trong `search_result` và kết quả trực tiếp.

## 4. Query hiểu và lập kế hoạch như thế nào?

### Đường offline

Input phải là chuỗi 1–10.000 ký tự, không rỗng sau trim, không chứa control/surrogate bị cấm. `original` luôn là đúng chuỗi nhận vào, kể cả khoảng trắng và Unicode NFD. Phân tích dùng bản NFC.

Ngày dạng ngày/tháng/năm được kiểm tra bằng `datetime.date`; `31/02/2024` cần hỏi lại. Năm nằm trong số hiệu `45/2019/QH14` không tự thành thời điểm áp dụng. Không suy diễn ngày nghỉ từ “đã làm 6 tháng”.

Các prefix tra cứu nguyên văn cũ và yêu cầu bắt đầu bằng “Tra cứu Điều 35…” hoặc “Tìm khoản 2…” tạo `quote_lookup`. Nội dung trích dẫn vẫn phải qua RetrievalService; prefix này không xác nhận điều luật tồn tại. Những câu chứa ngữ cảnh “tôi có phải…” không được biến thành exact lookup chỉ vì có nhắc điều luật. Nhận diện vẫn là heuristic, không bao phủ mọi cách diễn đạt.

Planner nghỉ việc chỉ xử lý đoạn hỏi đơn có hợp đồng lao động và ngữ cảnh “tôi … muốn/xin nghỉ”; bỏ qua các dấu hiệu phủ định, bị sa thải/bị chấm dứt. Với nhiều phần hỏi, giữ decomposition cũ để không làm mất mục tiêu khác. Planner trích chính xác các span như “hợp đồng lao động 2 năm”, “mới làm được 6 tháng”, “muốn nghỉ việc”. Nó tạo hai truy vấn: báo trước/miễn báo trước và bồi thường/đào tạo. Mỗi truy vấn giữ bối cảnh trích được. Câu hỏi về lý do/ngày nghỉ và thỏa thuận đào tạo được để ở `missing_information`, không chuyển thành sự kiện.

### Đường model

`SemanticQueryAgent` gọi validation offline trước. Câu cần clarification theo rules hoặc lookup nguyên văn không gọi model và vẫn mang nhãn `deterministic`. Câu thường gọi `complete(model=..., system=..., user=..., schema=...)` trong deadline mặc định 15 giây. `user` chứa JSON `{"question": ...}`, prompt coi nội dung người dùng là dữ liệu.

Kết quả phải là JSON object, tối đa 32.000 ký tự. Schema cấm extra fields; tối đa 12 facts, bốn issues, tám missing-information và 12 temporal mentions. Mỗi issue có nhãn và `search_query`; planner giữ tối đa bốn truy vấn khác nhau.

Các kiểm tra quan trọng:

- `fact.text == fact.source_quote` và quote phải có trong câu hỏi NFC. Không chấp nhận “hợp đồng không xác định thời hạn” khi người dùng nêu “2 năm”.
- Thời gian phải xuất hiện nguyên văn ngoài số hiệu văn bản. “2019” chỉ nằm trong `45/2019/QH14` bị từ chối khi model dùng làm mốc áp dụng.
- Không cho model đổi câu thường thành lookup nguyên văn.
- Mẫu Điều/Khoản/điểm hoặc số hiệu luật do model thêm phải có trong câu hỏi. Các token số trong issue/truy vấn/câu hỏi làm rõ cũng phải có trong câu hỏi. Điều này chặn ví dụ tự thêm “30 ngày” hoặc “hợp đồng 3 năm”.
- Nếu model không tuân thủ: `QUERY_ANALYSIS_INVALID_RESPONSE`; timeout: `QUERY_ANALYSIS_TIMEOUT`; lỗi adapter: `QUERY_ANALYSIS_PROVIDER_ERROR`. Không lộ nội dung lỗi upstream và không báo thành công giả.

Đây là guard bảo thủ, không chứng minh model không bịa bằng chữ hoặc hiểu đúng phủ định. Ví dụ số viết bằng chữ không được bảo đảm bởi guard token số. `facts` là các span người dùng cung cấp, không phải sự thật đã xác minh bên ngoài.

## 5. Schema đầu ra có ý nghĩa gì?

`QueryPlan` giữ sáu trường cũ: `original`, `intent`, `domain`, `temporal_scope`, `subqueries`, `clarification`. Các trường thêm có default để plan cũ còn đọc được: `analysis_method`, `analysis_model`, `facts`, `issues`, `missing_information`.

- `domain` hiện chỉ có `labour` hoặc `unknown`, chưa phải bộ phân loại toàn bộ ngành luật.
- `temporal_scope` ghi nhận cách diễn đạt, không phải filter ngày được tự động áp dụng.
- `clarification` khác `missing_information`: clarification khiến Search không gọi Retrieval; missing_information cho phép tìm quy định chung trước.
- `issues` là nhãn vấn đề để người đọc hiểu; `subqueries[i].text` mới là nội dung Search thực thi. Các issue có cùng objective có thể dùng chung truy vấn.

`SearchOptions` vẫn yêu cầu ứng dụng đưa rõ `mode`, `top_k`, `as_of_date`, `allowed_usage_policies`. Mode gồm bm25/dense/hybrid; rerank được cấu hình trong RetrievalService/hybrid, không có mode mới tên rerank trong SearchOptions. Mốc thời gian của người dùng và filter của ứng dụng có thể khác nhau: Search giữ filter được truyền vào và thêm cảnh báo `TEMPORAL_SCOPE_REQUIRES_CALLER_DATE_REVIEW` nếu plan có mốc thời gian. Chưa tự giải quyết xung đột thời gian.

`SearchState` giữ `plan`, `requests`, `responses`, `status` và thêm:

| Trường | Ý nghĩa |
|---|---|
| `evidence` | Các `AggregatedEvidence`: payload nguồn giữ nguyên + danh sách occurrences |
| `completeness` | `NOT_STARTED`, `COMPLETE`, `PARTIAL`, `FAILED`; chỉ mức hoàn thành thao tác tìm |
| `warnings` | Mã cảnh báo tổng hợp; nội dung/metadata cảnh báo đầy đủ vẫn trong native response |
| `errors` | Các RetrievalErrorDetail có phân loại |
| `skipped_subqueries` | Chỉ số bắt đầu từ 0 của truy vấn chưa được thực hiện vì clarification/lỗi trước đó |
| `executed_searches` | Số lời gọi Retrieval thực sự, không đếm lại các slot dùng cache |

`COMPLETE` không có nghĩa chứng cứ đầy đủ về mặt pháp lý. Tất cả truy vấn hoàn tất nhưng không có hit vẫn COMPLETE; `NO_MATCH:i` chỉ rõ mục tiêu không có kết quả.

## 6. Search gọi Retrieval thế nào?

Search validate plan/options, kiểm tra deadline hữu hạn dương (mặc định 45 giây cho mỗi truy vấn), rồi duyệt tối đa bốn subquery. Nó tạo RetrievalRequest với đúng filter từ SearchOptions. Không tự chọn backend, không gọi embedding hay BM25 trực tiếp.

Trong RetrievalService:

1. BM25: `_prepare_sparse_terms` dùng tokenizer hiện hữu → đọc/check index → `_search_sparse` → `_hydrate_sparse_hits` → kiểm tra index sau tìm. Service xác nhận chunk/source/hash và eligibility.
2. Dense: kiểm tra cấu hình/index → query encoder có sẵn → validate vector → dense retriever → `_map_dense_evidence` → kiểm tra index.
3. Hybrid: gọi `search_hybrid` với nhánh BM25 và dense hiện hữu, rồi RRF hiện hữu.
4. Nếu cấu hình rerank bật trên hybrid: gọi `search_reranked` dùng scorer hiện hữu. Native response giữ fusion/reranking metadata. Không sort lại theo RRF raw_score vì điểm RRF không phản ánh thứ tự sau rerank.

Các hàm, thuật toán, config và schema Retrieval trên không được sửa trong task này. Unit/integration tests dùng ports giả không chứng minh chất lượng retrieval trên corpus thật.

## 7. Khử trùng lặp và provenance

Cache Search có phạm vi đúng một lần gọi, khóa bằng nội dung query **giống hệt**. Hai query cùng chuỗi chỉ gọi Retrieval một lần nhưng vẫn giữ hai slot requests/responses để handoff cũ khớp plan theo vị trí. Không gộp hai câu chỉ vì có vẻ đồng nghĩa; không đổi case hoặc khoảng trắng trong exact lookup.

`_finish` tạo khóa từ toàn bộ payload evidence, chỉ bỏ `rank`, `raw_score`, `score_kind`, `retrieval_method` vì chúng là thuộc tính của mỗi lần tìm. Khóa còn chunk ID, source ID, structure ID, snapshot ID, hash, nội dung, ngày hiệu lực, policy và metadata. Khác bất kỳ dữ liệu nguồn nào thì không gộp. Metadata có thứ tự khác có thể khiến không gộp; đây là lựa chọn bảo thủ, không làm mất nguồn.

Với mỗi bằng chứng trùng an toàn, `occurrences` giữ query, subquery_index, response_index, request_id, rank và score_kind/raw_score cho từng lần xuất hiện. Payload đại diện là lần xuất hiện đầu tiên; rank của payload này không phải global rank. Không cộng/so sánh BM25 với cosine hoặc RRF. Điểm rerank vẫn đọc trong native response qua response_index.

Cùng chunk ID nhưng payload khác được giữ thành hai nhóm và có `EVIDENCE_IDENTITY_CONFLICT`; không tự chọn phiên bản “đúng”. Hai source_document_id khác nhau không bị gộp chỉ vì nội dung giống nhau.

## 8. Lỗi truyền đi như thế nào?

Giữ fail-fast vì `JudgeHandoff.validate_context` hiện bắt buộc dừng tại lỗi đầu tiên. Thay chính sách sẽ cần sửa contract ngoài phạm vi. Search vẫn trả toàn bộ response đã nhận và evidence có trước lỗi, đồng thời trả `status=FAILED`, `SEARCH_INCOMPLETE`, errors và skipped indices.

Ví dụ ba query A/B/C: A có kết quả, B lỗi database, C chưa chạy. Kết quả: responses=[A,B], completeness=PARTIAL, skipped_subqueries=[2]. Nếu A là NO_MATCH và B lỗi thì vẫn PARTIAL vì một thao tác đã hoàn tất; evidence có thể rỗng. Nếu ngay A lỗi, completeness=FAILED. Không có “COMPLETED” giả khi gặp lỗi.

RetrievalService đã chuyển nhiều lỗi phụ thuộc thành native FAILED. Search còn chuyển `RetrievalServiceError` thoát ra và deadline riêng thành response FAILED an toàn. Với deadline này, selected_index_name=`unavailable`: không bịa tên index đã đọc. Hybrid/rerank native response bình thường được giữ nguyên subtype.

RuntimeError bất ngờ và cancellation tiếp tục truyền lên runtime; không nuốt lỗi lập trình thành NO_MATCH. Khi caller đặt deadline ngoài ngắn hơn deadline Search, cancellation/timeout ngoài vẫn được runtime xử lý. Không retry hoặc tự đổi backend.

## 9. Ví dụ đầy đủ và cách kiểm tra

Đọc [EXAMPLE.md](EXAMPLE.md) để xem output thật của code trên fixture được gắn nhãn tổng hợp. Đọc [TEST_RESULTS.md](TEST_RESULTS.md) để biết lệnh, số test và giới hạn mỗi lần kiểm tra. [AUDIT.md](AUDIT.md) giữ hiện trạng trước sửa với file/function và khoảng dòng gốc.

Để gọi semantic boundary trong ứng dụng, mẫu cấu hình sau **chưa phải live adapter**:

```python
agent = SemanticQueryAgent(
    complete=application_gateway_adapter,  # ứng dụng phải cung cấp async adapter
    model=configured_provider_model,
    timeout_seconds=15,
)
pipeline = QuerySearch(retrieval_service, explicit_search_options, query_agent=agent)
result = await pipeline.search(question)
```

Adapter nhận keyword-only model/system/user/schema và trả chuỗi JSON; provider credentials nằm trong cấu hình bảo mật của ứng dụng. Agent không cần biết SDK. Không dùng ví dụ này để tuyên bố đã chạy model production.

Các test đáng đọc: `test_offline_complex_and_implicit_issues_preserve_context`, `test_semantic_json_contract_and_original`, `test_reject_unsupported_or_invalid_semantics`, `test_partial_failure_retains_evidence_and_explicit_skipped_queries`, `test_conflicting_legal_versions_never_merge`, và `test_mocked_semantic_query_to_real_service_execution` trong `tests/unit/applications/tillegal/test_query_search_semantic.py`.

## 10. Giới hạn và phần chưa làm

Đã triển khai: planner offline hẹp, cổng phân tích model có validation/deadline/lỗi rõ, injection tùy chọn vào QuerySearch trực tiếp, tổng hợp bằng chứng/provenance, cache exact request và completeness. Không có provider thật được nối; không sửa graph để bật semantic model. Không triển khai Judge, Summary, Answer, Verification hoặc đánh giá legal sufficiency.

Rules cho lĩnh vực khác vẫn đơn giản; thiếu classifier đa ngành và xử lý tổng quát phủ định/chủ thể. Câu vượt bốn phần hoặc mơ hồ theo guard cũ vẫn hỏi lại trước khi gọi model. Mốc tương đối chưa chuyển thành ngày. Facts/queries model tạo vẫn cần đánh giá grounding/recall trên tập câu hỏi tiếng Việt và corpus được duyệt. Guard citation/numeric không thay thế verification, không xác nhận hiệu lực hay tồn tại điều luật.

Việc chọn provider/model, làm live adapter qua gateway dùng chung và bật semantic node trong graph là công việc tiếp theo cần thực hiện trong scope riêng. Các bước đó là đề xuất tương lai, không phải tính năng đã hoàn tất ở đây.
