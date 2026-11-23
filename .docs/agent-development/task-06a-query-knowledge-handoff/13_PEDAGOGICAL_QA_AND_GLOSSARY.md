# Hỏi–đáp học thuật và glossary

**48 câu**, từ nền tảng tới phản biện. Source references dùng line range trong văn bản; source index16 chứa symbol ranges. Các ví dụ runtime đầy đủ ở08, không xem ví dụ diễn giải là một execution mới.

## 1. Query Agent chịu trách nhiệm gì?

Chuyển một question thành kế hoạch tra cứu có cấu trúc: original, intent, domain, temporal_scope, subqueries và clarification. Hàm không trả câu trả lời pháp lý hoặc evidence; những phần đó ở downstream.

Bằng chứng: [understand29–95](../../../src/applications/tillegal/agents/query/agent.py).

## 2. Vì sao tên Agent không chứng minh có LLM?

Agent là tên tổ chức module. Imports chỉ có re, unicodedata, date, typing và Pydantic; toàn bộ understand là rules, không gọi model hay API. Phải đọc call graph thay vì suy từ tên.

Bằng chứng: [imports3–8;understand29–95](../../../src/applications/tillegal/agents/query/agent.py).

## 3. Deterministic nghĩa là gì trong implementation này?

Các nhánh do chuỗi input và rules cố định quyết định; không đọc clock, random hoặc mạng. Cùng chuỗi và cùng implementation/runtime cho cùng kết quả. Điều đó không chứng minh kết quả phân loại luôn đúng về pháp lý.

Bằng chứng: [29–95](../../../src/applications/tillegal/agents/query/agent.py).

## 4. Entrypoint và kiểu trả thực tế là gì?

`understand(question: str) -> dict`. Bên trong tạo QueryPlan rồi gọi model_dump; caller nhận dict, không phải QueryPlan instance. Annotation str không tự chặn non-string nên hàm có guard riêng.

Bằng chứng: [29–34;88–95](../../../src/applications/tillegal/agents/query/agent.py).

## 5. Raw input dài tối đa bao nhiêu?

Từ1 đến10000 Python code points, kiểm bằng len trước NFC và strip. Không phải10000 bytes hoặc grapheme clusters; chuỗi NFD có thể dài hơn NFC dù người đọc thấy tương đương.

Bằng chứng: [33–34;37](../../../src/applications/tillegal/agents/query/agent.py).

## 6. Non-string bị xử lý thế nào?

isinstance(question,str) phải đúng. Nếu sai, raise QueryInputError với mã QUERY_INPUT_TYPE trước khi gọi len hay regex. Không ép số/list thành chuỗi để tiếp tục.

Bằng chứng: [31–32](../../../src/applications/tillegal/agents/query/agent.py).

## 7. Chuỗi rỗng và whitespace-only có giống nhau không?

Cùng là invalid input nhưng khác guard: chuỗi rỗng vi phạm length, whitespace-only có raw length hợp lệ rồi NFC/strip thành rỗng và nhận QUERY_INPUT_EMPTY. Không tạo QueryPlan ở cả hai trường hợp.

Bằng chứng: [33–39](../../../src/applications/tillegal/agents/query/agent.py).

## 8. Control characters nào được phép?

Category Unicode Cc hoặc Cs bị chặn, ngoại trừ tab, LF và CR. Các category khác không bị blanket-reject; U+200B thuộc Cf có thể đi qua. Cho phép tab phục vụ input nhiều phần nhưng còn edge case ở split.

Bằng chứng: [35–36](../../../src/applications/tillegal/agents/query/agent.py).

## 9. NFC làm gì với tiếng Việt?

NFC chuẩn hóa các biểu diễn Unicode tương đương sang dạng composed khi có thể, ví dụ a cộng dấu kết hợp thành ký tự dựng sẵn phù hợp. NFC không bỏ dấu, dịch, sửa chính tả hoặc biến mọi chữ thành lowercase.

Bằng chứng: [37](../../../src/applications/tillegal/agents/query/agent.py).

## 10. Original có bị NFC/strip thay đổi không?

