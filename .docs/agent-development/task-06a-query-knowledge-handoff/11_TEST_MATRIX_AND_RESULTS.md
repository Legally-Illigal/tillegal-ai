# Test matrix và verification hiện tại

## Command đã chạy mới trong Task6a

CWD D:/DOWNLOAD/tillegal-ai/tillegal-ai-main;Python .venv3.12.16,pytest8.4.2 theo environment hiện có. Không install dependencies.

```powershell
.venv/Scripts/python.exe -B -m pytest -p no:cacheprovider -q tests/unit/applications/tillegal/test_query_hardening.py tests/unit/applications/tillegal/test_query_search.py tests/unit/applications/tillegal/test_query_search_multimode.py tests/graph/test_query_search_workflow.py --junitxml=.docs/agent-development/task-06a-query-knowledge-handoff/evidence/focused-junit.xml
```

**120 collected/passed,0 failed/skipped,trong2.23s.** [JUnit](evidence/focused-junit.xml). Đây là focused Query/boundary/graph suite,không whole repository suite. Các con số40/185/275/320 trong task trước là lịch sử hoặc tập khác,không cộng vào120.

| Test classname từ JUnit | Cases mới chạy |
|---|---|
| tests.unit.applications.tillegal.test_query_hardening | 37 |
| tests.unit.applications.tillegal.test_query_search | 12 |
| tests.unit.applications.tillegal.test_query_search_multimode | 41 |
| tests.graph.test_query_search_workflow | 30 |

Bộ hardening hiện tại được mang sang target ở Task3 theo report,không đọc implementation checkout cũ để xác minh Task1. Task0–2 docs không có trong target;không khẳng định đã khôi phục exact27-test historical suite.

## Behavior → test/diagnostic

| Behavior | Regression hiện có | Kind/evidence | Kết quả |
|---|---|---|---|
|Type/length/controls/blank |test_invalid_type,test_length,test_characters,test_blank |Pure Query |PASSED |
|NFC/original và10000-bound |test_unicode_and_original;graph Unicode test |Pure Query + in-memory graph |PASSED |
|Valid/invalid calendar |test_valid_date,test_invalid_date |Parameterized Query |PASSED |
|Temporal year/relative/partial/law ID |test_temporal_semantics |Pure Query |PASSED |
|Intent/domain/six fields |test_contract_and_regressions |Pure Query/schema |PASSED |
|Clarification no calls |test_clarification_no_reads;test_clarification_all_modes;test_graph_clarification_skips_search_node |Mock service,graph stream |PASSED |
|Malformed plan/zero/blank subquery |test_options_and_plan_fail_before_reads;test_invalid_plan_no_calls;boundary-probes |Pydantic+AsyncMock |PASSED/probe reject |
|Plan/response identity giữ |test_response_identity_and_plan_unchanged;graph subtype test |Real service/fake ports |PASSED |
|Graph routing/IDs/isolation/exceptions |test_graph_exact_order_and_no_match_handoff;test_repeated_and_concurrent_requests_are_isolated và graph error cases |Compiled graph/fakes |PASSED |
|All7 topic rules/prefix sensitivity/duplicate baseparts/ISO-year behavior |52 diagnostic cases |Source code thật + sys.settrace + fake graph |OBSERVED;không gọi đây là existing pytest regression |
|State total=False/required clarification/default extras |boundary-probes và schema_probes |Direct runtime introspection/model calls |OBSERVED |

## Sanitized diagnostics

- [diagnose_query.py](evidence/diagnose_query.py) tạo42 cases đầu,Query locals/outputs và graph với FakeRetrieval.
- [supplement_diagnostics.py](evidence/supplement_diagnostics.py) thêm10 cases,bao đủ7 topic phrases và fixed ambiguity patterns.
- [query-traces-complete.json](evidence/query-traces-complete.json) chứa52 distinct synthetic inputs. Không cộng42+52;complete đã bao preliminary42.
- [boundary-probes.json](evidence/boundary-probes.json) ghi malformed-state/schema behavior và inspect signatures.

