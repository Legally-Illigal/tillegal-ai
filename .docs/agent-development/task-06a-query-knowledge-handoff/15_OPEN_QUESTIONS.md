# Missing evidence,discrepancies và câu hỏi mở

## Historical material không có trong target

Task00,01,02 directories không hiện diện. Task03–05 có33 Markdown hiện có và supporting evidence;được đọc làm support,không thay source authority. Không truy cập checkout legacy để phục dựng missing27 tests hoặc HTTP behavior cũ.

## Discrepancy đã xác minh

1. Task5 `02_GRAPH_STATE_AND_CONTRACTS.md` auto-table ghi LegalQAState fields Required. Source LegalQAState96 khai báo total=False và inherited WorkflowState cũng total=False;runtime __required_keys__ rỗng. New guide09/16 dùng optional typed keys và giải thích runtime functions vẫn cần keys cụ thể. Không sửa historical report.
2. Historical intent là “Agent” không có nghĩaQuery dùng LLM. Source hiện chỉrules/Pydantic;không gán E5/reranker downstream cho Query.
3. “Zero subqueries khi clarification” là mô tả dễ nhầm. QueryPlan hợp lệ vẫn1–4;graph skip Search/direct Search có zero requests. Current source không có pending field như legacy pilot.
4. Source target chat route là stub;không gán HTTP422 wrapper của checkout cũ cho target. Current boundary mới là application function/graph,typed errors propagate.
5. Unsupported ISO/date format không đồng nghĩakhông có bất kỳ mention nào:ISO input observed tríchyear2024. Calendar validity chỉ áp full slash-date branch.

## Hành vi còn cần quyết định ở task triển khai riêng

- Có reject punctuation-only/invisible-only text và tab-only clause ngay tại Query không? Hiện diagnostic thể hiện behavior khác nhau,không tự đổi.
- Có mở rộng ambiguity từ fixed phrases/token count sang missing legal facts không? Chưa dataset/criteria.
- Original là exact function argument,nhưng production API tương lai có thể trim trước đó;cần định nghĩa end-user provenance khi endpoint được tạo.
- Khi temporal_scope khác trusted as_of_date,ai hỏi lại hoặc resolve? Hiện Query không override config.
- Có dedup base parts và giữ context khi split guarded và không? Điều đó đổi Search call counts/semantics,cần regression/benchmark riêng.
- Có strict/extra-forbid/versioning cho QueryPlan không? Hiện defaults cho phép ignore extras và không calendar-validate manually supplied scope.
- Có per-subquery intent/domain/time binding không? Hiện labels/scope global.
- Có latency và intent/domain accuracy benchmark trên held-out Vietnamese legal queries không? Chưa verified trong task.

## Những gì chưa được chứng minh

Không có general semantic interpretation/ambiguity correctness,confidence calibration,legal sufficiency,production HTTP entry,checkpoint resume,tenant ACL hoặc model selection cho Query. New120 tests là technical checks,không chứng minh tư vấn đúng luật. Graph fakes isolation không chứng minh production native/DB concurrency safety.

Không chạy DB là quyết định scope vì kiến thức Query xác minh được offline;không phải blocker cần credential. Material bàn giao đủ để viết study guide nhưng author phải giữ labels và limitations,không điền câu trả lời suy đoán vào các mục chưa có evidence.
