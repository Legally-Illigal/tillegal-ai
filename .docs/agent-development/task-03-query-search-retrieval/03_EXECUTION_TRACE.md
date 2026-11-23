# Trace theo source thật

Ranges lấy AST sau Ruff format. Path tương đối với integration checkout.

| File | Class/function | Dòng |
|---|---|---|
| [src/applications/tillegal/agents/query/agent.py](../../../src/applications/tillegal/agents/query/agent.py) | QueryInputError | 11–12 |
| [src/applications/tillegal/agents/query/agent.py](../../../src/applications/tillegal/agents/query/agent.py) | Subquery | 15–17 |
| [src/applications/tillegal/agents/query/agent.py](../../../src/applications/tillegal/agents/query/agent.py) | QueryPlan | 20–26 |
| [src/applications/tillegal/agents/query/agent.py](../../../src/applications/tillegal/agents/query/agent.py) | understand | 29–95 |
| [src/applications/tillegal/agents/search/agent.py](../../../src/applications/tillegal/agents/search/agent.py) | SearchOptions | 13–28 |
| [src/applications/tillegal/agents/search/agent.py](../../../src/applications/tillegal/agents/search/agent.py) | SearchState | 31–35 |
| [src/applications/tillegal/agents/search/agent.py](../../../src/applications/tillegal/agents/search/agent.py) | search | 38–56 |
| [src/applications/tillegal/agents/search/agent.py](../../../src/applications/tillegal/agents/search/agent.py) | nonblank_policies | 25–28 |
| [src/query_search_bootstrap.py](../../../src/query_search_bootstrap.py) | QuerySearch | 16–21 |
| [src/query_search_bootstrap.py](../../../src/query_search_bootstrap.py) | create_query_search | 24–42 |
| [src/query_search_bootstrap.py](../../../src/query_search_bootstrap.py) | search | 20–21 |
| [src/retrieval_bootstrap.py](../../../src/retrieval_bootstrap.py) | create_retrieval_service | 22–70 |
| [src/application/services/retrieval_service.py](../../../src/application/services/retrieval_service.py) | _ChunkRow | 55–69 |
| [src/application/services/retrieval_service.py](../../../src/application/services/retrieval_service.py) | _SourceRow | 72–87 |
| [src/application/services/retrieval_service.py](../../../src/application/services/retrieval_service.py) | _SparseIndex | 90–117 |
| [src/application/services/retrieval_service.py](../../../src/application/services/retrieval_service.py) | _DenseIndex | 120–136 |
| [src/application/services/retrieval_service.py](../../../src/application/services/retrieval_service.py) | _failure | 139–147 |
| [src/application/services/retrieval_service.py](../../../src/application/services/retrieval_service.py) | RetrievalService | 150–724 |
| [src/application/services/retrieval_service.py](../../../src/application/services/retrieval_service.py) | aware_timestamp | 111–114 |
| [src/application/services/retrieval_service.py](../../../src/application/services/retrieval_service.py) | identity | 116–117 |
| [src/application/services/retrieval_service.py](../../../src/application/services/retrieval_service.py) | identity | 134–136 |
| [src/application/services/retrieval_service.py](../../../src/application/services/retrieval_service.py) | __init__ | 157–190 |
| [src/application/services/retrieval_service.py](../../../src/application/services/retrieval_service.py) | search | 192–305 |
| [src/application/services/retrieval_service.py](../../../src/application/services/retrieval_service.py) | _prepare_sparse_terms | 307–317 |
| [src/application/services/retrieval_service.py](../../../src/application/services/retrieval_service.py) | _search_sparse | 319–343 |
| [src/application/services/retrieval_service.py](../../../src/application/services/retrieval_service.py) | _hydrate_sparse_hits | 345–409 |
| [src/application/services/retrieval_service.py](../../../src/application/services/retrieval_service.py) | _check_eligibility | 412–435 |
| [src/application/services/retrieval_service.py](../../../src/application/services/retrieval_service.py) | _make_evidence | 438–467 |
| [src/application/services/retrieval_service.py](../../../src/application/services/retrieval_service.py) | _evidence_warnings | 470–490 |
| [src/application/services/retrieval_service.py](../../../src/application/services/retrieval_service.py) | _read_and_validate_index | 492–533 |
| [src/application/services/retrieval_service.py](../../../src/application/services/retrieval_service.py) | _check_index_unchanged | 535–553 |
| [src/application/services/retrieval_service.py](../../../src/application/services/retrieval_service.py) | _read_dense_index | 555–598 |
| [src/application/services/retrieval_service.py](../../../src/application/services/retrieval_service.py) | _check_dense_index_unchanged | 600–617 |
| [src/application/services/retrieval_service.py](../../../src/application/services/retrieval_service.py) | _map_dense_evidence | 619–724 |
| [src/application/services/retrieval_service.py](../../../src/application/services/retrieval_service.py) | run_hybrid | 197–208 |

## Vai trò từng hàm mới/được chuyển

- QueryInputError: subtype ValueError, lỗi input không chứa câu hỏi.
- Subquery và QueryPlan: validation output theo Task 1; không thêm public fields.
- understand: validate type/length/control, NFC, split/prefix/time/topic, date validation, model_dump. Caller QuerySearch.search, output plan dict.
- SearchOptions.nonblank_policies: validator strip/dedup tuple, blank gây ValueError/Pydantic ValidationError. Caller model validation.
- SearchState: mô tả bốn trường kết quả; TypedDict không tự validate runtime.
- search: nhận plan/service/options, validate, chặn clarification, tạo requests bằng options.model_dump, await service, giữ response object, dừng FAILED. Không đổi UnifiedEvidence.
- QuerySearch dataclass: giữ dependency service/options theo instance, không shared mutable result.
- QuerySearch.search: nhận question, gọi understand rồi search. QueryInputError propagate; không gọi DB nếu Query yêu cầu làm rõ hoặc invalid.
- create_query_search: validate options rồi gọi create_retrieval_service với settings và model/config/deadline, trả QuerySearch. Không tự đọc .env, không chọn policy/date, không migrations.

Live trace: script nạp dotenv vào mapping (không sửa os.environ), load_settings lấy SupabaseSettings; đọc date/policy/top_k từ artifact explicit; tạo options BM25; create_query_search → QuerySearch.search → service tokenization → sparse RPC → hydrate chunk/source → typed response. Outer test deadline 20s, service deadline 15s. Model path None nên không load E5/reranker. Chỉ in status/count/warning codes/error code, không in credential hoặc raw upstream error.