Không. local text nhận kết quả normalized/stripped; QueryPlan.original nhận đúng question ban đầu. Nhờ vậy giữ được raw argument để đối chiếu. Không có normalized_text field riêng trong public plan.

Bằng chứng: [37;89](../../../src/applications/tillegal/agents/query/agent.py).

## 11. Hàm có chuẩn hóa tất cả khoảng trắng không?

Không có whitespace-collapse toàn cục. strip đầu/cuối text khác với s.strip(" ?;") trên từng part. Case-insensitive matching cũng không có nghĩa text được lowercase toàn bộ.

Bằng chứng: [37–46](../../../src/applications/tillegal/agents/query/agent.py).

## 12. Query normalization có phải preprocessing BM25/Dense không?

Không. Đây là NFC/trim và rules lập plan. BM25 tokenization hay Dense embedding preprocessing thuộc retrieval phía sau; không được gán các thao tác đó cho understand.

Bằng chứng: [29–95](../../../src/applications/tillegal/agents/query/agent.py).

## 13. Có bao nhiêu intent?

Chỉ quote_lookup và legal_question theo Literal. Không có compare, summarize hoặc procedural intent trong schema hiện tại; tên nghiệp vụ ngoài schema không tự trở thành năng lực.

Bằng chứng: [22;90](../../../src/applications/tillegal/agents/query/agent.py).

## 14. Khi nào quote_lookup được chọn?

Prefix đầu câu phải khớp trích dẫn, trích nguyên văn hoặc tìm đoạn, có separator; topic sau bỏ prefix phải nonempty và len(parts)==1. quote_only quyết định cả intent và purpose lookup.

Bằng chứng: [45–48;74;90](../../../src/applications/tillegal/agents/query/agent.py).

## 15. Vì sao câu “Trích dẫn” có thể không yêu cầu clarification?

Không có separator sau prefix nên prefix không match; câu có hai whitespace tokens và không nằm trong fixed ambiguous set. Fallback thành legal_question. Đây là giới hạn phrasing của rules, không phải kết luận câu đã đủ ngữ cảnh.

Bằng chứng: [45;66–71](../../../src/applications/tillegal/agents/query/agent.py).

**Trả lời sai thường gặp:** Có hai từ thì Query đã hiểu đầy đủ tình huống.

**Vì sao sai và cách trả lời đúng:** nhầm cơ chế hoặc phạm vi bằng chứng. Cần chỉ đúng guard, kiểu dữ liệu và caller trong phần giải thích ở trên, rồi phân biệt kết quả rule với bảo đảm nghiệp vụ. Không nâng một kiểm tra cục bộ thành cam kết toàn hệ thống.

## 16. Nếu prefix quote và nhiều clauses cùng xuất hiện thì sao?

len(parts)>1 làm quote_only=False; intent legal_question và base parts giữ text đã split, có thể vẫn giữ prefix trong part đầu. Không có classifier cho mỗi subquery.

Bằng chứng: [40–48;74;90](../../../src/applications/tillegal/agents/query/agent.py).

## 17. Domain có những giá trị nào?

labour hoặc unknown. Một re.search với bốn mẫu lao động, tiền lương, nghỉ phép, làm việc quyết định labour; còn lại unknown. Không có taxonomy dân sự, hình sự hoặc bảo hiểm riêng.

Bằng chứng: [23;91](../../../src/applications/tillegal/agents/query/agent.py).

## 18. Domain labour có bảo đảm câu thuộc luật lao động không?

Không. Đây là substring heuristic, không kiểm phủ định hoặc word boundaries. Câu phủ định muốn hỏi về lao động vẫn có thể match; câu về bảo hiểm không có bốn cụm lại có thể unknown.

Bằng chứng: [91](../../../src/applications/tillegal/agents/query/agent.py).

**Trả lời sai thường gặp:** Keyword match chứng minh phân loại pháp lý đúng.

