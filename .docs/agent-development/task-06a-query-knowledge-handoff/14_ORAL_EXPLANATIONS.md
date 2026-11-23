# Giải thích miệng và sơ đồ bảng

Các script dưới đây là lời giải thích dựa trên source, không phải đo thời gian nói của một người cụ thể. Mốc60 giây/3 phút là mục tiêu luyện tập; điều chỉnh tốc độ sau khi tập. Ví dụ ở đây mang nhãn ILLUSTRATIVE; executions thực tế xem08 và evidence JSON.

## Script khoảng60 giây

Query Agent hiện tại của Tillegal là hàm deterministic understand, không gọi LLM hoặc Supabase. Nó kiểm kiểu chuỗi, giới hạn1–10000 code points và control characters, rồi chuẩn hóa Unicode NFC và bỏ whitespace đầu cuối. Original vẫn giữ đúng đối số ban đầu.

Hàm dùng regex tách câu thành tối đa bốn subqueries, nhận diện yêu cầu trích dẫn bằng prefix và gán domain bằng bốn cụm từ khóa. Temporal scope là các mentions, có kiểm lịch cho ngày dạng ngày/tháng/năm, không phải ngày truy hồi được tự suy ra. Một số trường hợp thiếu thông tin, quá nhiều phần hoặc ngày sai tạo clarification.

Kết quả công khai là dictionary sáu fields của QueryPlan. Trong LangGraph, Query node gọi trực tiếp understand; router dừng nếu có clarification, còn lại chuyển plan sang Search. Search validate lại plan rồi tạo request từ subquery.text và options được inject. Agent có thể giải thích được bằng rules nhưng còn giới hạn về ngữ cảnh, từ vựng và ambiguity.

Nguồn: query/agent.py29–95; graphs/legal_qa.py24–66; search/agent.py38–56, xem [source index](16_SOURCE_SYMBOL_INDEX.md).

## Script khoảng3 phút

Em sẽ phân biệt tên Agent với cơ chế thực thi. Implementation hiện tại là một hàm Python understand(question: str) trả dict, sử dụng re, unicodedata, datetime.date và Pydantic. Không có prompt, pretrained model, confidence score hay database call trong hàm. Đây là lớp lập kế hoạch truy hồi theo quy tắc, không trả lời câu hỏi pháp luật.

Boundary đầu tiên kiểm isinstance, raw length và Unicode control characters. Chuỗi rỗng khác whitespace-only ở mã lỗi. NFC và strip tạo local text để xử lý, còn original nhận raw question. Vì length được kiểm trước normalization nên code points dạng NFD có thể ảnh hưởng giới hạn; không được gọi giới hạn này là bytes hoặc số ký tự nhìn thấy.

Tiếp theo regex tách parts theo dấu hỏi, chấm phẩy, newline hoặc một số cấu trúc và có lookahead. Prefix trích dẫn, trích nguyên văn hoặc tìm đoạn chỉ tạo quote_lookup khi có topic và đúng một part. Nếu không, intent là legal_question. Domain labour chỉ do substring match lao động, tiền lương, nghỉ phép hoặc làm việc; unknown không chứng minh câu không thuộc lao động. Không có phân loại đa domain.

Temporal regex bắt slash-date, năm19xx/20xx và hiện nay/hiện hành. datetime.date kiểm ngày lịch thật, nên29/02/2024 hợp lệ còn31/02/2024 dẫn tới clarification. Year-only hoặc relative mention chỉ được lưu string. temporal_scope không tự override trusted as_of_date do bên gọi cung cấp cho Search.

Subqueries gồm text và purpose. Lookup dùng topic đã bỏ prefix; câu thường dùng tối đa bốn parts rồi thêm topic cụm từ cố định nếu còn chỗ. Topic dedup bằng casefold nhưng không loại duplicate base parts. Plan hợp lệ luôn có1–4 subqueries, kể cả clarification. Không được nhầm zero service calls với zero subqueries.

Clarification có thứ tự: quá nhiều parts, một số dạng thiếu thông tin, cuối cùng ngày sai ghi đè thông báo trước. Hàm tạo QueryPlan rồi model_dump thành dict. Field clarification nullable nhưng vẫn required vì không có default. Search model_validate lại toàn plan trước guard clarification; malformed plan có thể fail trước guard.

Trong graph, QuerySearchNodes.query gọi understand trực tiếp, ghi plan/options/status và router quyết định END hoặc Search. Search tạo RetrievalRequests từ text và options độc lập; không lấy domain hay temporal_scope tự làm filter. Workflow tạo input state mới cho mỗi invocation; các tests in-memory không chứng minh persistent resume. Task này chạy120 tests hiện có và52 diagnostics offline, không dùng dữ liệu Supabase thật. Những con số đó xác minh hành vi, chưa phải semantic accuracy benchmark. Các edge cases như punctuation-only, tab-only clause và ISO date cần được mô tả trung thực trước khi đề xuất sửa ở task khác.

Nguồn: [source trace07](07_SOURCE_EXECUTION_TRACE.md), [graph09](09_LANGGRAPH_QUERY_NODE.md), [boundary10](10_QUERY_SEARCH_CONTRACT.md), [tests11](11_TEST_MATRIX_AND_RESULTS.md).

## Sơ đồ bảng: vẽ và giải thích theo ownership

```text
question: str (raw argument)
       |
       v
understand [query/agent.py29–95]
  type/length/control checks ---- invalid --> QueryInputError, no plan
       |
  NFC + strip -> local text          original := raw question
       |
  split parts / prefix / quote_only
       |
  temporal mentions + calendar check
       |
  clarification priority
       |
  base subqueries + bounded topic extraction
       |
  QueryPlan(...).model_dump() -> dict, six fields
       |
       + standalone caller receives dict
       |
QuerySearchNodes.query [graphs/legal_qa.py24–33]
  state update: plan, clarification, options, status, reset downstream
       |
route_query [36–37]
       + clarification truthy -> END (0 Search calls)
       |
       + otherwise -> Search node [39–54]
                          |
                   search [search/agent.py38–56]
                   model_validate(plan), options
                   prebuild request(text + options)
                   await injected service sequentially
```

Một sơ đồ có thể dùng lúc giảng; không phải các entrypoints đều chạy nối nhau trong mọi đường gọi. Đường standalone chỉ understand; QuerySearch.search là wrapper khác và không nằm bên trong Query node.

## Bài tập tự giải thích bằng ví dụ

- ILLUSTRATIVE `Trích dẫn: nghỉ phép`: phân biệt raw original, text sau NFC, topic bỏ prefix, lookup purpose và domain keyword. Sau đó đối chiếu observed quote trace08 trước khi chép output cụ thể.
- OBSERVED trong08: ngày31/02/2024 không trở thành exception input; nó tạo clarification và graph skip Search. Hỏi tiếp vì sao original vẫn còn ngày sai.
- OBSERVED trong08: hai base parts nghỉ phép trùng nhau không được seen dedup. Chỉ đúng vị trí khởi tạo seen và append topic.
- OBSERVED trong08: tab-only clause qua Query nhưng không qua RetrievalRequest. Hỏi tiếp validation thuộc lớp nào và vì sao chưa có service calls.

Khi giảng không nói “Query hiểu ngữ nghĩa”, “temporal_scope chọn ngày hiện hành”, “LangGraph tự lưu lâu dài” hoặc “test pass chứng minh mọi câu hỏi pháp luật đều đúng”.
