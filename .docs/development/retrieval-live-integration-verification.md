> Publication note: the saved retrieval-e2e-evidence.json contains 8 scenarios: six service scenarios and CLI BM25/Dense. Historical claims below about CLI Hybrid or live fault scenarios are not corroborated by that artifact. No live scenarios were rerun for this publication.

# Retrieval live integration verification — 2026-11-14

## Kết luận

**Chưa có bằng chứng Retrieval tìm được dữ liệu VBPL thật trên Supabase.**
Phiên này xác minh source, SQL migration trong repository, metadata checkpoint local và unit tests;
không kết nối database. Không coi thiếu kết nối là lỗi thuật toán hoặc chứng minh database rỗng.

| Nhánh | Kết luận live | Mức bằng chứng hiện có | Blocker |
|---|---|---|---|
| BM25 | **BLOCKED** | UNIT_VERIFIED; RUNTIME_UNVERIFIED | Chưa xác định target project, cấu hình kết nối trong process và deployed read permissions/corpus/index |
| Dense | **BLOCKED** | UNIT_VERIFIED; RUNTIME_UNVERIFIED | Các blocker DB của BM25; chưa đối chiếu revision checkpoint với provenance stored embeddings |
| Hybrid | **BLOCKED** | UNIT_VERIFIED; RUNTIME_UNVERIFIED | Chưa có BM25 và Dense LIVE_INTEGRATION_VERIFIED |

**QUALITY_NOT_EVALUATED** cho cả ba nhánh. Không có kết luận Hybrid tốt hơn BM25/Dense.
Không có nhánh live FAIL: chưa thực thi truy vấn live để đánh giá kết quả.

## 1. Environment và nguồn bằng chứng

- Ngày: 2026-11-14, timezone Asia/Saigon.
- Workspace: `<WORKSPACE>`; main source: `<SOURCE_ROOT>`.
- Shell: PowerShell trên Windows; interpreter dùng `.venv/Scripts/python.exe` có sẵn trong main.
- Bản main không có Git repository nhận diện được; `git -C tillegal-ai-main status --short`
  trả `not a git repository`. Không đưa ra xác nhận Git diff/commit.
- Đã đối chiếu báo cáo Task 4 (`bm25-retrieval-mvp.md`), Task 5
  (`task5-retrieval-implementation.md`), Task 6 (`task6-hybrid-retrieval.md`),
  `known_issues.md` và source được nêu bên dưới.
- **Không tìm thấy Task 2 — Database Readiness Audit hoặc bộ SQL B1–B8** trong workspace.
  Đã tìm tên file và nội dung Markdown/SQL, kể cả thư mục ẩn, loại trừ dependencies/cache và secrets.
  Vì vậy không thể xác nhận đã đọc/chạy đúng SQL B1–B8 gốc. Ma trận mục 3 là checklist yêu cầu
  hiện tại, không phải bản phục dựng hay kết quả của B1–B8.
- Chỉ kiểm tra sự tồn tại của tên biến môi trường, không lấy/in giá trị:

| Biến process | Hiện diện |
|---|---|
| SUPABASE_URL | Không |
| SUPABASE_SERVICE_ROLE_KEY | Không |
| SUPABASE_ANON_KEY | Không |
| DATABASE_URL | Không |
| CONFIG_FILE | Không |
| HF_HOME / HUGGINGFACE_HUB_CACHE / HF_HUB_CACHE / SENTENCE_TRANSFORMERS_HOME | Không |

File `.env` tồn tại trong main nhưng **không mở, parse hoặc load**. Không mở cấu hình
YAML để tìm credentials. Sự tồn tại của `.env` không chứng minh CLI nhận được cấu hình:
CLI gọi `load_settings(environ=os.environ)`, nên bỏ qua nhánh `load_dotenv`.
Không có Supabase/database connector thích hợp trong các tools sẵn dùng.

