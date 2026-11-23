# SearchState, native responses và UnifiedEvidence

## SearchState: dictionary runtime, không phải Pydantic model

[SearchState31–35](../../../src/applications/tillegal/agents/search/agent.py) là TypedDict, không validate khi construct dict:

| Field | Exact type | Source/semantics | Transformation/consumer |
|---|---|---|---|
|plan |dict |Chính object plan argument |Không mutate/copy; graph packet validate thành QueryPlan |
|requests |tuple[RetrievalRequest,...] |Các request đã có responses khi FAILED, hoặc toàn bộ khi COMPLETED |Clarification empty; không serialize |
|responses |tuple[RetrievalResponse,...] |Native response objects, subclasses vẫn được giữ |Append→tuple; không dump/rehydrate trong Search |
|status |Literal CLARIFICATION_REQUIRED / COMPLETED / FAILED |Control-flow Search |Graph/handoff map status riêng |

 COMPLETED cho phép mọi responses NO_MATCH. FAILED có thể giữ successful responses trước đó. Không có Search -level flattened evidence, warnings, error metadata fields riêng. Đọc chúng trong mỗi native response. Không tạo EvidenceBundle của legacy code.

## RetrievalResponse: mọi fields trong source

Nguồn [contracts113–149](../../../src/applications/tillegal/retrieval/contracts.py). Default expressions giữ đúng AST dưới đây; Field(...) có constraints là required nếu không có default.

| Field | Annotation nguyên schema | Default/expression | Source line |
|---|---|---|---|
| schema_version | `Literal['1']` | `'1'` | 114 |
| request_id | `UUID` | `required; no default` | 115 |
| query | `str` | `required; no default` | 116 |
| query_used | `str` | `required; no default` | 117 |
| mode | `RetrievalMode` | `required; no default` | 118 |
| top_k | `StrictInt` | `Field(ge=1, le=50)` | 119 |
| as_of_date | `date` | `required; no default` | 120 |
| allowed_usage_policies | `tuple[str, ...]` | `required; no default` | 121 |
| selected_index_name | `str` | `required; no default` | 122 |
| index | `IndexIdentity \| None` | `required; no default` | 123 |
| status | `Literal['OK', 'NO_MATCH', 'FAILED']` | `required; no default` | 124 |
| evidence | `tuple[UnifiedEvidence, ...]` | `()` | 125 |
| warnings | `tuple[RetrievalWarning, ...]` | `()` | 126 |
| error | `RetrievalErrorDetail \| None` | `None` | 127 |
| retrieved_at | `datetime` | `required; no default` | 128 |
| consistency | `Literal['BEST_EFFORT']` | `'BEST_EFFORT'` | 129 |

Nguồn/ý nghĩa theo nhóm:

- schema_version 1 là version contract; request_id do service/helper cấp; retrieved_at aware timestamp; consistency BEST_EFFORT, không corpus snapshot.
- query giữ request query; query_used là text thực dùng (single backend strip); mode/ top_k /date/policies echo request context. Search không tự normalize chúng.
- selected_index_name là tên service chọn; index là observation metadata hoặc None. Hybrid có index= None ở top-level và per-branch indexes trong fusion.
- status OK đòi evidence nonempty/no error; NO_MATCH đòi empty/no error; FAILED đòi empty/error. Validator còn kiểm evidence<= top_k, unique IDs trong response, rank liên tục 1..N và method khớp mode, timezone.
- evidence/warnings/error giữ objects gốc qua Search. ErrorDetail có category/code/stage/message/retryable; không mọi exception đều được biến thành object này.

IndexIdentity fields là id, index_name, index_version, status, updated_at, algorithm optional, tokenizer optional (contracts 47–56). RetrievalWarning là code, message, retrieval_chunk_id optional default None (59–62). Các nullable fields khác trong schema không mặc định optional nếu không có default.

## UnifiedEvidence: full field inventory

Nguồn [contracts65–110](../../../src/applications/tillegal/retrieval/contracts.py). Tất cả values do service/adapters dựng trước khi Search nhận. Search không có per-field map nên provenance không bị bỏ vì một mapping chưa đủ fields.