**Vì sao sai và cách trả lời đúng:** nhầm cơ chế hoặc phạm vi bằng chứng. Cần chỉ đúng guard, kiểu dữ liệu và caller trong phần giải thích ở trên, rồi phân biệt kết quả rule với bảo đảm nghiệp vụ. Không nâng một kiểm tra cục bộ thành cam kết toàn hệ thống.

## 19. Domain có tự trở thành retrieval filter không?

Search hiện lấy subquery.text cùng SearchOptions để tạo RetrievalRequest; domain không được map thành filter ở boundary này. Đừng suy domain label đồng nghĩa thay đổi corpus.

Bằng chứng: [38–44](../../../src/applications/tillegal/agents/search/agent.py).

## 20. Date extraction nhận những gì?

Regex nhận ngày d/m/yyyy, năm độc lập19xx hoặc20xx, hiện nay và hiện hành với boundary guards. Nó lưu strings theo thứ tự xuất hiện; không tạo một time interval object.

Bằng chứng: [49–62](../../../src/applications/tillegal/agents/query/agent.py).

## 21. 29/02/2024 và31/02/2024 khác nhau ở đâu?

Slash-date được tách day/month/year rồi gọi date(year,month,day). Leap day2024 hợp lệ nên append;31/02 ném ValueError, bị bắt để đánh dấu invalid_date và bỏ mention đó khỏi scope.

Bằng chứng: [55–62](../../../src/applications/tillegal/agents/query/agent.py).

## 22. Year-only và date đầy đủ có cùng miền năm không?

Không. Year-only regex chỉ19xx/20xx; full date dùng bốn chữ số rồi datetime.date validation. Không nên suy mọi date chỉ hỗ trợ1900–2099 từ branch year-only.

Bằng chứng: [52;55–62](../../../src/applications/tillegal/agents/query/agent.py).

## 23. ISO date được hỗ trợ đầy đủ chưa?

Không có parser yyyy-mm-dd. Trong diagnostic, câu chứa2024-02-29 trích được2024 như year mention; không xác minh toàn ISO date. Unsupported format không đồng nghĩa temporal_scope luôn rỗng.

Bằng chứng: [52–62](../../../src/applications/tillegal/agents/query/agent.py).

**Trả lời sai thường gặp:** Không parse ISO thì tuyệt đối không extract được gì.

**Vì sao sai và cách trả lời đúng:** nhầm cơ chế hoặc phạm vi bằng chứng. Cần chỉ đúng guard, kiểu dữ liệu và caller trong phần giải thích ở trên, rồi phân biệt kết quả rule với bảo đảm nghiệp vụ. Không nâng một kiểm tra cục bộ thành cam kết toàn hệ thống.

## 24. “Hiện nay” được resolve thành ngày hôm nay không?

Không. Nó được giữ thành mention string với case gốc. Query không đọc clock và không tự biến mention này thành trusted as_of_date.

Bằng chứng: [49–62](../../../src/applications/tillegal/agents/query/agent.py).

## 25. Temporal scope có tự thay as_of_date không?

Không. temporal_scope thuộc QueryPlan; as_of_date là cấu hình SearchOptions được inject độc lập vào RetrievalRequest. Legal validity checks là trách nhiệm downstream, không phải chứng minh bằng mention extraction.

Bằng chứng: [13–28;38–44](../../../src/applications/tillegal/agents/search/agent.py).

**Trả lời sai thường gặp:** Query tự chọn ngày truy hồi bằng temporal_scope.

**Vì sao sai và cách trả lời đúng:** nhầm cơ chế hoặc phạm vi bằng chứng. Cần chỉ đúng guard, kiểu dữ liệu và caller trong phần giải thích ở trên, rồi phân biệt kết quả rule với bảo đảm nghiệp vụ. Không nâng một kiểm tra cục bộ thành cam kết toàn hệ thống.

## 26. Subquery có những fields nào?

text là str min_length1,max_length10000; purpose là lookup, question_part hoặc topic. Không có per-subquery date/domain/confidence. Pydantic kiểm độ dài không tự bảo đảm text không toàn whitespace.

Bằng chứng: [15–17](../../../src/applications/tillegal/agents/query/agent.py).

## 27. Câu hỏi được split thế nào?

