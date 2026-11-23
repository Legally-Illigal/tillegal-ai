# Engineering rationale,alternatives và limitations

Các rationale dưới là **engineering interpretation** từ source,không tự nhận là ADR đã duyệt hoặc lý do lịch sử của tác giả. Bằng chứng source quyết định behavior;theory giúp giải thích tradeoffs. Không dùng external model facts để gán capability cho Query.

| Quyết định thực | Source chứng minh | Rationale/tradeoff kỹ thuật | Alternative | Chưa đo/chưa có |
|---|---|---|---|---|
|Rules deterministic |understand29–95,không random/API/model |Có thể tái lập trên same input/runtime,giải thích bằng branches |LLM/ML classifier có thể xử lý paraphrase nhưng cần model/training/prompt validation |Accuracy/latency/cost comparison |
|Pydantic structured plan |15–26,88–95 |Chặn shape/literal/cardinality sai trước consumer |Unstructured text linh hoạt nhưng parse khó;strict schema mới sẽ cần compatibility review |Schema version/migration riêng cho QueryPlan |
|NFC nội bộ giữ original |37,89 |Canonical matching và truy vết raw input |Normalize cảoriginal đơn giản hơn nhưng mất representation gốc |Boundary-length effects ngoài cases hiện tại |
|Regex intent/domain |45–47,90–91 |Rule inspect được,không cần hosted inference |Semantic classifier có thể tổng quát hơn nhưng cần dataset và safeguards |False-positive/negative rates |
|Bounded phrase extras |75–87 |Thêm từ khóa đã có trong input mà không phát minh luật |Synonym/paraphrase expansion có thể tăng recall nhưng cũng drift intent/tăng calls |Retrieval quality impact,human labels |
|Clarification fixed messages |64–73 |Predictable zero-call branch cho mẫu đã biết |Generated clarification có thể cụ thể hơn nhưng có thể tự thêm assumptions |General missing-fact/ambiguity detection |
|Calendar validation |49–62 |Không dùng impossible slash date làm scope hợp lệ |Temporal resolver có thể hiểu relative/range/ISO nhưng phải có reference policy |Time expression benchmark,context resolution |
|Query/Search tách |QuerySearch21,graph25/40 |Query dễ test offline,Search sở hữu trusted execution và I/O |Gộp vào1 function khó route/đo từng bước và dễ trộn quyền với user text |Production caller/API validation |
|Global labels |QueryPlan model |Contract nhỏ,không cần per-subquery annotation |Per-issue labels tăng biểu đạt nhưng đổi schema và consumer |Multi-domain/multi-intent context model |

## Chi phí và hallucination

Source chứng minh Query không gọi LLM API hoặc pretrained model,nên không có token billing của Query inference trong đường này. Whole pipeline vẫn có retrieval/DB/CPU costs. Không có số tiền hoặc per-query latency đo độc lập trong task.

Rules lấy topics từ input và không sinh reference luật mới bằng model;điều đó không bảo đảm mọi output phù hợp. Substring labour có thể false positive,unknown có thể false negative,split làm mất context,cap bỏ bớt parts/topics và punctuation có thể đi Search. Determinism chỉ làm kết quả lặp lại,dễ kiểm;không biến heuristic thành legal understanding.

LLM-assisted alternative là PROPOSED ngoài scope,không có Query model/prompt/profile đã triển khai. Chỉ schema validation cũng không chứng minh LLM không bịa facts hoặc giữ intent. Mọi so sánh ML-quality/cost/latency cần dataset và measurements riêng.

## Limitations đã quan sát

- Trích dẫn thiếu colon/topic có thể không clarification nếu chỉ đúng2 tokens;internal extra spaces làm prefix miss.
- ? ; có thể tạo valid fallback subquery dù vô nghĩa.
- Tab-only part có thể qua Query model nhưng fail request validation ở Search.
- Base duplicate clauses không dedup;chỉ topic extras được dedup.
- ISO date có thể thành year-only mention;partial dates/relative mới không resolve.
- Invalid dates được giữ trong original/query text nhưng clarification chặn Search;không remove toàn raw text.
- Unknown domain không tương đươngunsupported jurisdiction;negation chưa hiểu.
- Metadata/extra model fields chưa strict/frozen,một số malformed semantic plans có thể qua shape schema nếu bypass entrypoint.

Mọi điểm trên được mô tả,không sửa hoặc refactor trong Task6a. Xem15 cho câu hỏi mở và evidence còn thiếu.
