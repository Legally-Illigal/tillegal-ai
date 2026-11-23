# Open questions, discrepancies và evidence gaps

## Đã biết từ source, không gọi là missing

 Search có validation/prebuild/sequential transport/stop-on-failure/native preservation. Không fusion cross-query, không mode auto-selection, không legal sufficiency/ LLM / Supabase trực tiếp. JudgeHandoff có schema/consistency checks nhưng chưa có Judge node. Những sự vắng mặt này là contract hiện tại, không tự là bug cần sửa trong handoff.

## Historical discrepancies và cách phân giải

1. Task 5 `02_GRAPH_STATE_AND_CONTRACTS.md` table gán Required cho LegalQAState optional TypedDict keys. Current LegalQAState 96–103 kế thừa WorkflowState(total= False), nên keys optional về type; functions vẫn có required indexing runtime. Task 6a đã chỉ ra; Task 6B giữ correction, không sửa old report.
2. Ports. Query Embedder docstring nói “Reserved for Task 5; no encoder implementation...here”. Phần “here” chỉ port module; E 5 QueryEncoder implementation hiện có ở integrations và factory dùng. Không dùng comment lịch sử để phủ nhận current Dense support.
3. Task 3 Dense / Hybrid /rerank live NOT TESTED được Task 4 bổ sung evidence. Đây là mốc thời gian khác, không xóa hoặc “sửa” historical results.
4. “Rerank mode” là profile tên ở test/harness, không RetrievalMode thứ tư; source enum chỉ 3 labels.
5. `READY` của packet và graph `SEARCH_COMPLETED` khác Search `COMPLETED`; không gộp thành một status hoặc coi là verdict Judge.
6. Tên “ Search Agent” không chứng minh có LLM, cross-query fusion hoặc direct DB access. Source function 38–56 là authority, không dùng ai_core/legacy EvidenceBundle để điền hành vi.

Nguồn: [Search38–56](../../../src/applications/tillegal/agents/search/agent.py),[state15–103](../../../src/applications/tillegal/state/legal_qa_state.py),[ports](../../../src/applications/tillegal/retrieval/ports.py),[E5 encoder](../../../src/integrations/embeddings/e5_query_encoder.py). Old report hashes được neo trong baseline 409 files.

## Câu hỏi Project Lead cần quyết định ở task tương lai

| Câu hỏi | Vì sao cần quyết định | Hiện trạng đã xác minh |
|---|---|---|
|Có cần validate response context ngay ở direct Search boundary? |Direct consumer chưa đi packet có thể nhận mismatch từ dependency lỗi |context_mismatch giữ response; handoff reject |
|Có cần global evidence budget/dedup/fusion giữa subqueries? |Hiện top_k per query, cùng chunk có thể lặp |3 queries× 2 tạo 6 occurrences nhưng 2 unique IDs ở fixture |
|Muốn exposure partial history khi unexpected exception thế nào? |Classified failure và exception khác output contract |Exception không return SearchState |
|Policy/date/mode được authorize ở API /application nào? |Trusted options không tự là quyền end-user |Options validated nhưng Search không ACL |
|Owner production lifecycle/client cleanup/warmup là ai? |Factory có thể gọi nhiều lần; no close path ở container |Models lazy, shared wrappers; no production startup/shutdown proof |
|Cần queue/concurrency limits thay MODEL_BUSY không? |Shared model locks có fail/fallback semantics |In-memory isolation tests không native load benchmark |
|Có giữ raw mutable plan alias hay snapshot/version strict? |Caller mutation/extras/compatibility |Raw plan identity retained; parsed model ignore extras |
|Metadata JSON compatibility được enforce ở đâu? |dict[str, object] chấp nhận arbitrary values |Synthetic object() gây serialization error |
|Future Judge criteria là gì? | READY chưa kiểm legal sufficiency |Không Judge hoặc verdict logic |
|Có persistent checkpoint/tenant boundary không? |Graph hiện no saver; IDs không auth |No resume/multi-user ACL proof |

## Chưa được kiểm trong Task 6B

Không chạy lại Supabase, không model weights/inference, không thay configs. Existing live evidence đủ phân biệt boundary khỏi unknown production behavior; không có technical uncertainty buộc gọi DB mới. Historical sample ít, không chứng minh current DB state sau thời điểm đó.

Không có held-out retrieval/legal quality benchmark, production latency/throughput, live graph Dense / Hybrid /rerank, multi-subquery live Supabase trace, HTTP end-to-end, durable resume hoặc cleanup guarantees mới. Không được biến các gaps thành câu khẳng định thành công hoặc thất bại.

## Điểm dừng

Bàn giao Search knowledge hoàn chỉnh theo current source. Không implement/sửa Search, Query, Service, Judge, Answer, API hoặc graph; không Word/slides trong task này. Những câu hỏi trên để người phụ trách quyết định bước sau.