**Target project/database: CHƯA XÁC ĐỊNH.** Không suy project từ model cache, tên repo
hoặc giá trị cấu hình giả trong unit tests. Không xác nhận cấu hình YAML có/không chứa target;
chưa có target và phương thức truy cập an toàn được kiểm chứng cho phiên này.

## 2. Phase 1 — Dependency audit

### Cấu hình và entry point

- `scripts/search_legal_chunks.py` → `src/retrieval_bootstrap.py` → `RetrievalService`.
- HTTP retrieval cần `SUPABASE_URL` và API key. `SupabaseSettings.api_key` ưu tiên
  service-role key, sau đó anon key. Source grants hiện tại chỉ cho `service_role`
  thực thi các retrieval RPC; anon key được parser chấp nhận không đồng nghĩa có quyền search.
- `DATABASE_URL` không bắt buộc cho HTTP retrieval, nhưng cần cho phương án audit PostgreSQL
  trực tiếp nếu được cấp. Không gọi application startup, auto-migration hoặc workers.
- Bootstrap tạo SDK client với `persist_session=False`, `auto_refresh_token=False`,
  PostgREST timeout 10 giây. Service mặc định deadline 30 giây.
- Request cần query, mode, top-k, `as_of_date` và allowlist `allowed_usage_policies`.
  Không tự chọn policy/date để ép có hits khi chưa biết dữ liệu thật.

### Index configuration trong source

Tên dưới đây là constants/defaults trong `retrieval_service.py` và
`vbpl_markdown_indexing_service.py`, không phải index đã quan sát trên database:

| Nhánh | Index name | Readiness/config gate |
|---|---|---|
| BM25 | `vbpl-bm25-unicode-v1` | READY; version v1; BM25; tokenizer `unicode-nfc-lower-v1`; language `simple`; document count và average length > 0; k1/b hợp lệ |
| Dense | `vbpl-multilingual-e5-small-v1` | READY; version v1; provider sentence-transformers; model intfloat/multilingual-e5-small; 384 chiều; cosine; normalized và prefixes tương thích |
| Hybrid | Hai index trên | Mặc định RRF k=60, budgets BM25/Dense=20/20; STRICT, tuần tự, không fallback |

CLI hiện không cung cấp flags thay tên index; service constructor có tham số tên index.
Không đổi tên hoặc config trong nhiệm vụ này.

### Bảng và read RPC

| Thành phần | Bảng phụ thuộc |
|---|---|
| Source/hydration | `source_documents`, `retrieval_chunks`; chunk mang `document_structure_id` để truy provenance |
| Sparse search | `sparse_indexes`, `sparse_chunk_documents`, `sparse_postings`, chunks và sources |
| Dense search | `dense_indexes`, `dense_chunk_embeddings`, chunks và sources |

| RPC mà đường retrieval sử dụng | Signature theo migrations local | Hành vi source |
|---|---|---|
| get_sparse_index | `(p_index_name TEXT)` | SELECT index metadata |
| search_sparse_legal_chunks | `(p_terms TEXT[], p_sparse_index_name TEXT, p_top_k INTEGER, p_as_of_date DATE, p_usage_policies TEXT[])` | SELECT ranked chunk UUID/score |
| get_retrieval_chunks | `(p_chunk_ids UUID[])` | SELECT stored chunks |
| get_source_document | `(p_source_document_id UUID)` | SELECT source metadata |
| get_dense_index | `(p_index_name TEXT)` | SELECT index metadata |
| search_legal_chunks | `(p_query_embedding vector, p_dense_index_name TEXT, p_top_k INTEGER, p_as_of_date DATE, p_usage_policies TEXT[])` | SELECT content/source/similarity |

Các definitions trên là STABLE, SECURITY INVOKER trong source. Chưa kiểm tra definitions,
overloads, grants, RLS hoặc PostgREST schema cache của database triển khai.

Migration lineage quan trọng:

