# Input boundary, validation và Unicode

Signature OBSERVED bằng inspect: `(question: str) -> dict`. Type annotation không tự validate runtime. `understand` tự kiểm cả direct Python caller; graph wrapper cũng đưa question trực tiếp vào hàm. Target chưa có HTTP Query route để bảo đảm đã validate trước đó. Search revalidate plan là boundary khác,không validation cùng chuỗi lần hai ở Query.

Nguồn chính [Query agent.py,31–39](../../../src/applications/tillegal/agents/query/agent.py). Test [test_query_hardening.py](../../../tests/unit/applications/tillegal/test_query_hardening.py),ranges từng function ở16.

| Điều kiện theo thứ tự | Dữ liệu kiểm | Hợp lệ → | Không hợp lệ → | Rationale kỹ thuật | Test hiện có |
|---|---|---|---|---|---|
|31: isinstance(question,str) |Raw object |Tiếp length |QueryInputError/QUERY_INPUT_TYPE |Tránh AttributeError ngoài contract |test_invalid_type |
|33: 1<=len(question)<=10000 |Raw code points,trước NFC |Tiếp controls |QUERY_INPUT_LENGTH |Giữ giới hạn original/schema,bounded text |test_length;test_unicode_and_original cho10000 |
|35: bất kỳ Cc/Cs trừ tab/LF/CR |Từng raw code point |Tiếp normalize |QUERY_INPUT_CHARACTER |Control không phù hợp/lone surrogate |test_characters |
|37: NFC(question).strip() |Raw string đã qua checks trên |Tạo local text |Không có reject riêng ở normalize |Canonical Unicode và trim edges |test_unicode_and_original |
|38: text không rỗng |Normalized/stripped text |Tiếp analysis |QUERY_INPUT_EMPTY |Không tạo query toàn whitespace |test_blank |

Mọi QueryInputError là subclass ValueError,dòng11–12; message chỉ mã cố định,không kèm query. Empty string bị LENGTH trước EMPTY; whitespace nonempty bị EMPTY sau normalize. Raw length quá lớn dù chỉ whitespace vẫn LENGTH. bool/int/list/dict/bytes không phải str và bị TYPE. isinstance cho phép str subclass; chưa kiểm exhaustively custom subclasses.

Python len đếm code points,không phải UTF-8 bytes hoặc grapheme hiển thị. NFD có thể dài hơn NFC trước normalization nên canonical-equivalence chỉ đảm bảo analysis tương ứng trong miền cả hai inputs được chấp nhận. Giới hạn lấy từ code/schema hiện hữu,không tự cắt10000 ký tự.

## Bảng biến đổi thực tế

| Block | Thao tác | Ví dụ | Lossy? | Có đổi original? |
|---|---|---|---|---|
|37 |NFC rồi strip whitespace hai đầu |NFD của Người lao động... → NFC; bỏ spaces ngoài |Representation đổi canonical,edge whitespace bị bỏ ở text |Không |
|40–44 |Split delimiters và strip tập ký tự ` ?;` ở mỗi phần |Câu A? Câu B; → parts |Mất separator/edge punctuation ở parts |Không |
|45–46 |Match prefix và trim ký tự ở edges của topic (literal bên dưới) |Trích nguyên văn: “Điều 1.” → Điều 1 |Bỏ prefix/quotes/period tại edges của lookup text |Không |
|69 |casefold().strip(" ?") để so câu mơ hồ |Có được không? → có được không |Chỉ comparison key |Không |
|82/85/87 |casefold của query/topic để dedup |NGHỈ PHÉP tương đương nghỉ phép trong seen |Chỉ membership key |Không |
|42/45/52/76/91 |re.I |Case-insensitive matching |Không lowercase output toàn văn |Không |

Literal nguyên văn ở dòng46: `topic = text[prefix.end() :].strip(' “”?."') if prefix else ""`. Tập trim gồm space,hai curly double quotes,question mark,period và straight double quote. Đây là strip ký tự ở edges,không collapse whitespace nội bộ.

Không có re.sub,no stemming/lemmatization/word segmentation. `text.split()` ở68 đếm whitespace tokens để heuristic,không tách từ tiếng Việt học máy. Diacritics được giữ. Không gom nhiều spaces nội bộ thành một; vì prefix literal có một space trong cụm nên Trích  dẫn có thể không nhận lookup.

## Unicode/control edge cases

- Cc bao NUL/ESC/DEL/NEL U+0085; dù NEL là whitespace ở một số thao tác,raw category check vẫn reject.
- TAB U+0009,LF U+000A,CR U+000D được cho phép. LF là split delimiter; CR không xuất hiện trong regex delimiter. `.strip(" ?;")` không loại tab/CR khỏi một part nội bộ.
- Cs surrogate bị reject trước Pydantic/JSON. Cf như ZERO WIDTH SPACE U+200B không bị reject như control;diagnostic thấy một plan clarification với subquery chứa ký tự đó.
- Chỉ whitespace thông thường sau NFC/strip bị EMPTY. Không có tổng quát hóa loại mọi invisible character.

NFC/NFD pair trong08 có raw input khác và same normalized text/final analysis khi bỏ original. OBSERVED bằng capture locals và output; không phải illustrative output.

## Khác preprocessing Retrieval

Query normalization phục vụ rules và subqueries. BM25 tokenizer downstream dùng NFC+lowercase+regex token extraction (src/application/services/vbpl_markdown_indexing_service.py:tokenize_sparse_text). Dense encoder thêm `query: ` và tokenize bằng checkpoint. Những bước downstream không được gọi trong understand; không dùng thời gian retrieval để báo Query latency.
