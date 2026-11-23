# Temporal extraction và calendar validation

Nguồn [Query agent.py,49–62](../../../src/applications/tillegal/agents/query/agent.py). Regex thực tế ở52:

```python
r"(?<![/\w])(?:\d{1,2}/\d{1,2}/\d{4}|(?:19|20)\d{2}|hiện nay|hiện hành)(?![/\w])", text, re.I
```

## Format và điều kiện

| Thành phần | Hành vi chính xác | Ví dụ OBSERVED |
|---|---|---|
|Ngày đầy đủ |1–2 digits /1–2 digits /4 digits,không whitespace quanh slash |29/02/2024 giữ nguyên;1/1/2024 trong unit test |
|Year-only |19xx hoặc20xx,không mọi năm4 digits |1999/2024 được lấy;2100 không được lấy riêng |
|Relative symbolic |hiện nay hoặc hiện hành,re.I |HIỆN NAY được giữ nguyên casing |
|Boundary |Không có slash/word character ngay trước/sau match |45/2019/QH14 không trích2019 |
|Partial |Không có parser day/month hoặc month/year |29/02,02/2024 vẫn trong query text,scope rỗng |
|Format khác |Chưa parser ISO/dot-date bằng calendar |2024-02-29 có thể trích year2024,không xác nhận cả ISO date |
|Relative khác |Không resolve hoặc tự đọc reference date |ngày mai,năm tới chưa được hỗ trợ |

`\w` và `\d` theo Python Unicode regex,không mặc định chỉ ASCII. Full date branch lấy4 digits rồi int/date; riêng year-only branch giới hạn19/20. Không trim hoặc normalize chuỗi mention thành ISO date trong output;1/1/2024 khác format01/01/2024 nhưng có thể cùng calendar day.

## Processing từng bước

1. dates=[] và invalid_date=False.
2. re.finditer duyệt matches theo vị trí text. mention=match.group() giữ matched string.
3. Nếu mention có slash,day/month/year=map(int,...). `date(year,month,day)` kiểm Gregorian calendar,không phải date.today(). Không tạo ngày tham chiếu.
4. Nếu date constructor raise ValueError,đặt invalid_date=True và continue;mention đó không append dates.
5. Ngày hợp lệ,year-only hoặc symbolic expression append dates. Không dedup/sort lại;multiple mentions giữ order,lặp giữ lặp.
6. Sau rules ambiguity,invalid_date=True ghi đè clarification thành message kiểm ngày ở72–73.

Leap-year tests hiện có kiểm2000 và2024 hợp lệ,1900/2023 không hợp lệ;calendar loại31/04,day0,month13. Diagnostic 29/02/2024 trả đúng chuỗi trong scope;31/02/2024 scope rỗng và clarification. Với ngày sai cùng năm2020,scope vẫn giữ2020 nhưng graph vẫn hỏi lại vì flag có bất kỳ ngày sai.

## Bốn khái niệm phải phân biệt

| Khái niệm | Owner | Representation | Ý nghĩa/giới hạn |
|---|---|---|---|
|Ngày trong user text |Caller/question |Raw substring |Có thể sai hoặc không rõ;original giữ nguyên |
|temporal_scope |Query Agent |list[str] matches đã calendar-check cho full slash date |Không time range/context resolver;year/symbolic vẫn strings |
|as_of_date |Trusted SearchOptions → RetrievalRequest |datetime.date |Application cấp explicit;không bị Query ghi đè theo temporal_scope |
|Reported eligibility downstream |RetrievalService._check_eligibility |So policy và recorded effective_from/effective_to với as_of_date |Không chứng minh legal validity bên ngoài hoặc applicability |

Sources downstream chỉ trong boundary cần biết: [Search38–44](../../../src/applications/tillegal/agents/search/agent.py),[RetrievalRequest](../../../src/applications/tillegal/retrieval/contracts.py),[Service._check_eligibility](../../../src/application/services/retrieval_service.py). Nó reject recorded effective_to<effective_from,ngoài inclusive range hoặc policy không cho phép. Source date None có thể được giữ cùng warnings;không tự coi là xác minh hiệu lực.

## Multi-rule/unsupported cases

ISO diagnostic lấy2024 nhưng không parse29/02 phần còn lại;không trình bày output đó như validated ISO date. Duplicate years trả[2024,2024] dạng strings. Mốc thời gian không được gắn riêng cho từng subquery:scope global cho cả plan. Câu có nhiều dates chưa xác định quan hệ trước/sau,từ/đến hoặc ngày có áp dụng cho vụ việc.

QueryPlan schema chỉ yêu cầu list[str]. Probe manually constructing plan với scope[31/02/2024] vẫn được accept;calendar rule thuộc understand,không phải validator của model. Caller bypass entrypoint không có same semantic guarantees. Đây là limitation đã quan sát,không sửa trong Task6a.