- `20261028170000_unified_rag_storage.sql`: bảng, hashes, sparse/dense storage và RLS.
- `20261031190000_rag_repository_operations.sql`: getters, sparse search và grants.
- `20261107230000_simplify_retrieval_schema.sql`: thay search signatures cũ 9 tham số bằng
  5 tham số; loại các governance columns cũ khỏi source schema.
- `20261111130000_multilingual_e5_embeddings.sql`: vector storage không cố định typmod,
  partial HNSW 384/1536 và Dense RPC phân nhánh dimension.
- `20261111163000_restore_parsed_index_stale_helpers.sql`: có trong danh sách local migrations;
  không gọi helpers cập nhật status.

Source search hiện lọc `usage_policy = ANY(p_usage_policies)` và effective date inclusive;
NULL date không loại source. Không còn nhận bốn governance allowlists cũ.
Nếu B1–B8 hoặc database thực còn dùng schema/signatures cũ thì cần đối chiếu trước khi chạy;
đây là rủi ro version mismatch, **chưa phải lỗi deployment đã quan sát**.

SQL definitions local đã được đọc tĩnh; không chạy PostgreSQL parser hoặc SQL trên server.
**Không gắn nhãn SQL_VERIFIED cho deployed database.**

## 3. Phase 2 — Database readiness: BLOCKED

**Dữ liệu đã crawl ≠ dữ liệu đã chunk ≠ dữ liệu đã index.** Có source record không chứng minh
có retrieval chunks; có chunks không chứng minh có postings/vectors READY.
Mọi số liệu dưới đây là UNKNOWN, không phải 0.

| Hạng mục phải kiểm chứng read-only | Kết quả phiên này |
|---|---|
| Target project, database, role, schema/migration deployment | UNKNOWN / chưa kết nối |
| Deployed RPC signatures/definitions và read-only behavior | UNKNOWN |
| Tổng source_documents; số sources VBPL, source IDs/URLs/snapshot provenance | UNKNOWN |
| Tổng retrieval_chunks; số chunks thuộc VBPL; nguồn có/chưa có chunks | UNKNOWN |
| sparse_indexes/dense_indexes tồn tại trên server, index IDs/names | UNKNOWN |
| Index statuses READY/STALE/BUILDING/FAILED/DISABLED | UNKNOWN |
| Distinct chunks INDEXED có postings theo từng sparse index; coverage trên corpus/VBPL | UNKNOWN |
| Sparse document_count, total_token_count, avg length, DF/TF/positions và orphan rows | UNKNOWN |
| content_sha256 khớp UTF-8 content; sparse indexed_text_sha256 khớp content | UNKNOWN |
| Dense INDEXED vectors non-NULL, 384 chiều, finite/nonzero/normalized; coverage | UNKNOWN |
| Dense embedded_text_sha256 khớp SHA-256 của `passage: ` + content | UNKNOWN |
| Dense model/provider/version/revision, prefix/preprocessing metadata | UNKNOWN |
| Policy distribution, date eligibility, NULL/invalid date boundaries | UNKNOWN |
| Application-role EXECUTE/SELECT, RLS/policies, SECURITY INVOKER visibility | UNKNOWN |

Coverage phải tính distinct chunk UUID theo index, phân biệt toàn corpus và VBPL; không dùng
số postings làm số chunks và không dùng status READY thay bằng chứng coverage/hash thực tế.
Nếu role trả 0 rows, phải loại trừ RLS/quyền/filters trước khi kết luận database rỗng.
Role audit SQL và role HTTP search có thể khác nhau; một role đọc được không chứng minh role kia có quyền.

Không có SQL live, count query, RPC hoặc Storage request nào được chạy trong phiên này.
Không gọi `refresh_dense_index_status`, upsert, save, ingestion hoặc indexing RPC.

## 4. Phase 3 — BM25 live input/output: BLOCKED

