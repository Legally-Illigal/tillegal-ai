# Engineering rationale, alternatives và giới hạn

Các ý dưới đây phân biệt **SOURCE FACT**, **ENGINEERING INTERPRETATION** và **UNVERIFIED ASSUMPTION**. Source chứng minh cơ chế, không tự chứng minh tác giả chọn cơ chế vì một rationale cụ thể hoặc định lượng lợi ích.

| Decision | SOURCE FACT/source | ENGINEERING INTERPRETATION | Alternative và tradeoff | UNVERIFIED ASSUMPTION/measurement gap |
|---|---|---|---|---|
| Query / Search tách | QueryPlan + Search 38–56, bootstrap 20–21 |Tách text planning khỏi execution transport giúp kiểm boundary độc lập |Một monolithic agent giảm interface nhưng khó phân lập rules/config/side effects |Chưa đo maintainability hoặc dev velocity |
|Delegate retrieval | Search 47 chỉ await service |Tái dùng algorithms/guards đã có, không nhân đôi implementation | Search tự implement BM25 /encoding/fusion sẽ tăng coupling và divergence |Không benchmark alternative trong task |
|Trusted runtime options | SearchOptions 18–28, graph 40 |Giữ governance/date/mode ngoài user-derived text | LLM chọn options cần authorization/validation riêng; không được infer đã có |Không tenant ACL /end-user authorization proof |
| Pydantic boundaries | Search 40–44, Request validators |Fail before I/O và dùng type constraints chung |Dict-only nhanh/linh hoạt nhưng dời lỗi về sâu; strict models hơn đổi compatibility |Chưa đo validation latency; models không runtime-proof mọi bypass |
|Native typed responses |Append object 48; return 53/56 |Giữ metadata/ranking/extensions, tránh lossy adapter |Flat EvidenceBundle cần explicit mapping và schema/version design |Identity không chứng minh correctness upstream; generic serialization chưa có API contract |
|Sequential multi-query |for/await 46–47 |Dễ giữ order và dừng sớm, không concurrency fan-out |gather/TaskGroup giảm wall-time tiềm năng nhưng cần failure/order/model-busy policy |Không có throughput benchmark hoặc p 95 |
|Không cross-query fusion | Search responses tuple |Không trộn score scales hoặc duplicate provenance ngoài thiết kế |Global RRF /dedup cần policy provenance/rank/budget, benchmark trước thay |Chưa biết chất lượng nhiều câu khi cùng evidence lặp |
|Stop first FAILED |49–55 giữ prefix |Không trình bày missing backend thành no-match thành công |Best-effort partial hoặc retry có thể tăng coverage nhưng phải đổi state semantics |Chưa reliability/SLO study |
|Structured handoff | JudgeHandoff 18–93 |Future Judge có context/options/native outcomes để kiểm sufficiency |Plain text prompt mất machine-checkable consistency; packet quá rộng tăng payload |Không Judge implementation hoặc sufficiency thresholds |
|Technical READY |from_search 76–82 |Tách retrieval success khỏi quyết định pháp lý |Cho Search judge sufficiency sẽ gộp responsibility và cần criteria/model mới |Không legal quality/citation benchmark |
| LangGraph coordination |graph 57–66, executor 28–84 |Có explicit branching/state/lifecycle trước future nodes |Pure async pipeline đơn giản hơn cho 2 nodes nhưng lifecycle/state contracts phải viết riêng |Không chứng minh graph cần cho mọi deployment hoặc durable resume |
|Lazy local model wrappers |retrieval_bootstrap 45–55, adapters |Reuse weights và tránh load nếu chưa dùng path |Eager load/startup warmup tăng startup cost nhưng giảm cold-request risk |Task 4 initial timeout chưa có root-cause decomposition |

Nguồn trực tiếp: [Search](../../../src/applications/tillegal/agents/search/agent.py),[QuerySearch](../../../src/query_search_bootstrap.py),[graph](../../../src/applications/tillegal/graphs/legal_qa.py),[handoff](../../../src/applications/tillegal/state/legal_qa_state.py),[retrieval bootstrap](../../../src/retrieval_bootstrap.py). Actual symbol ranges và snippets ở 10/18.

## Model-free Search không đồng nghĩa model-free request

 Search transport không gọi pretrained model hoặc LLM API. End-to-end request dense/hybrid/rerank có thể invoke local E 5/ CrossEncoder downstream. Cost/latency của request gồm I/O/model work, không thể tuyên bố “ Search miễn phí/gần 0 ms” vì function ngắn. Task 6B chỉ đo test-suite runtime, không benchmark isolated Search latency.

Deterministic orchestration giảm rủi ro tự sinh/biến đổi nội dung ở layer này vì nó không generate text answer. Không loại hallucination/legal interpretation risk của layer khác hoặc dữ liệu nguồn. Content hash integrity chứng minh quan hệ payload/hash ở phạm vi kiểm, không bảo đảm source authentic, current, complete hoặc áp đúng tình huống.

## Các limits có thể tái hiện

- Plan raw dict là alias; extra fields ignore trong parsed model nhưng còn raw output.
- Subquery whitespace có thể qua upstream schema rồi fail tại Request; prebuild eager bảo đảm 0 calls toàn batch nếu invalid.
- Search không revalidate response context; packet validator mới bắt mismatch. Direct consumers phải hiểu trust assumption dependency.
- No global top_k, no dedup, no response fusion; duplicate questions có duplicate calls.
- FAILED giữ successful history nhưng unexpected exception không return partial state.
- Packet properties warnings/errors không tự là top-level JSON fields; native response vẫn giữ details.
- Frozen models không deep-freeze nested metadata; arbitrary object values có thể không JSON serializable.
- State-isolation tests không production SDK thread-safety hoặc multi-tenant authorization.

Các alternative là thảo luận kiến trúc, chưa triển khai và không phải migration plan được tự động thực hiện. Task này chỉ bàn giao kiến thức.
