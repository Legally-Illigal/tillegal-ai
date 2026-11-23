# Test evidence và commands

CWD target D:/DOWNLOAD/tillegal-ai/tillegal-ai-main, .venv Python3.12.16. Không cài dependencies. Commands ngoài sandbox qua approval vì target ngoài writable roots và Windows asyncio socketpair. Source export không Git, nên không claim Git diff.

## Level A/B — nodes, graph, handoff

```powershell
.venv/Scripts/python.exe -B -m pytest -p no:cacheprovider -q tests/graph/test_query_search_workflow.py --junitxml=.docs/agent-development/task-05-langgraph-integration/evidence/graph-junit.xml
```

30 collected/passed, 0 failed/skipped, 2.08s. Lượt đầu26 passed/2.29s, sau thêm4 context/Unicode cases thành 30. [Graph JUnit](evidence/graph-junit.xml) lưu lượt30.

Coverage direct node/routing, stream query→search, clarification chỉ query, exact calls, no-match, real RetrievalService với fake ports4 profiles, native identity và JSON subtype preservation, multi-query failure history, invalid input, Query/Search processing exceptions, typed service timeout, outer deadline, token/caller cancellation, context binding, repeated/concurrent isolation, trusted options, packet tampering/extra fields và Unicode original.

## Level C — regression

```powershell
.venv/Scripts/python.exe -B -m pytest -p no:cacheprovider -q tests/graph tests/unit/framework/test_framework_components.py tests/unit/applications/tillegal/test_query_hardening.py tests/unit/applications/tillegal/test_query_search.py tests/unit/applications/tillegal/test_query_search_multimode.py tests/unit/applications/tillegal/retrieval/test_service.py tests/unit/applications/tillegal/retrieval/test_contracts.py tests/unit/applications/tillegal/retrieval/test_dense_service.py tests/unit/applications/tillegal/retrieval/test_query_encoder.py tests/unit/applications/tillegal/retrieval/test_hybrid_service.py tests/unit/applications/tillegal/retrieval/test_rank_fusion.py tests/unit/applications/tillegal/retrieval/test_reranking.py tests/unit/applications/tillegal/retrieval/test_supabase_vector_repository.py --junitxml=.docs/agent-development/task-05-langgraph-integration/evidence/regression-junit.xml
```

Final320 collected/passed, 0 failed/skipped, 3.82s. [Regression JUnit](evidence/regression-junit.xml). Trước 4 cases cuối có 316 passed/3.95s.30 là subset320; không cộng reruns thành distinct tests mới. Suite offline có framework foundation/approval/executor và Query/Search/Retrieval regression;không live model/DB.

## Level D — một graph BM25 Supabase smoke

```powershell
.venv/Scripts/python.exe -B -X utf8 -c "import runpy; runpy.run_path('.docs/agent-development/task-05-langgraph-integration/evidence/live_smoke.py',run_name='__main__')"
```

Bọc subprocess.run(timeout=60), service default30s, graph deadline35s explicit. Date2026-11-17/top_k5/policyEXPERIMENTAL_ONLY từ artifact e2e-retrieval.json có sẵn. dotenv_values chỉ là mapping cho load_settings, không đổi environment. Hosted LangSmith tracing tắt trong probe. Không load model hoặc chạy lại4 live modes Task 4.

Kết quả3.062241s: graph SEARCH_COMPLETED, lifecycle succeeded, handoff READY, đúng 1 retrieval call, OK/5 evidence, 5 warnings TEMPORAL_METADATA_INCOMPLETE, errors=[], ID/hash checks true, packet JSON round-trip equal. [JSON live](evidence/live-bm25.json). Một sample không là benchmark p95/throughput/legal quality.

## Quality gates

```powershell
.venv/Scripts/ruff.exe check src/applications/tillegal/graphs/legal_qa.py src/applications/tillegal/state/legal_qa_state.py tests/graph/test_query_search_workflow.py .docs/agent-development/task-05-langgraph-integration/evidence/live_smoke.py
.venv/Scripts/ruff.exe format --check src/applications/tillegal/graphs/legal_qa.py src/applications/tillegal/state/legal_qa_state.py tests/graph/test_query_search_workflow.py .docs/agent-development/task-05-langgraph-integration/evidence/live_smoke.py
```

All checks passed;4 files already formatted. Lint đầu sửa1 import-order issue;không có test assertion failure trong Task 5. Một lệnh gộp ghi docs bị Windows từ chối os error206 vì command quá dài, trước khi process chạy;đã tách nhóm và không có source bị viết dở từ lệnh đó.

Checksum xác minh đúng 2 stub runtime đổi, 1 test added, 0deleted;Agents/Retrieval/config/dependencies không đổi. Source fingerprints tại evidence/source_before.json và source_after.json. Scanner cuối kiểm credential values trong bộ nhớ, không in secret;links tương đối được kiểm tồn tại.

NOT TESTED: durable saver/checkpoint resume, production HTTP/ACL, live multi-user load, live Dense/Hybrid/rerank qua graph và legal sufficiency. Concurrent fake tests không chứng minh toàn resource thread safety của native model/DB clients.