Dùng separator semicolon, question mark, newline; hoặc “và” có whitespace hai bên khi lookahead gặp khi nào, ai, bao nhiêu, điều kiện, thủ tục. Không split mọi liên từ và, không khôi phục chủ thể bị lược.

Bằng chứng: [40–44](../../../src/applications/tillegal/agents/query/agent.py).

## 28. Một plan hợp lệ có thể có0 subqueries không?

Không: schema yêu cầu1–4 và fallback queries=[text] nếu parts rỗng. Clarification vẫn có subqueries; zero retrieval requests là chuyện khác. Invalid input raise trước khi tạo plan.

Bằng chứng: [25;48;64–95](../../../src/applications/tillegal/agents/query/agent.py).

**Trả lời sai thường gặp:** Clarification luôn trả danh sách subqueries rỗng.

**Vì sao sai và cách trả lời đúng:** nhầm cơ chế hoặc phạm vi bằng chứng. Cần chỉ đúng guard, kiểu dữ liệu và caller trong phần giải thích ở trên, rồi phân biệt kết quả rule với bảo đảm nghiệp vụ. Không nâng một kiểm tra cục bộ thành cam kết toàn hệ thống.

## 29. Topic extraction có phải semantic expansion không?

Nó thêm nguyên cụm topic đã match trong input vào cuối danh sách khi còn chỗ. Không thêm synonyms, paraphrase hay kiến thức ngoài câu. Có thể gọi bounded deterministic topic extraction, tránh gọi semantic expansion.

Bằng chứng: [75–87](../../../src/applications/tillegal/agents/query/agent.py).

## 30. Bảy topic rules là gì?

đối thoại định kỳ; nghỉ hằng năm; nghỉ phép; thời giờ làm việc; chấm dứt hợp đồng lao động; tiền lương; làm thêm giờ. Chúng khác bốn domain rules, nên topic match không kéo theo labour.

Bằng chứng: [77–78;91](../../../src/applications/tillegal/agents/query/agent.py).

## 31. Dedup hoạt động trên toàn danh sách phải không?

Không. seen ban đầu gồm casefold của queries để tránh thêm lại topic, nhưng base parts trùng nhau vẫn còn. “nghỉ phép; nghỉ phép” tạo hai question_part giống nhau. Đây là kết quả observed trong trace.

Bằng chứng: [48;74;82–87](../../../src/applications/tillegal/agents/query/agent.py).

**Trả lời sai thường gặp:** seen loại mọi phần trùng nhau.

**Vì sao sai và cách trả lời đúng:** nhầm cơ chế hoặc phạm vi bằng chứng. Cần chỉ đúng guard, kiểu dữ liệu và caller trong phần giải thích ở trên, rồi phân biệt kết quả rule với bảo đảm nghiệp vụ. Không nâng một kiểm tra cục bộ thành cam kết toàn hệ thống.

## 32. Nếu có năm clauses thì sao?

queries chỉ lấy parts[:4] và clarification yêu cầu tối đa bốn phần. Vì clarification tồn tại, graph dừng trước Search; đừng hiểu là âm thầm tra cứu bốn phần và bỏ phần thứ năm.

Bằng chứng: [48;64–65](../../../src/applications/tillegal/agents/query/agent.py).

## 33. Clarification rules ưu tiên thế nào?

Quá nhiều parts trước; nếu không thì empty quote topic, token count<2 hoặc ba fixed ambiguous phrases. Cuối cùng invalid_date ghi đè bất kỳ message trước đó. Không phải hệ phân tích thiếu tình tiết tổng quát.

Bằng chứng: [63–73](../../../src/applications/tillegal/agents/query/agent.py).

## 34. Clarification có đổi intent không?

Không trực tiếp. intent dựa quote_only và domain dựa keyword dù clarification có mặt. Ví dụ quote request có ngày sai vẫn có thể quote_lookup nhưng graph yêu cầu làm rõ.

Bằng chứng: [47;72–95](../../../src/applications/tillegal/agents/query/agent.py).

## 35. QueryPlan.clarification optional nghĩa là có thể bỏ key?

