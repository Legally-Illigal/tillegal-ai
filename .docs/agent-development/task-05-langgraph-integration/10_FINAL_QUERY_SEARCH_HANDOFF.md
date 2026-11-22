# Bàn giao cuối phạm vi Query/Search

## Files và version

Hai runtime stubs được hoàn thiện:
- src/applications/tillegal/graphs/legal_qa.py: QuerySearchNodes, compile_query_search_graph, QuerySearchWorkflow.
- src/applications/tillegal/state/legal_qa_state.py: LegalQAState, RetrievalOutcome union, JudgeHandoff v1.

Thêm tests/graph/test_query_search_workflow.py và 12 Markdown cùng evidence/probe Task 5. Source export không Git;manifest_before323 files/after324, đúng 2 changed/1 added/0deleted. Không claim Git diff. Không đổi Agents/RetrievalService/QuerySearch/bootstrap/algorithms/config/dependencies/migrations.

## Application entrypoint

```python
# Application validate/cấp quyền settings và options trước khi compose.
pipeline = create_query_search(settings, options)
workflow = QuerySearchWorkflow(pipeline)  # compile một lần trong lifecycle application
state = await workflow.execute(question, context, timeout_seconds=35)
packet = state["handoff"]
```

35s là deadline smoke đã kiểm, không default của execute. Caller chọn deadline phù hợp, service/models vẫn có deadline riêng. context là ExecutionContext có run/request IDs. Không đưa credentials/clients vào graph state hoặc packet.

CLARIFICATION_REQUIRED: lấy message và kết thúc lượt, packet None. READY: technical retrieval success để Judge tương lai tiếp nhận, không legal sufficiency. NO_MATCH/RETRIEVAL_FAILED: giữ trạng thái riêng, có thể có diagnostic history. Exception/cancel: không có final packet mới;không dùng output run trước.

## Readiness và giới hạn

VERIFIED OFFLINE compile/routing/state/isolation/serialization/subtype và320 regression tests. VERIFIED REAL SUPABASE một BM25 graph smoke OK/5 evidence. PARTIAL prototype handoff readiness;live model graphs, production lifecycle/concurrency/ACL/checkpoint chưa xác minh. Dense cold-start instability Task 4 vẫn là limitation lịch sử, chưa được sửa trong graph task.

Handoff version hóa và validate context. JSON canonical giữ warnings/errors trong responses;properties derive lại. Unknown metadata phải giữ unknown. Frozen model không deep-freeze nested dict/list, caller tránh mutate evidence sau bàn giao. Runtime temporal mentions chưa được reconcile tự động với date options.

## Quyết định cho scope tiếp theo

Judge cần chốt sufficiency, coverage, conditions/exceptions, temporal applicability và xử lý retrieval failures;không suy từ READY hoặc ranking. Persistence cần serializer/version migration, thread/tenant ACL và resume consistency. Application lifecycle cần ownership/close của shared Supabase/model resources cùng load tests. Đây là gaps được ghi nhận, chưa triển khai.

Task 5 kết thúc ở Query/Search và handoff. Không có Judge/Answer/Summary/Citation Verification, HTTP endpoint, DB checkpoint setup hoặc Git write mới. Không truy cập hay ghi vào checkout cũ trong task.
