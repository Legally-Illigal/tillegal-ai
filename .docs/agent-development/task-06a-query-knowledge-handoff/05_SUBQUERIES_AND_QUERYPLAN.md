# Subqueries và QueryPlan contract

Nguồn [agent.py,15–26/40–48/74–95](../../../src/applications/tillegal/agents/query/agent.py).

### Subquery

| Field | Type thật | Required/default | Constraint |
|---|---|---|---|
| text | `str` | Required,không default | `Field(min_length=1, max_length=10000)` |
| purpose | `Literal['lookup', 'question_part', 'topic']` | Required,không default | `Không custom constraint` |

### QueryPlan

| Field | Type thật | Required/default | Constraint |
|---|---|---|---|
| original | `str` | Required,không default | `Field(min_length=1, max_length=10000)` |
| intent | `Literal['quote_lookup', 'legal_question']` | Required,không default | `Không custom constraint` |
| domain | `Literal['labour', 'unknown']` | Required,không default | `Không custom constraint` |
| temporal_scope | `list[str]` | Required,không default | `Không custom constraint` |
| subqueries | `list[Subquery]` | Required,không default | `Field(min_length=1, max_length=4)` |
| clarification | `str \| None` | Required,không default | `Không custom constraint` |

clarification có type str|None nhưng vẫn required khi dựng model vì không default. None là giá trị hợp lệ,không phải cho phép thiếu key. Pydantic config QueryPlan hiện{}:không extra-forbid/strict/frozen custom. Diagnostic extra confidence bị bỏ ở parsed output,không tạo confidence capability. Unsupported intent literal bị reject.

## Generation rules

| Rule/line | Điều kiện/input | Subquery tạo | Giải thích field và consumer |
|---|---|---|---|
|42 |Split `;`,`?`,LF hoặc guarded “và” |parts list[str] |Chưa Subquery;strip edges ` ?;`,filter parts rỗng theo cùng phép strip |
|47–48/74 |quote_only true:Trích dẫn: đối thoại |Subquery(text='đối thoại',purpose='lookup') |Topic bỏ prefix;Search chỉ lấy text |
|48/74 |Không quote_only |Mỗi parts[:4] với purpose question_part |Giữ order từng phần;không intent model riêng mỗi phần |
|48 |parts rỗng nhưng text không rỗng |Fallback[text],purpose question_part |? ; quan sát tạo1 query punctuation dù không có meaningful words |
|75–87 |Không lookup,còn slot,topic phrase chưa trong seen |Subquery(text=match.group(),purpose='topic') |Phrase có sẵn trong text,thêm sau base queries |

Split regex chỉ tách “và” nếu ngay sau là khi nào,ai+space,bao nhiêu,điều kiện hoặc thủ tục,re.I. Đây là heuristic decomposition,có thể tách điều kiện khỏi chủ thể. “Nghỉ phép và tiền lương...” không split ở và;whole question làm base rồi topic phrases được bổ sung.

Topic whitelist đầy đủ: đối thoại định kỳ;nghỉ hằng năm;nghỉ phép;thời giờ làm việc;chấm dứt hợp đồng lao động;tiền lương;làm thêm giờ. Diagnostic complete đã quan sát matches cả7. Nó không đồng nhất với4 domain keywords.

## Ordering/dedup/limit

Base queries trước,theo vị trí clauses. Topic extras sau,theo re.finditer order trong original normalized text. `seen` ban đầu chứa casefold của mọi base query;topic chỉ thêm khi len(subqueries)<4 và casefold chưa có,sau đó cập nhật seen. Nó không xóa duplicate base parts. OBSERVED nghỉ phép; nghỉ phép tạo2 question_part giống nhau. Lookup bỏ qua topic extraction hoàn toàn.

Có tối đa4 Subquery trong accepted plan. Hơn4 parts vẫn giữ4 phần đầu trong plan nhưng clarification yêu cầu chia câu hỏi;graph bỏ Search toàn lượt,không silently search4 rồi bỏ phần5. Khi base đã đủ4,không còn topic slots. Repeated topic matches được ghi trong diagnostic nhưng không nhất thiết được thêm vào output vì dedup/cap.

## Zero subqueries chính xác ở đâu?

Accepted QueryPlan luôn1–4 subqueries. Invalid input raise và không có plan;không trả plan với[]. Clarification vẫn có subqueries;graph skip Search hoặc Search trực tiếp trả empty requests/responses. Zero retrieval requests khác zero plan subqueries. Empty subqueries trong externally supplied plan bị receiving Search model_validate reject,ngay cả clarification truthy.

## Six-field semantics đầy đủ

| Field | Origin/logic | Meaning/consumer | Example và serialization |
|---|---|---|---|
|original |constructor89:question |Exact caller argument,graph/handoff |Giữ prefix/whitespace/NFD trong dict/JSON |
|intent |90 từ quote_only |Global lookup hoặc fallback question;Search không routing theo field |quote_lookup làstr,JSON string |
|domain |91 regex4 keywords |Heuristic global;Search không derive policy |labour/unknown strings |
|temporal_scope |92 từ dates |Global mentions,không resolve as_of_date |[] hoặc['2024'];JSON array |
|subqueries |94 từ list models |Source text cho request.query |list of dicts sau model_dump |
|clarification |93 từ rules |Message hoặcNone;graph routing |JSON null khiNone |

## Các representation khác nhau

1. `Subquery(...)` và `QueryPlan(...)` nội bộ là Pydantic objects;đây là schemas,không ML models.
2. understand gọi model_dump() không arguments,trả dict với nested lists/dicts;chưa phải JSON string. Hàm không trả QueryPlan instance ra caller.
3. Query node đặt cùng returned dict vào state.plan. Không lưu normalized text riêng trong public schema;chỉ original và subquery strings.
4. Search nhận raw plan dict,revalidate thành parsed QueryPlan để đọc clarification/subqueries. SearchState.plan vẫn là raw input dict;tests assert identity.
5. Handoff typed QueryPlan là một validation representation khác;JSON generation thuộc handoff/diagnostic,không tự chạy trong understand.

Nguồn Search [38–56](../../../src/applications/tillegal/agents/search/agent.py),handoff [legal_qa_state.py](../../../src/applications/tillegal/state/legal_qa_state.py). Unknown extra keys nếu caller tự thêm có thể bị QueryPlan parsed model ignore,raw SearchState.plan vẫn giữ;không hứa arbitrary extras round-trip như public contract. Normal entrypoint chỉ tạo đúng6 keys.

Python output thật và JSON cho từng case có ở08;`None` Python trở thành `null` JSON. Có thể gọi QueryPlan.model_validate(output).model_dump() round-trip schema;không biến model validation thành semantic verification.