Sai nếu hiểu vậy: annotation str|None cho phép giá trị None nhưng field không có default, nên vẫn required trong constructor/model_validate. Trong LegalQAState total=False là ý nghĩa optional-key khác.

Bằng chứng: [20–26](../../../src/applications/tillegal/agents/query/agent.py).

**Trả lời sai thường gặp:** Nullable đồng nghĩa key có default và có thể bỏ.

**Vì sao sai và cách trả lời đúng:** nhầm cơ chế hoặc phạm vi bằng chứng. Cần chỉ đúng guard, kiểu dữ liệu và caller trong phần giải thích ở trên, rồi phân biệt kết quả rule với bảo đảm nghiệp vụ. Không nâng một kiểm tra cục bộ thành cam kết toàn hệ thống.

## 36. Extra field confidence có được giữ không?

Theo Pydantic defaults của model hiện tại, extra bị ignore; probe confidence không làm Query có confidence. Receiving model validation và result.plan giữ raw dict có thể khác nhau; xem boundary guide.

Bằng chứng: [20–26;95](../../../src/applications/tillegal/agents/query/agent.py).

**Trả lời sai thường gặp:** Extra confidence được model giữ nên Agent có score.

**Vì sao sai và cách trả lời đúng:** nhầm cơ chế hoặc phạm vi bằng chứng. Cần chỉ đúng guard, kiểu dữ liệu và caller trong phần giải thích ở trên, rồi phân biệt kết quả rule với bảo đảm nghiệp vụ. Không nâng một kiểm tra cục bộ thành cam kết toàn hệ thống.

## 37. Ai gọi understand trong LangGraph?

QuerySearchNodes.query gọi trực tiếp understand(state["question"]). Nó không gọi QuerySearch.search để chạy cả pipeline trong Query node; Search có node riêng và routing ở giữa.

Bằng chứng: [24–40](../../../src/applications/tillegal/graphs/legal_qa.py).

## 38. Query node cập nhật những gì?

Trả plan, options, clarification, status QUERY_COMPLETED hoặc CLARIFICATION_REQUIRED và reset downstream fields thành None. Đây là state update dict, không phải biến toàn cục chứa request gần nhất.

Bằng chứng: [24–33](../../../src/applications/tillegal/graphs/legal_qa.py).

## 39. Graph dừng khi nào vì clarification?

route_query đọc truthiness clarification và trả end hoặc search; compile map end tới END. Vì không đi vào Search node nên không có retrieval calls ở nhánh đó, được xác minh bởi graph tests/fake traces.

Bằng chứng: [36–37;57–66](../../../src/applications/tillegal/graphs/legal_qa.py).

## 40. LegalQAState total=False có nghĩa runtime tự validate mọi key?

Không. TypedDict phục vụ mô tả type, total=False cho phép thiếu keys; Python không tự chạy Pydantic validation cho nó. Node truy cập state["question"] vẫn có thể KeyError nếu caller bypass workflow boundary. Boundary probes xác minh thiếu route/query key.

Bằng chứng: [24–37](../../../src/applications/tillegal/graphs/legal_qa.py).

**Trả lời sai thường gặp:** TypedDict tự validate missing keys lúc chạy.

**Vì sao sai và cách trả lời đúng:** nhầm cơ chế hoặc phạm vi bằng chứng. Cần chỉ đúng guard, kiểu dữ liệu và caller trong phần giải thích ở trên, rồi phân biệt kết quả rule với bảo đảm nghiệp vụ. Không nâng một kiểm tra cục bộ thành cam kết toàn hệ thống.

## 41. Mỗi request có state riêng không?

Workflow.execute tạo input dict mới và mang request/run IDs qua framework executor. Tests thực thi nhiều invocations kiểm isolation; không có cơ sở gán persistent checkpoint/resume cho graph compiler hiện tại. Pipeline dependency dùng chung cần phân biệt với request state.

Bằng chứng: [69–95](../../../src/applications/tillegal/graphs/legal_qa.py).