| Bước | Bằng chứng live |
|---|---|
| Chọn chunk VBPL thực có postings | Chưa thể chọn; UUID UNKNOWN |
| Terms/query từ postings | UNKNOWN; không dùng query giả làm input live |
| Index/date/policy | Tên index từ source; date/policy hợp lệ với corpus UNKNOWN |
| search_sparse_legal_chunks output: IDs/order/scores | NOT_RUN |
| RetrievalService/CLI BM25 output | NOT_RUN |
| RPC ↔ service ranking/score equality | NOT_RUN |
| Hydration content/source identity/metadata/hash | NOT_RUN |
| No-write verification trên live request | NOT_RUN; không có live request |

Chưa quan sát empty search hoặc lỗi RPC/hydration. Không gán nguyên nhân vào postings,
filters, permissions hoặc thuật toán. Khi được mở chặn, lấy terms từ postings đã tồn tại,
giữ cùng top-k/date/policy và đối chiếu IDs/order/scores, rồi content hash/source metadata.

## 5. Phase 4 — Dense checkpoint và live input/output: BLOCKED

Checkpoint local quan sát được tại:

```text
C:\Users\Admin\.cache\huggingface\hub\models--intfloat--multilingual-e5-small\snapshots\614241f622f53c4eeff9890bdc4f31cfecc418b3
```

Đã kiểm tra tồn tại: `model.safetensors`, `config.json`, `modules.json`,
`sentence_bert_config.json`, `1_Pooling/config.json`, `tokenizer.json`,
`tokenizer_config.json`, `sentencepiece.bpe.model`.
Đã đọc metadata không chứa credentials:

| Metadata local | Quan sát |
|---|---|
| Snapshot directory revision | `614241f622f53c4eeff9890bdc4f31cfecc418b3` |
| sentence_bert_config | max_seq_length=512, do_lower_case=false |
| Pooling | word_embedding_dimension=384; mean tokens=true; CLS/max/mean_sqrt_len=false |
| Modules | Transformer → Pooling → Normalize |

Đây là bằng chứng metadata/path local; không xác thực weights bằng upstream checksum và
không chứng minh stored embeddings dùng revision này.
Query encoder source yêu cầu local directory, CPU, `local_files_only=True`,
`trust_remote_code=False`, input `query: ` + query.strip(), `prompt=""`,
`normalize_embeddings=True`; validate 384 finite values và |L2 norm − 1| ≤ 1e-4.
Không pin/so revision hash trong encoder.

Ingestion source chọn model name nhưng không pin revision khi load; metadata index được
ghi gồm normalized/passages/query prefixes, không có revision. Điều này là **khoảng trống
provenance trong source**, không chứng minh database thực không có metadata bổ sung.
Để xác nhận compatibility cần deployed index/vector metadata hoặc manifest tạo corpus,
revision/weights identity và preprocessing/prefixes tương ứng checkpoint local.
Dimension và model name trùng nhau chưa đủ.

| Bước | Bằng chứng live |
|---|---|
| Stored index/vector metadata, valid vectors | UNKNOWN |
| Local checkpoint ↔ corpus revision compatibility | BLOCKED |
| Chạy encoder thật cho live query; dimension/norm thực | NOT_RUN trong task này theo prerequisite gate |
| Vector RPC input/query/output, IDs/similarity | NOT_RUN |
| Dense RetrievalService/CLI evidence/hydration | NOT_RUN |

Không download model, không gọi passage embedder/indexer. Local encoder smoke của Task 5
là bằng chứng lịch sử trong báo cáo đó, không được tính là lần live verification của task này.
Technical smoke test cũng không thay semantic relevance evaluation.

## 6. Phase 5 — Hybrid live input/output: BLOCKED

Chưa đạt prerequisite BM25 + Dense live PASS nên không chạy Hybrid trên database.

- Cùng query/date/policy, rankings BM25/Dense/Hybrid: NOT_RUN.
- Independent RRF recomputation, UUID dedup, final evidence identity trên dữ liệu thật: NOT_RUN.
- Một backend không sẵn sàng trên live environment: NOT_RUN; không đổi status/index để tạo lỗi.
- Unit tests hiện có kiểm tra strict failure và zero partial evidence khi backend lỗi.
  Kết quả này chỉ UNIT_VERIFIED.