| Field | Annotation nguyên schema | Default/expression | Source line |
|---|---|---|---|
| retrieval_chunk_id | `UUID` | `required; no default` | 68 |
| source_document_id | `UUID` | `required; no default` | 69 |
| document_structure_id | `UUID` | `required; no default` | 70 |
| chunk_key | `str` | `Field(min_length=1)` | 71 |
| content | `str` | `Field(min_length=1)` | 72 |
| content_sha 256 | `str` | `Field(pattern='^[0-9a-f]{64}$')` | 73 |
| hash_check | `Literal['MATCHED_STORED', 'PAYLOAD_ONLY']` | `required; no default` | 74 |
| content_representation | `Literal['retrieval_chunk_content']` | `'retrieval_chunk_content'` | 75 |
| rank | `StrictInt` | `Field(ge=1)` | 76 |
| raw_score | `float` | `required; no default` | 77 |
| score_kind | `Literal['BM25', 'COSINE_SIMILARITY', 'RRF']` | `required; no default` | 78 |
| retrieval_method | `RetrievalMode` | `required; no default` | 79 |
| node_id | `str \| None` | `required; no default` | 80 |
| block_id | `str \| None` | `required; no default` | 81 |
| chunk_type | `str` | `Field(min_length=1)` | 82 |
| start_offset | `int \| None` | `Field(ge=0)` | 83 |
| end_offset | `int \| None` | `Field(ge=0)` | 84 |
| chunk_metadata | `dict[str, object]` | `required; no default` | 85 |
| source_id | `str \| None` | `required; no default` | 86 |
| source_record_id | `str \| None` | `required; no default` | 87 |
| source_snapshot_id | `str \| None` | `required; no default` | 88 |
| title | `str` | `Field(min_length=1)` | 89 |
| source_url | `str \| None` | `required; no default` | 90 |
| language | `str \| None` | `required; no default` | 91 |
| issued_on | `date \| None` | `required; no default` | 92 |
| effective_from | `date \| None` | `required; no default` | 93 |
| effective_to | `date \| None` | `required; no default` | 94 |
| effect_status_reported | `str \| None` | `required; no default` | 95 |
| usage_policy | `str` | `Field(min_length=1)` | 96 |
| source_metadata | `dict[str, object]` | `required; no default` | 97 |

| Nhóm | Ý nghĩa, nguồn và consumer |
|---|---|
|Identity | retrieval_chunk_id, source_document_id, document_structure_id, chunk_key để truy ngược stored chunk/source/structure |
|Payload/integrity |content là stored retrieval chunk text có thể có breadcrumb; content_sha 256 và hash_check mô tả integrity, không xác minh literal raw quote |
|Ranking |rank, raw_score, score_kind, retrieval_method giữ nghĩa backend; consumer dùng evidence order/rank |
|Chunk provenance |node_id, block_id, chunk_type, offsets, chunk_metadata là vị trí/metadata đã hydrate |
|Source provenance |source_id, source_record_id, source_snapshot_id, title, source_url, language, source_metadata là thông tin nguồn; nullable không được tự điền |
|Temporal |issued_on, effective_from, effective_to, effect_status_reported là metadata nguồn, không kết luận applicability cho case |
|Policy |usage_policy là nhãn governance được giữ; Search không nâng quyền |

 UnifiedEvidence.validate_semantics 100–110 kiểm score_kind ↔method, BM25 /COSINE_SIMILARITY/ RRF, nonblank content/title/policy, offset range. Hash pattern kiểm định dạng 64 hex, không tự tính lại nội dung trong schema; actual integrity check thuộc service. Không gán validator này là legal correctness check.

## Subtypes và serialization

 HybridRetrievalResponse thêm fusion với config/branches/ranking. RerankedHybridRetrievalResponse thêm reranking metadata; raw_score vẫn RRF sau rerank. SearchState.responses annotation là base nhưng Python tuple giữ subtype object: không có serialization trong function có thể làm rơi fields. JudgeHandoff dùng explicit union cụ thể để JSON round-trip không mất fusion/reranking; chi tiết 09.

 SearchState không có. model_dump_json (); cần serializer bên ngoài. Không hứa mọi generic serializer khai báo base type sẽ giữ subtype fields giống packet union. JSON diagnostic dùng runtime model. model_dump (mode="json") để hiện full subtype. Không phải HTTP endpoint serialization đã implement.

## Ranking/provenance preservation và giới hạn

 Search chỉ append response object ở 48, tuple ở 53/56. Test identity ở [test_query_search88–95](../../../tests/unit/applications/tillegal/test_query_search.py), all-mode identity/parity ở [multimode139–182](../../../tests/unit/applications/tillegal/test_query_search_multimode.py), graph JSON assertions ở [graph130–152](../../../tests/graph/test_query_search_workflow.py) kiểm hỗ trợ kết luận này.

Không reorder/merge/dedup/recalculate scores/rewrite content/remove warnings/upgrade hash_check trong Search. Đây là preservation so với dependency output, không chứng minh metadata upstream đúng, hash là raw legal source, hay evidence đủ cho Judge. Frozen Pydantic model không làm nested chunk_metadata / source_metadata dict deep immutable. SearchState.plan là alias mutable; consumer không được coi mọi output là snapshot bất biến.

Reranked evidence order có thể khác descending RRF raw_score do Cross-Encoder stage trước Search nhận response. Đừng sort raw_score lần nữa; điều đó phá ranking có chủ ý của service. Fusion explanations và CandidateScore giúp giải thích scores trước/sau mà không trộn hai scale.