**Trả lời sai thường gặp:** Có LangGraph thì tự có checkpoint bền vững.

**Vì sao sai và cách trả lời đúng:** nhầm cơ chế hoặc phạm vi bằng chứng. Cần chỉ đúng guard, kiểu dữ liệu và caller trong phần giải thích ở trên, rồi phân biệt kết quả rule với bảo đảm nghiệp vụ. Không nâng một kiểm tra cục bộ thành cam kết toàn hệ thống.

## 42. Search thực sự đọc field nào của plan?

Search validate toàn dict bằng QueryPlan.model_validate; clarification quyết định early return, mỗi subquery.text thành request query. intent/domain/time/original không tự thay SearchOptions. Raw plan vẫn được gắn vào SearchState để giữ thông tin.

Bằng chứng: [31–56](../../../src/applications/tillegal/agents/search/agent.py).

## 43. Malformed plan có được cứu bằng clarification không?

Không. Search validate plan trước guard clarification. Empty subqueries hoặc unsupported intent thất bại Pydantic trước khi guard chạy, kể cả có clarification. Không invent fallback thành legal_question ở receiving boundary.

Bằng chứng: [40–44](../../../src/applications/tillegal/agents/search/agent.py).

**Trả lời sai thường gặp:** Clarification luôn được xét trước schema.

**Vì sao sai và cách trả lời đúng:** nhầm cơ chế hoặc phạm vi bằng chứng. Cần chỉ đúng guard, kiểu dữ liệu và caller trong phần giải thích ở trên, rồi phân biệt kết quả rule với bảo đảm nghiệp vụ. Không nâng một kiểm tra cục bộ thành cam kết toàn hệ thống.

## 44. Câu chỉ chứa dấu câu và tab-only clause có bị chặn hết chưa?

Chưa. “ ? ; ” qua Query với punctuation fallback và có thể tới fake retrieval. Một clause chỉ tab có thể qua Subquery min_length nhưng bị RetrievalRequest nonblank validator chặn; requests được dựng trước loop nên diagnostic ghi0 service calls.

Bằng chứng: [40–46](../../../src/applications/tillegal/agents/search/agent.py).

**Trả lời sai thường gặp:** min_length=1 bảo đảm chuỗi có nội dung nhìn thấy.

**Vì sao sai và cách trả lời đúng:** nhầm cơ chế hoặc phạm vi bằng chứng. Cần chỉ đúng guard, kiểu dữ liệu và caller trong phần giải thích ở trên, rồi phân biệt kết quả rule với bảo đảm nghiệp vụ. Không nâng một kiểm tra cục bộ thành cam kết toàn hệ thống.

## 45. Invalid input, clarification và no match khác nhau thế nào?

Invalid input ném QueryInputError, không có plan. Clarification trả plan và ngăn Search. No match là Query đủ đi Search nhưng retrieval không tìm evidence theo kết quả service; fixture NO_MATCH không chứng minh corpus Supabase không có luật.

Bằng chứng: [24–54](../../../src/applications/tillegal/graphs/legal_qa.py).

## 46. 120 tests pass chứng minh semantic accuracy chưa?

Chưa. Nó chứng minh các assertions trong focused suite với fixtures/mocks và deterministic code hiện tại. Không có held-out intent/domain accuracy benchmark hoặc production latency measurement được thực hiện trong task này.

Bằng chứng: [29–95; xem guide11](../../../src/applications/tillegal/agents/query/agent.py).

**Trả lời sai thường gặp:** Test pass nghĩa là phân loại luật luôn chính xác.

**Vì sao sai và cách trả lời đúng:** nhầm cơ chế hoặc phạm vi bằng chứng. Cần chỉ đúng guard, kiểu dữ liệu và caller trong phần giải thích ở trên, rồi phân biệt kết quả rule với bảo đảm nghiệp vụ. Không nâng một kiểm tra cục bộ thành cam kết toàn hệ thống.

## 47. Có nên sửa các heuristic ngay khi thấy hạn chế không?

Không trong task handoff. Cần quyết định contract/acceptance criteria và regression riêng. Báo cáo phân biệt observed behavior với ý định thiết kế; không sửa source để làm ví dụ đẹp hơn.