- Khi đủ điều kiện, so hai candidate lists đúng budgets và tính độc lập
  `sum(1 / (60 + rank_backend))`, tie theo UUID, truncate top-k và đối chiếu content/provenance.
  Không dùng raw BM25/cosine scores để tính lại RRF.

## 7. Tests và lỗi thực thi

Command chạy từ main với interpreter hiện có:

```powershell
.venv/Scripts/python.exe -m pytest tests/unit/applications/tillegal/retrieval tests/unit/integrations/database/test_repositories.py -q -p no:cacheprovider --tb=no
```

- Đặt `PYTHONDONTWRITEBYTECODE=1`, `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1` trong child process.
- Lần đầu trong sandbox: output 7 dấu pass rồi không tiến triển; đã interrupt, exit 1.
  Không có test summary/stack trace để xác định chính xác nguyên nhân. Các báo cáo Task 4/6
  đã ghi nhận hạn chế asyncio/socketpair trên Windows sandbox; đây là giả thuyết phù hợp,
  không phải chẩn đoán stack trace mới của phiên này.
- Chạy lại cùng focused suite ngoài sandbox qua execution approval, dùng subprocess timeout
  60 giây: **200 passed in 2.94s**, exit 0; không fail/skip.
- Không chạy lại toàn bộ 360-test suite; 360 là kết quả lịch sử Task 6, không phải kết quả task này.
- Suite dùng fake ports/RPC responses và fake query model; kiểm contracts, service, encoder,
  CLI, ranking/fusion, hydration integrity, backend failures và repository parameter mapping.
- Existing cold-import guard chặn model/worker imports/network connects; CLI unit test
  kiểm không gọi dotenv. Không coi fake RPC assertions là bằng chứng deployed RPC read-only.
- Thử inspect process qua `Get-CimInstance` bị môi trường từ chối truy cập CIM; đã dừng test
  qua execution session thay thế. Đây là lỗi công cụ local, không liên quan Supabase/RLS.
- Không phát hiện production bug bằng bằng chứng live; không sửa lỗi/thuật toán/config để ép pass.

## 8. Phân loại bằng chứng

| Nhãn | Áp dụng phiên này |
|---|---|
| UNIT_VERIFIED | Có: 200 focused tests pass với fake dependencies |
| SQL_VERIFIED | Chưa đạt cho database triển khai; chỉ đọc tĩnh migrations local, không chạy SQL |
| LIVE_INTEGRATION_VERIFIED | Chưa đạt ở BM25, Dense hoặc Hybrid |
| RUNTIME_UNVERIFIED | Có: target, network/auth/RLS, deployed schema/RPC, corpus, live search và hydration |
| QUALITY_NOT_EVALUATED | Có: chưa semantic relevance benchmark, labels hoặc so sánh chất lượng |

## 9. Điều kiện mở chặn và bước tiếp theo

1. Cung cấp xác nhận project/database đích bằng thông tin không bí mật và bổ sung Task 2 + B1–B8
   vào workspace. Không paste credentials vào chat hoặc báo cáo.
2. Provision `SUPABASE_URL` và credential phù hợp qua môi trường process/secret manager an toàn
   trước khi khởi chạy verifier. Không yêu cầu agent mở `.env`. Với source grants hiện tại,
   anon key không có EXECUTE retrieval RPC; cần role thực có quyền đã được kiểm tra.
3. Cho audit catalog/count/hash/coverage, provision đường PostgreSQL read-only qua `DATABASE_URL`
   hoặc cung cấp session/tool SQL read-only tương đương. Dùng transaction READ ONLY để ngăn ghi
   trong audit SQL. Không mở rộng grants/schema trong task verification này.
