# Intent và domain: toàn bộ rules hiện hành

Nguồn [Query agent.py,45–48 và88–95](../../../src/applications/tillegal/agents/query/agent.py). Không có intent/domain model học máy hoặc score.

## Intent chỉ có hai nhãn

Prefix regex thật:

```python
r"^(?:trích dẫn|trích nguyên văn|tìm đoạn)\s*[:\s]\s*"
```

Regex ở source dùng single backslash trong raw literal; Markdown hiển thị theo snippet regex. `^` bắt đầu local text đã strip. Cụm đầu khớp re.I. Sau cụm phải có colon hoặc whitespace theo `[:\s]`,không phải optional hoàn toàn. `topic = text[prefix.end():].strip(...)`; `quote_only = bool(topic and len(parts)==1)`.

| Intent | Trigger đầy đủ | Ví dụ OBSERVED | Output chính | Limit |
|---|---|---|---|---|
|quote_lookup |Prefix match,topic không rỗng,đúng1 part |Trích dẫn: đối thoại |1 Subquery lookup,text=đối thoại |Không chứng minh exact citation;prefix + nhiều parts mất lookup intent |
|legal_question |Mọi trường hợp quote_only false |Câu hỏi nghỉ phép thông thường |Question_part và optional topic extras |Fallback không kiểm câu có thực sự là yêu cầu pháp lý |

Ba prefix là alternatives của cùng một rule,một nhãn; không priority giữa các intent models. `re.match` lấy match đầu tại start; không tìm prefix ở giữa câu. Prefix detection phụ thuộc parts đã tạo,không phụ thuộc domain hoặc date.

## Decision table và priority

| Prefix? | Topic rỗng? | len(parts) | quote_only / intent |
|---|---|---|---|
|Không |N/A |Bất kỳ |False/legal_question |
|Có |Có |1 thường gặp |False/legal_question;clarification prefix_empty |
|Có |Không |1 |True/quote_lookup |
|Có |Không |>1 |False/legal_question;parts gốc còn prefix ở first part |

OBSERVED Trích dẫn không có colon/topic: prefix=None,legal_question,không clarification vì2 whitespace tokens. Trích  dẫn: đối thoại có internal extra space:prefix không match. Trích dẫn: đối thoại? nghỉ phép? có prefix nhưng2 parts,nên legal_question. Đây là phrasing sensitivity,không semantic intent ambiguity detector.

Multi-rule trace OBSERVED: Trích dẫn: tiền lương ngày31/02/2024 (input thực có space trước31) đồng thời prefix lookup,domain labour,invalid_date. Output intent vẫn quote_lookup,domain labour;clarification ngày sai quyết định skip Search. Date flag không đổi intent nhưng ghi đè clarification message theo72–73.

## Domain chỉ là binary keyword flag

Rule thật ở91:

```python
re.search(r"lao động|tiền lương|nghỉ phép|làm việc", text, re.I)
```

| Label | Điều kiện | Ví dụ/giới hạn |
|---|---|---|
|labour |Ít nhất1 trong4 substrings |Người lao động...,tiền lương...,nghỉ phép...,làm việc...;không weight/score |
|unknown |Không match |Hợp đồng dân sự hoặc Bảo hiểm xã hội... có thể unknown;không suy là ngoài pháp luật |

Không word boundaries ở domain regex,nên keyword trong chuỗi dài hơn vẫn có thể match. Không phủ định/ngữ cảnh:diagnostic Tôi không hỏi về lao động,chỉ hỏi thuế vẫn labour. Không multi-domain labels và không gán domain cho từng subquery. Một keyword ở phần cuối đủ đặt global labour cho toàn plan.

Topic whitelist và domain keywords khác nhau. Nghỉ hằng năm có thể thêm topic nhưng không khớp4 domain substrings nếu không có keyword khác. Domain unknown không chặn Search và không đổi mode/index/policy. Receiving Search chỉ schema-validate label,không dùng nó để xây filter.

## Expected output và evidence label

Main lookup/legal_question examples có actual final JSON ở08. Counterexamples trên cũng có diagnostic IDs bare_prefix,extra_space_prefix,lookup_multi,negated_domain,domain_miss,annual_leave. Unsupported intent literal khi manually validate QueryPlan bị ValidationError;understand không bao giờ sinh nhãn thứ ba. Câu unsupported ngoài luật tự rơi fallback legal_question nếu qua input checks;chưa có explicit unsupported-request result.