Bằng chứng: [29–95; xem guide15](../../../src/applications/tillegal/agents/query/agent.py).

## 48. Có thể nói Query đã kết nối trực tiếp Supabase không?

Không. Query không có database dependency hay I/O. Search nhận retrieval service được bootstrap bên ngoài; Query chỉ tạo plan. Không lấy hành vi legacy ai_core, Judge hoặc Dense model gán cho Query.

Bằng chứng: [imports3–8;29–95](../../../src/applications/tillegal/agents/query/agent.py).

**Trả lời sai thường gặp:** Query Agent gọi database vì service tổng thể dùng Supabase.

**Vì sao sai và cách trả lời đúng:** nhầm cơ chế hoặc phạm vi bằng chứng. Cần chỉ đúng guard, kiểu dữ liệu và caller trong phần giải thích ở trên, rồi phân biệt kết quả rule với bảo đảm nghiệp vụ. Không nâng một kiểm tra cục bộ thành cam kết toàn hệ thống.

## Glossary

| Thuật ngữ | Nghĩa trong implementation hiện tại |
|---|---|
| Agent | Tên vai trò/module; ở đây là hàm rules, không mặc định là LLM. |
| Deterministic | Cùng input và implementation/runtime cho cùng output trong hàm này. |
| Heuristic | Quy tắc thực dụng có false positive/negative, không phải chứng minh ngữ nghĩa. |
| Regex | Pattern so khớp chuỗi, dùng cho split/prefix/topic/domain/time. |
| NFC | Unicode canonical composition; không bỏ dấu. |
| Code point | Đơn vị len(str), khác byte và grapheme. |
| Grapheme cluster | Đơn vị người đọc có thể thấy như một ký tự, có thể gồm nhiều code points. |
| Cc/Cs/Cf | Unicode categories: control, surrogate, format; guard xử lý chúng khác nhau. |
| Casefold | So sánh case-insensitive cho fixed ambiguity/dedup topic; không biến đổi toàn public output. |
| Intent | Nhãn quote_lookup hoặc legal_question cho toàn plan. |
| Domain | labour hoặc unknown bằng keyword heuristic. |
| Temporal mention | Đoạn thời gian bắt được trong text. |
| Temporal scope | List string mentions trong QueryPlan, không phải resolved legal validity interval. |
| as_of_date | Ngày tin cậy do SearchOptions cung cấp độc lập. |
| Subquery | Object text/purpose dùng tạo retrieval request. |
| QueryPlan | Pydantic contract sáu fields; understand xuất dict. |
| model_dump | Chuyển Pydantic model thành Python dict; không phải JSON string. |
| model_validate | Kiểm object/dict tại receiving boundary và tạo model. |
| Nullable | Cho phép None làm giá trị; không mặc định cho phép thiếu key. |
| TypedDict | Mô tả kiểu của dictionary, không tự là runtime validator. |
| State update | Dict node trả về để graph kết hợp với state hiện có. |
| Reducer | Quy tắc hợp nhất state channel; không mặc định mọi field là append-list. |
| Routing | Chọn end/search từ clarification. |
| Dependency injection | Truyền retrieval/options vào pipeline thay vì Query tự tạo chúng. |
| Clarification | Plan hợp lệ yêu cầu hỏi lại; khác exception. |
| No match | Kết quả retrieval không có evidence phù hợp; không phải input invalid. |
| Provenance | Khả năng truy ngược input/source; original chỉ là một phần, không phải citation verification. |
| OBSERVED | Giá trị đo/thu được bởi execution trong evidence. |
| SOURCE-DERIVED | Suy ra trực tiếp từ source, không giả làm giá trị runtime đã đo. |
| ILLUSTRATIVE | Ví dụ giải thích; không chứng minh đã chạy. |
| Checkpoint | State snapshot để persistence/resume; graph đang kiểm tra không tự chứng minh hỗ trợ này. |
| Regression | Kiểm hành vi không vô tình đổi sau thay đổi tương lai. |