4. Trước HTTP RPC search, đối chiếu deployed function definitions/signatures, permissions và
   read-only behavior, kể cả dependencies; local STABLE definitions không bảo đảm server giống source.
   Dùng read-call allowlist/request trace, không log auth headers. Service-role key có quyền ghi
   không tự trở thành credential read-only; chỉ gọi RPC đã xác minh không ghi.
5. Lấy corpus counts, source provenance, statuses, coverage/statistics/hashes, date/policy thực;
   chạy BM25 từ postings thật. Nếu bị chặn ở tầng nào, giữ nguyên dữ liệu và báo nguyên nhân.
6. Đối chiếu stored embedding provenance với revision local ở mục 5 trước Dense live encode/search.
   Nếu không có provenance đủ mạnh, Dense vẫn BLOCKED; không tự tải model hoặc re-index.
7. Chỉ sau hai nhánh đơn live PASS mới kiểm Hybrid/RRF và failure behavior bằng phương án
   không thay đổi dữ liệu/status (ví dụ fault injection tại client verifier được ghi rõ là simulated).

**Change control:** Chỉ thêm báo cáo này. Không sửa production code, tests, SQL/migrations,
index status, cấu hình hoặc known_issues. Không chạy crawler/ingestion/indexing, migration,
application server, Agent, DB/Storage write hoặc tải model. Không đọc/in secrets.
Các bước live còn lại chờ cấu hình/quyền và bằng chứng compatibility; chưa được tuyên bố hoàn tất.


## Addendum — actual RetrievalService and CLI E2E (2026-11-14)

This section supersedes the earlier runtime-unverified status for the executed technical scenarios. It reuses the baseline audit; the 27 SELECT statements were not repeated.

### Independent status

| Status | Result | Evidence |
|---|---|---|
| BM25_SQL_VERIFIED | PASS | Prior coverage audit; current direct SQL chunk IDs/order/scores equal live service |
| BM25_E2E_VERIFIED | PASS | Actual text → request → tokenizer → adapters → RPC → hydration; CLI also passes |
| DENSE_SQL_VERIFIED | PASS (numeric/hash scope) | Prior complete 2,609-vector audit, current READY metadata |
| DENSE_TECHNICAL_E2E_VERIFIED | PASS | Actual local encoder and real pgvector RPC; CLI also passes |
| DENSE_MODEL_COMPATIBILITY_VERIFIED | BLOCKED | Corpus checkpoint revision/weights provenance not recovered |
| HYBRID_E2E_VERIFIED | PASS (technical) | Both real branches, independent RRF/dedup/order and strict failure verified |
| RETRIEVAL_QUALITY_EVALUATED | BLOCKED | No labeled relevance evaluation |

Overall unrestricted Retrieval verification remains **BLOCKED** on model compatibility and quality; all three technical E2E paths passed their executed scenarios.

### Execution environment, safety and configuration

Configuration was loaded through existing `load_settings()`; identifiers in API URL and PostgreSQL connection agree. Both target indexes were rechecked READY with the same updated_at values as the baseline. No dataset-wide recount was performed.

The production CLI still calls `load_settings(environ=os.environ)`. The verification launcher first calls normal `load_settings()`, which provisions dotenv variables into its process, then runs the unchanged CLI through `runpy` in a fresh subprocess. No service_factory/fake service was supplied. API key/connection string values never appear in commands or evidence.

SQL seed/comparison reads used a separate PostgreSQL REPEATABLE READ READ ONLY transaction with default_transaction_read_only=on and rollback. HTTP adapter calls used the real SDK RPC implementation with verification-only `get=True` instrumentation. PostgreSQL/PostgREST GET RPC mode is read-only; a transport guard rejects every non-GET request and every RPC outside the six-name retrieval allowlist. Array parameters were serialized as equivalent PostgreSQL array literals for GET.

This is E2E of the unchanged service, tokenizer/encoder, repository mappings and actual RPCs under read-only transport instrumentation. The default POST transport of the unwrapped CLI was not executed or verified. No production source, credentials, data, schema or statuses changed. No app/worker/migration/ingestion/indexer was started.

