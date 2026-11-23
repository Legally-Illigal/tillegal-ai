# Clarification,error và stop conditions

Nguồn [agent.py64–73](../../../src/applications/tillegal/agents/query/agent.py),[graph24–37](../../../src/applications/tillegal/graphs/legal_qa.py),[Search38–44](../../../src/applications/tillegal/agents/search/agent.py).

## Message priority

1. len(parts)>4 → “Vui lòng chia câu hỏi thành tối đa bốn phần.”
2. elif:prefix có nhưng topic rỗng,hoặc len(text.split())<2,hoặc casefold().strip(' ?') bằng có được không/như vậy đúng không/trường hợp này → “Bạn cần tra cứu quy định hoặc tình huống cụ thể nào?”
3. Sau if/elif,bất kỳ invalid_date=True ghi đè message → “Ngày được nêu không hợp lệ. Bạn vui lòng kiểm tra lại ngày, tháng và năm.”

Không có model-generated question,không tự hỏi riêng chủ thể/số tiền/ngày nếu regex không xác định thiếu. Câu rõ về mặt pháp lý vẫn có thể bị rule một-word yêu cầu làm rõ. Câu thiếu context nhưng không match fixed patterns có thể đi Search.

| Ví dụ OBSERVED | Trigger | Plan/Search behavior |
|---|---|---|
|Có được không? |Exact fixed phrase |Plan1 subquery,clarification,Search skip |
|Như vậy đúng không? |Exact fixed phrase |Same message,zero calls |
|Trường hợp này |Exact fixed phrase |Same message,zero calls |
|thuế |<2 whitespace tokens |Clarification,dù từ có ý nghĩa pháp lý |
|Trích dẫn: |Prefix có,topic rỗng |legal_question,purpose question_part,clarification |
|5 clauses |len(parts)>4 |Plan giữ4 nhưng skip toàn Search |
|5 clauses có31/02/2024 |Too-many và invalid date |Date message thắng |
|Trích dẫn: tiền lương ngày31/02/2024 |Lookup+domain+invalid date |Intent lookup vẫn giữ,clarification chặn Search |

Input có space trước31 trong cases thực;exact strings/final JSON ở08 và evidence. Câu có punctuation ? ; là counterexample:2 whitespace tokens,parts rỗng,không match ambiguity,plan fallback1 punctuation subquery và fake retrieval được gọi. Không gọi hệ này là general ambiguity detector.

## Error matrix

| Trigger | Owner/lines | Exception/code | Plan? | Graph/Search outcome | Evidence |
|---|---|---|---|---|---|
|Empty string |understand33–34 |QueryInputError/LENGTH |Không |No final state,lifecycle failure,Search không chạy |test_length;diag empty |
|Whitespace-only |37–39 |QueryInputError/EMPTY |Không |Exception trước Search |test_blank;diag whitespace |
|Non-string |31–32 |QueryInputError/TYPE |Không |Exception |test_invalid_type;diag non_string |
|>10000 raw codepoints |33–34 |QueryInputError/LENGTH |Không |Exception |test_length;diag length |
|Cc/Cs không allowlisted |35–36 |QueryInputError/CHARACTER |Không |Exception |test_characters;diag control/surrogate |
|Invalid date |58–61,72–73 |Không exception ra caller;clarification |Có |CLARIFICATION_REQUIRED,zero calls |test_invalid_date;diag invalid_date/override |
|Unknown user intent/domain |90–91 fallback |Không unsupported-request code |Có nếu input pass |Có thể Search |Rule source/diag domain_miss |
|Unsupported model intent literal |QueryPlan Literal |Pydantic ValidationError |Không parsed model |Direct boundary reject |schema_probe unsupported_intent |
|Clarification known pattern |64–73 |Không raise |Có,1–4 queries |Graph END trước Search node |Graph clarification test;52 diagnostics |
|Internal Query exception |understand/node invocation |Underlying exception |Không valid output |Executor FAILED,propagate |test_query_execution_failure_propagates_without_handoff |
|Missing state.question |query node25 |KeyError |Không |Raw node fails;public wrapper cấp key |boundary missing_query_field |
|Missing state.clarification |route_query37 |KeyError |N/A |Không fallback route tự động |boundary missing_route_field |
|Malformed plan/empty subqueries |Search40 |Pydantic ValidationError |Raw dict có nhưng không parsed plan |Zero service calls |empty_subqueries boundary;existing tests |
|Tab-only middle part |Query41 vs Search request validation |Query returns plan;Search raises ValidationError(query) |Có |Search node đã vào nhưng zero retrieval calls,no final graph state |diag tab_part |
|Valid input không matches |Service outcome sau Search |NO_MATCH response,không exception |Có |Graph NO_MATCH,không clarification |FakeRetrieval graph tests/diagnostics |

Mã đầy đủ ở source là QUERY_INPUT_TYPE,QUERY_INPUT_LENGTH,QUERY_INPUT_CHARACTER,QUERY_INPUT_EMPTY. Schema errors không có project QueryInputError code;không tự gán code mới. Graph status execution failure là out-of-band exception/lifecycle,không emit một final state.status EXECUTION_FAILED.

Zero calls khi clarification được bảo đảm bởi graph conditional edge và thêm guard ở receiving Search;tests là evidence thực thi của hai đường đó. Pydantic validate plan diễn ra trước guard,do đó malformed plan với clarification và subqueries=[] vẫn reject.

## Three outcomes cần phân biệt

Invalid input không trả plan. Clarification trả plan/message nhưng dừng trước Search. No-match chỉ biết sau Search có valid request và service trả empty outcome. Diagnostics dùng fake service luônNO_MATCH cho valid input nên không nói database thực không có luật phù hợp.