Chạy bằng Python -B -X utf8 -c với runpy.run_path(...,run_name='__main__') tại target để source imports đúng. Scripts chỉ là diagnostic mới dưới Task6a;không thêm/sửa tests hoặc source. Khi tái chạy nên chọn output directory mới để giữ evidence hiện tại theo chính sách không overwrite reports. Script hiện có tạo filename cố định,không chạy lại để đè artifact đã bàn giao.

Trace runtime chưa được tách timer riêng;không suy Query latency từ2.23s whole suite hoặc execution time Task4 retrieval. sys.settrace chỉ theo understand code object,không formal branch coverage cho comprehensions/Pydantic/native internals. Line union và52 observations bao các branch chính theo mapping,không claim100% path coverage.

## Source-level test index

Excerpts dưới lấy AST từ test files hiện tại,chỉ hiển thị tối đa2 assert mỗi function;file gốc là authority cho parameterization và các assert còn lại.

| File | Function/range | Assertion excerpt thật |
|---|---|---|
| [tests/unit/applications/tillegal/test_query_hardening.py](../../../tests/unit/applications/tillegal/test_query_hardening.py) | test_invalid_type 11–13 | `Xem pytest.raises/context trong body;không suy assertion khi không có ast.Assert.` |
| [tests/unit/applications/tillegal/test_query_hardening.py](../../../tests/unit/applications/tillegal/test_query_hardening.py) | test_length 17–19 | `Xem pytest.raises/context trong body;không suy assertion khi không có ast.Assert.` |
| [tests/unit/applications/tillegal/test_query_hardening.py](../../../tests/unit/applications/tillegal/test_query_hardening.py) | test_blank 23–25 | `Xem pytest.raises/context trong body;không suy assertion khi không có ast.Assert.` |
| [tests/unit/applications/tillegal/test_query_hardening.py](../../../tests/unit/applications/tillegal/test_query_hardening.py) | test_characters 29–31 | `Xem pytest.raises/context trong body;không suy assertion khi không có ast.Assert.` |
| [tests/unit/applications/tillegal/test_query_hardening.py](../../../tests/unit/applications/tillegal/test_query_hardening.py) | test_unicode_and_original 34–42 | `assert first.pop("original") == original / assert second.pop("original") == decomposed` |
| [tests/unit/applications/tillegal/test_query_hardening.py](../../../tests/unit/applications/tillegal/test_query_hardening.py) | test_valid_date 46–49 | `assert plan["temporal_scope"] == [mention] / assert plan["clarification"] is None` |
| [tests/unit/applications/tillegal/test_query_hardening.py](../../../tests/unit/applications/tillegal/test_query_hardening.py) | test_invalid_date 53–57 | `assert plan["temporal_scope"] == ["2020"] / assert plan["clarification"]` |
| [tests/unit/applications/tillegal/test_query_hardening.py](../../../tests/unit/applications/tillegal/test_query_hardening.py) | test_temporal_semantics 73–74 | `assert understand(question)["temporal_scope"] == expected` |
| [tests/unit/applications/tillegal/test_query_hardening.py](../../../tests/unit/applications/tillegal/test_query_hardening.py) | test_contract_and_regressions 77–85 | `assert set(plan) == {"original", "intent", "domain", "temporal_scope", "subqueries", "clarification"} / assert QueryPlan.model_validate(plan).model_dump() == plan` |
| [tests/unit/applications/tillegal/test_query_search.py](../../../tests/unit/applications/tillegal/test_query_search.py) | test_real_service_fake_ports 31–43 | `assert result["plan"] == understand(question) / assert result["status"] == "COMPLETED"` |
| [tests/unit/applications/tillegal/test_query_search.py](../../../tests/unit/applications/tillegal/test_query_search.py) | test_clarification_no_reads 47–52 | `assert result["status"] == "CLARIFICATION_REQUIRED" / assert result["requests"] == result["responses"] == ()` |
| [tests/unit/applications/tillegal/test_query_search.py](../../../tests/unit/applications/tillegal/test_query_search.py) | test_invalid_input 56–60 | `Xem pytest.raises/context trong body;không suy assertion khi không có ast.Assert.` |
| [tests/unit/applications/tillegal/test_query_search.py](../../../tests/unit/applications/tillegal/test_query_search.py) | test_options_and_plan_fail_before_reads 63–76 | `Xem pytest.raises/context trong body;không suy assertion khi không có ast.Assert.` |
| [tests/unit/applications/tillegal/test_query_search.py](../../../tests/unit/applications/tillegal/test_query_search.py) | test_no_match_failure_and_no_fallback 79–85 | `assert asyncio.run(QuerySearch(service(), options()).search("Trích dẫn: thuế"))["responses"][0].status == "NO_MATCH" / assert state["status"] == "FAILED" and len(state["responses"]) == 1` |
| [tests/unit/applications/tillegal/test_query_search.py](../../../tests/unit/applications/tillegal/test_query_search.py) | test_response_identity_and_plan_unchanged 88–95 | `assert state["responses"][0] is response and plan == before` |
| [tests/unit/applications/tillegal/test_query_search.py](../../../tests/unit/applications/tillegal/test_query_search.py) | test_bootstrap_delegates 98–103 | `assert result.retrieval is svc / assert factory.call_args.kwargs["dense_model_path"] is None` |
| [tests/unit/applications/tillegal/test_query_search.py](../../../tests/unit/applications/tillegal/test_query_search.py) | test_no_legacy_imports 106–113 | `assert "ai_core" not in inspect.getsource(agent) / assert "ai_core" not in inspect.getsource(bootstrap)` |
| [tests/unit/applications/tillegal/test_query_search_multimode.py](../../../tests/unit/applications/tillegal/test_query_search_multimode.py) | test_unit_request_mapping_and_no_match_identity 56–76 | `assert result["requests"] == (req,) / assert result["responses"][0] is response` |
| [tests/unit/applications/tillegal/test_query_search_multimode.py](../../../tests/unit/applications/tillegal/test_query_search_multimode.py) | test_clarification_all_modes 81–86 | `assert result["status"] == "CLARIFICATION_REQUIRED" / assert result["requests"] == result["responses"] == ()` |
| [tests/unit/applications/tillegal/test_query_search_multimode.py](../../../tests/unit/applications/tillegal/test_query_search_multimode.py) | test_unit_invalid_options 100–102 | `Xem pytest.raises/context trong body;không suy assertion khi không có ast.Assert.` |
| [tests/unit/applications/tillegal/test_query_search_multimode.py](../../../tests/unit/applications/tillegal/test_query_search_multimode.py) | test_invalid_plan_no_calls 108–112 | `Xem pytest.raises/context trong body;không suy assertion khi không có ast.Assert.` |
| [tests/unit/applications/tillegal/test_query_search_multimode.py](../../../tests/unit/applications/tillegal/test_query_search_multimode.py) | test_unit_bootstrap_preserves_backend_configuration 116–135 | `assert pipeline.options == options(mode) / assert factory.call_args.kwargs == {         "dense_model_path": dense,         "hybrid_config": hybrid,         "rerank_config": rerank,         "timeout_seconds": 30,     }` |
| [tests/unit/applications/tillegal/test_query_search_multimode.py](../../../tests/unit/applications/tillegal/test_query_search_multimode.py) | test_offline_real_dispatch_direct_parity_and_all_metadata 139–182 | `assert plan == before and state["status"] == "COMPLETED" / assert response is recorder.responses[0]` |
| [tests/unit/applications/tillegal/test_query_search_multimode.py](../../../tests/unit/applications/tillegal/test_query_search_multimode.py) | test_offline_no_match_all_modes 186–192 | `assert result["responses"][0].status == "NO_MATCH" / assert result["responses"][0].evidence == ()` |
| [tests/unit/applications/tillegal/test_query_search_multimode.py](../../../tests/unit/applications/tillegal/test_query_search_multimode.py) | test_offline_hybrid_failure_is_not_partial_success 196–211 | `assert result["status"] == "FAILED" and len(result["responses"]) == 1 / assert response.error.category == "DATABASE_FAILURE"` |
| [tests/unit/applications/tillegal/test_query_search_multimode.py](../../../tests/unit/applications/tillegal/test_query_search_multimode.py) | test_offline_missing_e5_no_vector_call 214–218 | `assert result["responses"][0].error.code == "MODEL_NOT_PROVISIONED" / assert dense.calls == []` |
| [tests/unit/applications/tillegal/test_query_search_multimode.py](../../../tests/unit/applications/tillegal/test_query_search_multimode.py) | test_offline_missing_dense_index_no_model_call 221–226 | `assert result["responses"][0].error.code == "INDEX_NOT_FOUND" / assert dense.calls == encoder.calls == []` |
| [tests/unit/applications/tillegal/test_query_search_multimode.py](../../../tests/unit/applications/tillegal/test_query_search_multimode.py) | test_offline_missing_reranker_fallback_explicit 229–238 | `assert result["status"] == "COMPLETED" and response.status == "OK" / assert response.reranking.status == "FALLBACK"` |
| [tests/unit/applications/tillegal/test_query_search_multimode.py](../../../tests/unit/applications/tillegal/test_query_search_multimode.py) | test_offline_total_deadline 242–252 | `assert result["status"] == "FAILED" / assert result["responses"][0].error.code == code` |
| [tests/unit/applications/tillegal/test_query_search_multimode.py](../../../tests/unit/applications/tillegal/test_query_search_multimode.py) | test_offline_total_deadline.SlowEncoder 243–246 | `Xem pytest.raises/context trong body;không suy assertion khi không có ast.Assert.` |
| [tests/unit/applications/tillegal/test_query_search_multimode.py](../../../tests/unit/applications/tillegal/test_query_search_multimode.py) | test_offline_total_deadline.SlowEncoder.encode_query 244–246 | `Xem pytest.raises/context trong body;không suy assertion khi không có ast.Assert.` |
| [tests/unit/applications/tillegal/test_query_search_multimode.py](../../../tests/unit/applications/tillegal/test_query_search_multimode.py) | test_no_legacy_references_in_application_path 255–261 | `assert "ai_core" not in inspect.getsource(module)` |
| [tests/graph/test_query_search_workflow.py](../../../tests/graph/test_query_search_workflow.py) | test_unit_query_node_and_routes 62–74 | `assert service.requests == [] / assert state["plan"] == understand(question)` |
| [tests/graph/test_query_search_workflow.py](../../../tests/graph/test_query_search_workflow.py) | test_unit_search_node_keeps_native_result_and_ids 77–88 | `assert state == before and update["status"] == "NO_MATCH" / assert handoff.responses[0] is service.responses[0]` |
| [tests/graph/test_query_search_workflow.py](../../../tests/graph/test_query_search_workflow.py) | test_graph_clarification_skips_search_node 92–110 | `assert service.requests == [] / assert [next(iter(update)) for update in updates] == ["query"]` |
| [tests/graph/test_query_search_workflow.py](../../../tests/graph/test_query_search_workflow.py) | test_graph_clarification_skips_search_node.run 96–107 | `assert [next(iter(update)) for update in updates] == ["query"] / assert result["status"] == "CLARIFICATION_REQUIRED"` |
| [tests/graph/test_query_search_workflow.py](../../../tests/graph/test_query_search_workflow.py) | test_graph_exact_order_and_no_match_handoff 113–126 | `assert len(service.requests) == 1 / assert set(flow.graph.nodes) == {"__start__", "query", "search"}` |
| [tests/graph/test_query_search_workflow.py](../../../tests/graph/test_query_search_workflow.py) | test_graph_exact_order_and_no_match_handoff.run 117–122 | `assert [next(iter(update)) for update in updates] == ["query", "search"] / assert updates[0]["query"]["status"] == "QUERY_COMPLETED"` |
| [tests/graph/test_query_search_workflow.py](../../../tests/graph/test_query_search_workflow.py) | test_real_service_fake_ports_preserve_subtypes_and_json 130–152 | `assert lifecycle.snapshot.status is ExecutionStatus.SUCCEEDED / assert state["status"] == "SEARCH_COMPLETED" and state["clarification"] is None` |
| [tests/graph/test_query_search_workflow.py](../../../tests/graph/test_query_search_workflow.py) | test_multiple_queries_failure_keeps_prior_response_and_error 155–165 | `assert state["status"] == packet.status == "RETRIEVAL_FAILED" / assert state["search_result"]["status"] == "FAILED"` |
| [tests/graph/test_query_search_workflow.py](../../../tests/graph/test_query_search_workflow.py) | test_invalid_input_preserves_query_error 169–175 | `assert lifecycle.snapshot.status is ExecutionStatus.FAILED / assert service.requests == []` |
| [tests/graph/test_query_search_workflow.py](../../../tests/graph/test_query_search_workflow.py) | test_query_execution_failure_propagates_without_handoff 178–184 | `assert lifecycle.snapshot.status is ExecutionStatus.FAILED and service.requests == []` |
| [tests/graph/test_query_search_workflow.py](../../../tests/graph/test_query_search_workflow.py) | test_unexpected_search_exception_is_execution_failure 187–195 | `assert lifecycle.snapshot.status is ExecutionStatus.FAILED` |
| [tests/graph/test_query_search_workflow.py](../../../tests/graph/test_query_search_workflow.py) | test_unexpected_search_exception_is_execution_failure.Broken 188–190 | `Xem pytest.raises/context trong body;không suy assertion khi không có ast.Assert.` |
| [tests/graph/test_query_search_workflow.py](../../../tests/graph/test_query_search_workflow.py) | test_unexpected_search_exception_is_execution_failure.Broken.search 189–190 | `Xem pytest.raises/context trong body;không suy assertion khi không có ast.Assert.` |
| [tests/graph/test_query_search_workflow.py](../../../tests/graph/test_query_search_workflow.py) | test_typed_retrieval_timeout_becomes_failed_handoff 198–213 | `assert state["status"] == "RETRIEVAL_FAILED" / assert state["handoff"].errors[0].category == "TIMEOUT"` |
| [tests/graph/test_query_search_workflow.py](../../../tests/graph/test_query_search_workflow.py) | test_typed_retrieval_timeout_becomes_failed_handoff.Deadline 199–209 | `Xem pytest.raises/context trong body;không suy assertion khi không có ast.Assert.` |
| [tests/graph/test_query_search_workflow.py](../../../tests/graph/test_query_search_workflow.py) | test_typed_retrieval_timeout_becomes_failed_handoff.Deadline.search 200–209 | `Xem pytest.raises/context trong body;không suy assertion khi không có ast.Assert.` |
| [tests/graph/test_query_search_workflow.py](../../../tests/graph/test_query_search_workflow.py) | test_outer_timeout_and_cancellation_propagate 216–249 | `assert lifecycle.snapshot.status is ExecutionStatus.FAILED and service.cancelled / assert lifecycle.snapshot.status is ExecutionStatus.CANCELLED and service.cancelled` |
| [tests/graph/test_query_search_workflow.py](../../../tests/graph/test_query_search_workflow.py) | test_outer_timeout_and_cancellation_propagate.Waiting 217–228 | `Xem pytest.raises/context trong body;không suy assertion khi không có ast.Assert.` |
| [tests/graph/test_query_search_workflow.py](../../../tests/graph/test_query_search_workflow.py) | test_outer_timeout_and_cancellation_propagate.Waiting.__init__ 218–221 | `Xem pytest.raises/context trong body;không suy assertion khi không có ast.Assert.` |
| [tests/graph/test_query_search_workflow.py](../../../tests/graph/test_query_search_workflow.py) | test_outer_timeout_and_cancellation_propagate.Waiting.search 223–228 | `Xem pytest.raises/context trong body;không suy assertion khi không có ast.Assert.` |
| [tests/graph/test_query_search_workflow.py](../../../tests/graph/test_query_search_workflow.py) | test_outer_timeout_and_cancellation_propagate.run 230–247 | `assert lifecycle.snapshot.status is ExecutionStatus.FAILED and service.cancelled / assert lifecycle.snapshot.status is ExecutionStatus.CANCELLED and service.cancelled` |
| [tests/graph/test_query_search_workflow.py](../../../tests/graph/test_query_search_workflow.py) | test_caller_task_cancellation_propagates 252–271 | `assert lifecycle.snapshot.status is ExecutionStatus.CANCELLED` |
| [tests/graph/test_query_search_workflow.py](../../../tests/graph/test_query_search_workflow.py) | test_caller_task_cancellation_propagates.run 253–269 | `assert lifecycle.snapshot.status is ExecutionStatus.CANCELLED` |
| [tests/graph/test_query_search_workflow.py](../../../tests/graph/test_query_search_workflow.py) | test_caller_task_cancellation_propagates.run.Waiting 256–259 | `Xem pytest.raises/context trong body;không suy assertion khi không có ast.Assert.` |
| [tests/graph/test_query_search_workflow.py](../../../tests/graph/test_query_search_workflow.py) | test_caller_task_cancellation_propagates.run.Waiting.search 257–259 | `Xem pytest.raises/context trong body;không suy assertion khi không có ast.Assert.` |
| [tests/graph/test_query_search_workflow.py](../../../tests/graph/test_query_search_workflow.py) | test_repeated_and_concurrent_requests_are_isolated 274–296 | `assert failed["status"] == "RETRIEVAL_FAILED" / assert first["errors"] == second["errors"] == []` |
| [tests/graph/test_query_search_workflow.py](../../../tests/graph/test_query_search_workflow.py) | test_repeated_and_concurrent_requests_are_isolated.run 278–294 | `assert failed["status"] == "RETRIEVAL_FAILED" / assert first["errors"] == second["errors"] == []` |
| [tests/graph/test_query_search_workflow.py](../../../tests/graph/test_query_search_workflow.py) | test_untrusted_state_options_do_not_override_injection 299–307 | `assert service.requests[0].mode == "bm25" / assert update["handoff"].options == options("bm25")` |
| [tests/graph/test_query_search_workflow.py](../../../tests/graph/test_query_search_workflow.py) | test_handoff_rejects_inconsistent_or_extra_fields 314–318 | `Xem pytest.raises/context trong body;không suy assertion khi không có ast.Assert.` |
| [tests/graph/test_query_search_workflow.py](../../../tests/graph/test_query_search_workflow.py) | test_graph_context_and_no_judge_dependency 321–335 | `assert "ai_core" not in source / assert "agents.judge" not in source` |
| [tests/graph/test_query_search_workflow.py](../../../tests/graph/test_query_search_workflow.py) | test_graph_context_and_no_judge_dependency.Bound 326–329 | `Xem pytest.raises/context trong body;không suy assertion khi không có ast.Assert.` |
| [tests/graph/test_query_search_workflow.py](../../../tests/graph/test_query_search_workflow.py) | test_graph_context_and_no_judge_dependency.Bound.search 327–329 | `assert current_execution_context().run_id == "run-1"` |
| [tests/graph/test_query_search_workflow.py](../../../tests/graph/test_query_search_workflow.py) | test_handoff_context_mismatch_is_rejected 339–349 | `Xem pytest.raises/context trong body;không suy assertion khi không có ast.Assert.` |
| [tests/graph/test_query_search_workflow.py](../../../tests/graph/test_query_search_workflow.py) | test_unicode_original_survives_graph_and_handoff 352–360 | `assert state["question"] == state["plan"]["original"] == state["handoff"].question == question / assert service.requests[0].query == "nghỉ phép"` |

## Giới hạn verification

Không DB/live/LLM/model inference trong Task6a. Fake no-match không có nghĩa corpus thật không có match. Không có human-approved intent/domain benchmark hoặc general ambiguity accuracy. Một số edge mới chỉ diagnostic,không tồn tại dedicated regression test trong application test suite. Giữ rõ SOURCE INSPECTION/OBSERVED DIAGNOSTIC/PYTEST PASSED.