Local inference used the provisioned snapshot `614241f622f53c4eeff9890bdc4f31cfecc418b3`, CPU/local_files_only, offline environment flags. The model was warmed before service tests; standalone CLI runs loaded their model independently. No download occurred.

### Inputs and evidence

- Seed chunk: `0029f385-4290-4359-bf32-87aea3da43cc` (eligible stored chunk with existing postings).
- Exact text query derived from its stored content using the actual tokenizer: `văn bản hợp nhất 60 2026 vbhn nđ`.
- Date: `2026-11-14`; policy: `EXPERIMENTAL_ONLY`; top-k=5.
- Hybrid budgets: BM25=5, Dense=5, RRF k=60.
- Finite query vector: 384 dimensions, norm 1.0000000200572066; actual query encoder source applies `query: ` prefix.
- Evidence artifact: [retrieval-e2e-evidence.json](retrieval-e2e-evidence.json); includes per-test request context, relevant response fields, UUIDs/ranks/scores, errors/warnings and observed RPC call sequences. Full legal text and arbitrary source metadata were not persisted.

| Test | Result | Evidence count / observation |
|---|---|---|
| bm25_hits | OK | 5 evidence |
| bm25_filter_no_match | NO_MATCH | 0 evidence |
| dense_hits | OK | 5 evidence |
| dense_filter_no_match | NO_MATCH | 0 evidence |
| hybrid_hits | OK | 5 evidence |
| hybrid_filter_no_match | NO_MATCH | 0 evidence |
| cli_bm25 | OK | 5 evidence; exit 0 |
| cli_dense | OK | 5 evidence; exit 0 |
| cli_hybrid | OK | 5 evidence; exit 0 |
| bm25_invalid_request | REJECTED | validation boundary |
| bm25_controlled_missing_index | FAILED | zero partial evidence |
| cli_bm25_invalid | FAILED | validation boundary; exit 2 |
| dense_invalid_request | REJECTED | validation boundary |
| dense_controlled_missing_index | FAILED | zero partial evidence |
| cli_dense_invalid | FAILED | validation boundary; exit 2 |
| hybrid_invalid_request | REJECTED | validation boundary |
| hybrid_controlled_missing_index | FAILED | zero partial evidence |
| cli_hybrid_invalid | FAILED | validation boundary; exit 2 |

### Observed rankings


bm25:

| Rank | Chunk UUID | Score | Kind |
|---|---|---|---|
| 1 | 4bf655a2-a1f7-427e-aea9-ddb952b18b85 | 13.9595546836106 | BM25 |
| 2 | 09982b9b-cfc7-4b57-a656-9ca8daa369fc | 13.7857169260629 | BM25 |
| 3 | 69019f42-d59c-45ce-9313-9c4c9153b1b2 | 13.4507145414879 | BM25 |
| 4 | 4e25db41-5d45-49b3-bce5-978dfa7a7385 | 12.9776652791903 | BM25 |
| 5 | 46ccc6eb-69e4-4926-90ba-3fafc3b4440e | 12.6803608581204 | BM25 |

dense:

| Rank | Chunk UUID | Score | Kind |
|---|---|---|---|
| 1 | e72ce95a-258b-4f3b-9cba-18c9117a1d3c | 0.899065381344238 | COSINE_SIMILARITY |
| 2 | 2244d304-77d2-4796-b843-548bea0a3c0e | 0.898479169697813 | COSINE_SIMILARITY |
| 3 | 67c18b69-c5c5-4ab9-abac-0294b5b7ba0f | 0.897835916409737 | COSINE_SIMILARITY |
| 4 | 09982b9b-cfc7-4b57-a656-9ca8daa369fc | 0.896894467247198 | COSINE_SIMILARITY |
| 5 | 4bf655a2-a1f7-427e-aea9-ddb952b18b85 | 0.891103393369712 | COSINE_SIMILARITY |

