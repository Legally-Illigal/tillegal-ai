# Dependency injection, construction và lifecycle

## Wiring authority

[QuerySearch16–21/create_query_search24–42](../../../src/query_search_bootstrap.py) giữ retrieval: RetrievalService và options: SearchOptions trong frozen dataclass. Frozen không làm service immutable hoặc tự thread-safe.

create_query_search thứ tự:validate options 34; gọi create_retrieval_service 35–41 với settings, dense_model_path, hybrid_config, rerank_config, timeout_seconds; return QuerySearch 42. Tất cả opt-ins đi nguyên qua factory; test_bootstrap_delegates và test_unit_bootstrap_preserves_backend_configuration assert đúng kwargs. Không có algorithm được thay ở đây.

[create_retrieval_service22–70](../../../src/retrieval_bootstrap.py):

| Block | Object được tạo | Khi nào/reuse/owner |
|---|---|---|
|35–36 |Missing config guard |Trước client allocation; URL/key thiếu→ValueError |
|37–41 | Supabase client |Mỗi factory invocation tạo 1; persist_session= False, auto_refresh_token= False, HTTP 10 s; giữ qua repositories |
|42–44 | Dense dependencies defaults None |Không model nếu không opt-in |
|45–50 | Supabase VectorRepository, Dense IndexRepository, E 5 QueryEncoder |Chỉ khi dense_model_path được supplied; wrapper chưa load weights |
|51–55 | LocalCrossEncoder |Chỉ rerank config enabled; wrapper giữ config/lock, load lazy |
|56–70 | RetrievalService + sparse/chunk/source/index read adapters/tokenizer |Container service giữ để các Search requests dùng lại; không tạo mới mỗi subquery |

Default service index names từ service 49–50:vbpl-bm25-unicode-v1 vàvbpl-multilingual-e 5-small-v1. Search không chọn index theo domain/intent. Model/data readiness được kiểm downstream, kể cả wrapper đã construct thành công.

## Where configuration originates

Application phải cung cấp SearchOptions:mode/ top_k /date/policies; factory không lấy từ user question. Supabase Settings từ config loader/.env mapping của application hoặc harness, không in credential. Production HTTP Query / Search endpoint/lifespan wiring chưa được chứng minh chỉ bởi factory này; target chat route còn stub. Không hứa singleton toàn process hoặc dependency cache nếu application tạo factory nhiều lần.

 Hybrid Config điều khiển RRF /candidate budgets. RerankConfig điều khiển enabled/pool/path/timeouts. Dense path explicit opt-in. Rerank enabled không tự đảm bảo Dense cũng có path; misconfiguration có thể được service classify MODE_NOT_CONFIGURED. Wrapper wiring và ready-to-serve khác nhau.

## Model lifecycle đủ để hiểu Search boundary

[E5QueryEncoder27–101](../../../src/integrations/embeddings/e5_query_encoder.py):__init__ giữ path, _model= None và threading.Lock; encode_query 40–44 dùng to_thread; _get_model 46–67 lazy load local_files_only trên lần inference đầu; _encode 69–101 acquire lock nonblocking, MODEL_BUSY nếu đang dùng; giữ model để reuse.

[LocalCrossEncoder12–100](../../../src/integrations/embeddings/cross_encoder_reranker.py):wrapper giữ _model/_tokenizer= None /Lock; score_pairs 19–20 to_thread; _score 46–100 lazy _load và nonblocking lock. Cancellation của await không release lock của running worker; worker finally mới release. Rerank MODEL_BUSY có thể dẫn FALLBACK được warning theo helper policy.

Những ranges này phải đối chiếu source index 18 cho actual function boundaries; không giả mọi request tạo SentenceTransformer /torch model mới. Factory tạo wrapper, first-use model load là hai thời điểm khác nhau. Task 6B không chạy các local model này.

## Graph lifecycle và concurrency

Workflow.__init__72–74 compile graph và tạo executor một lần theo workflow instance. Nodes giữ shared pipeline. Workflow.execute 84–88 tạo fresh state mỗi run. Search tạo local request/response containers, không cache mutable result global.

Shared resources gồm service, client/repos, tokenizer, encoder/scorer và configs. [SupabaseRpcRepository.call_rpc21–27](../../../src/integrations/database/repositories/rpc.py) chạy sync SDK qua to_thread. Locks cho model không tự chứng minh Supabase SDK thread-safety hoặc tenant isolation. Fake graph repeated/concurrent tests kiểm state/IDs/errors, không benchmark concurrent native inference/connectionpool.

Không có close/aclose/shutdown trong QuerySearch / Search factory path đã inspect. Việc giải phóng client/thread/model theo production lifespan vẫn cần owner policy riêng; không suy đã hoàn tất từ in-memory tests. HTTP timeout 10 s bound I/O không bảo đảm mọi cancellation đã dừng tức thì mọi resource.

Nguồn runtime [executor28–102](../../../src/framework/runtime/executor.py),[context17–71](../../../src/framework/runtime/execution_context.py); method ranges AST ở 18. No persistent saver/tenant ACL trong graph path. Không chạy bootstrap thật trong diagnostics để tránh network/client initialization không cần thiết; factory tests mock construction, service tests fake ports.