hybrid:

| Rank | Chunk UUID | Score | Kind |
|---|---|---|---|
| 1 | 4bf655a2-a1f7-427e-aea9-ddb952b18b85 | 0.03177805800756621 | RRF |
| 2 | 09982b9b-cfc7-4b57-a656-9ca8daa369fc | 0.031754032258064516 | RRF |
| 3 | e72ce95a-258b-4f3b-9cba-18c9117a1d3c | 0.01639344262295082 | RRF |
| 4 | 2244d304-77d2-4796-b843-548bea0a3c0e | 0.016129032258064516 | RRF |
| 5 | 67c18b69-c5c5-4ab9-abac-0294b5b7ba0f | 0.015873015873015872 | RRF |

### Verification details and scenario limits

BM25 SQL comparison was exact for UUID/order/scores. For all successful service responses, targeted SQL reads confirmed content equality, SHA-256, source/structure IDs and chunk metadata equality. All captured service/CLI hit responses pass consecutive-rank, unique-UUID, nonincreasing-score and date/policy checks. Service performs its real source hydration and integrity gates. CLI UUIDs and scores equal their corresponding service results.

Independent Hybrid recomputation used the full five-candidate lists from the separately executed BM25 and Dense branches, not only final contributions: sum(1/(60+rank)), sort descending then UUID ascending, truncate five. Final UUIDs and scores match within 1e-12. CLI repeats the same output, providing a second ordering observation.

NO_MATCH was produced by an explicitly nonexistent policy allowlist, not a nonsense Dense query. Invalid top-k=0 requests were rejected before service/database operations; the real CLI returned INVALID_ARGUMENTS/exit 2 in each mode.

Unavailable-index tests changed only the private index-name field on a newly created verification service instance to `audit-deliberately-unavailable-index`. The database returned no index row through real GET RPC. BM25/Dense/Hybrid all failed with zero evidence. For Hybrid the BM25 branch actually succeeded before Dense index lookup failed: strict no-partial-result behavior was observed without changing production infrastructure. These are controlled configuration faults, not claims that the production indexes were unavailable.

Database transport/RPC failure taxonomy uses the existing unit/fake evidence (200 tests from the earlier verification); no network outage was manufactured. This remains UNIT_VERIFIED, not a new live outage test. No semantic relevance, citation legal correctness or recall benchmark was performed.

### Checkpoint provenance investigation

Reused index/vector metadata from baseline: revision/model_revision/checkpoint_revision absent. Searched repository Markdown/JSON/Python artifacts for revision/checkpoint evidence and filenames for manifests/logs; no corpus embedding-run manifest or log establishing weights identity was found. Existing Task 5 documents the local snapshot only. The writer source loads model name without pinning revision, so matching names/dimensions and successful inference do not establish historical corpus revision. No model download or vector modification was attempted. Missing provenance is uncertainty, not proof of incompatibility.

### Reproduction and minimum next actions

Run from main with the existing venv and authorized network execution:

```powershell
.venv/Scripts/python.exe .docs/development/retrieval-e2e-verifier.py
.venv/Scripts/python.exe .docs/development/retrieval-e2e-scenarios.py
```

The first launcher records exact sanitized child CLI argv per mode in the evidence file. The second records invalid-request and controlled missing-index cases. Both are documentation-side verification tools, not product changes.

1. Preserve and reuse the existing 2,609 chunks/postings/vectors; no evidence in these runs justifies blanket reparse/re-index.
2. Recover corpus embedding-run revision/weights/tokenizer/pooling provenance and compare with local checkpoint. If unrecoverable, retain compatibility BLOCKED and design a separate bounded compatibility study; do not automatically re-encode.
3. If semantic quality is required, prepare labeled queries/expected sources and evaluate BM25/Dense/Hybrid separately. Technical hits do not establish quality improvement.
4. Separately inspect stored source assets for the 21 unchunked documents; these E2E tests concern the indexed cohort only.
