# Contracts hiện tại

Các bảng dưới trích trực tiếp Python AST sau verification, không tạo model mới. Field không default vẫn required kể cả type có None; Field(...) chỉ có constraints nhưng không default cũng required. UUID/date/datetime là Python types trong native model; JSON boundary dùng model_dump(mode="json") đúng subclass.

## QueryPlan và Search

Input `understand(question: str)` có raw length 1–10000, NFC nội bộ, rejects type/control/blank bằng QueryInputError(ValueError), original giữ đối số. Các literals/expansion không đổi trong Task 4. Consumer production là QuerySearch.search.

### Subquery

| Field | Python annotation | Default / constraint expression |
|---|---|---|
| text | `str` | `Field(min_length=1, max_length=10000)` |
| purpose | `Literal['lookup', 'question_part', 'topic']` | `Required (không default)` |

### QueryPlan

| Field | Python annotation | Default / constraint expression |
|---|---|---|
| original | `str` | `Field(min_length=1, max_length=10000)` |
| intent | `Literal['quote_lookup', 'legal_question']` | `Required (không default)` |
| domain | `Literal['labour', 'unknown']` | `Required (không default)` |
| temporal_scope | `list[str]` | `Required (không default)` |
| subqueries | `list[Subquery]` | `Field(min_length=1, max_length=4)` |
| clarification | `str \| None` | `Required (không default)` |

| Field plan | Search có dùng trực tiếp? | Biến đổi / consumer |
|---|---|---|
| original | Không để tạo request | Giữ trong state.plan; user text không cấp policy |
| intent | Chỉ schema validate | Không tự đổi retrieval mode |
| domain | Chỉ schema validate | unknown không suy thành unsupported law |
| temporal_scope | Chỉ giữ trong plan | Date runtime không bị ghi đè; reconciliation tương lai |
| subqueries | Có | Mỗi text → RetrievalRequest.query; purpose giữ trong plan |
| clarification | Có | Truthy → zero calls, CLARIFICATION_REQUIRED |

### SearchOptions

| Field | Python annotation | Default / constraint expression |
|---|---|---|
| mode | `RetrievalMode` | `Required (không default)` |
| top_k | `StrictInt` | `Field(ge=1, le=50)` |
| as_of_date | `date` | `Required (không default)` |
| allowed_usage_policies | `tuple[StrictStr, ...]` | `Field(min_length=1)` |

### SearchState

| Field | Python annotation | Default / constraint expression |
|---|---|---|
| plan | `dict` | `Required (không default)` |
| requests | `tuple[RetrievalRequest, ...]` | `Required (không default)` |
| responses | `tuple[RetrievalResponse, ...]` | `Required (không default)` |
| status | `Literal['CLARIFICATION_REQUIRED', 'COMPLETED', 'FAILED']` | `Required (không default)` |

SearchOptions required bốn trường, extra forbid, frozen; policy strip/dedup, không rỗng. SearchState là TypedDict, không có runtime validators riêng. requests/responses đều tuples; plan raw dict giữ nguyên. Response subtype có fusion/reranking được giữ bằng object identity, không model_dump lại qua base model.

## Retrieval và evidence

### RetrievalRequest

| Field | Python annotation | Default / constraint expression |
|---|---|---|
| query | `StrictStr` | `Field(min_length=1, max_length=10000)` |
| mode | `RetrievalMode` | `Required (không default)` |
| top_k | `StrictInt` | `Field(default=10, ge=1, le=50)` |
| as_of_date | `date` | `Required (không default)` |
| allowed_usage_policies | `tuple[StrictStr, ...]` | `Field(min_length=1)` |

### IndexIdentity

| Field | Python annotation | Default / constraint expression |
|---|---|---|
| id | `UUID` | `Required (không default)` |
| index_name | `str` | `Field(min_length=1)` |
| index_version | `str` | `Field(min_length=1)` |
| status | `str` | `Required (không default)` |
| updated_at | `datetime` | `Required (không default)` |
| algorithm | `str \| None` | `None` |
| tokenizer | `str \| None` | `None` |

### RetrievalWarning

| Field | Python annotation | Default / constraint expression |
|---|---|---|
| code | `str` | `Required (không default)` |
| message | `str` | `Required (không default)` |
| retrieval_chunk_id | `UUID \| None` | `None` |

### UnifiedEvidence

| Field | Python annotation | Default / constraint expression |
|---|---|---|
| retrieval_chunk_id | `UUID` | `Required (không default)` |
| source_document_id | `UUID` | `Required (không default)` |
| document_structure_id | `UUID` | `Required (không default)` |
| chunk_key | `str` | `Field(min_length=1)` |
| content | `str` | `Field(min_length=1)` |
| content_sha256 | `str` | `Field(pattern='^[0-9a-f]{64}$')` |
| hash_check | `Literal['MATCHED_STORED', 'PAYLOAD_ONLY']` | `Required (không default)` |
| content_representation | `Literal['retrieval_chunk_content']` | `'retrieval_chunk_content'` |
| rank | `StrictInt` | `Field(ge=1)` |
| raw_score | `float` | `Required (không default)` |
| score_kind | `Literal['BM25', 'COSINE_SIMILARITY', 'RRF']` | `Required (không default)` |
| retrieval_method | `RetrievalMode` | `Required (không default)` |
| node_id | `str \| None` | `Required (không default)` |
| block_id | `str \| None` | `Required (không default)` |
| chunk_type | `str` | `Field(min_length=1)` |
| start_offset | `int \| None` | `Field(ge=0)` |
| end_offset | `int \| None` | `Field(ge=0)` |
| chunk_metadata | `dict[str, object]` | `Required (không default)` |
| source_id | `str \| None` | `Required (không default)` |
| source_record_id | `str \| None` | `Required (không default)` |
| source_snapshot_id | `str \| None` | `Required (không default)` |
| title | `str` | `Field(min_length=1)` |
| source_url | `str \| None` | `Required (không default)` |
| language | `str \| None` | `Required (không default)` |
| issued_on | `date \| None` | `Required (không default)` |
| effective_from | `date \| None` | `Required (không default)` |
| effective_to | `date \| None` | `Required (không default)` |
| effect_status_reported | `str \| None` | `Required (không default)` |
| usage_policy | `str` | `Field(min_length=1)` |
| source_metadata | `dict[str, object]` | `Required (không default)` |

### RetrievalResponse

| Field | Python annotation | Default / constraint expression |
|---|---|---|
| schema_version | `Literal['1']` | `'1'` |
| request_id | `UUID` | `Required (không default)` |
| query | `str` | `Required (không default)` |
| query_used | `str` | `Required (không default)` |
| mode | `RetrievalMode` | `Required (không default)` |
| top_k | `StrictInt` | `Field(ge=1, le=50)` |
| as_of_date | `date` | `Required (không default)` |
| allowed_usage_policies | `tuple[str, ...]` | `Required (không default)` |
| selected_index_name | `str` | `Required (không default)` |
| index | `IndexIdentity \| None` | `Required (không default)` |
| status | `Literal['OK', 'NO_MATCH', 'FAILED']` | `Required (không default)` |
| evidence | `tuple[UnifiedEvidence, ...]` | `()` |
| warnings | `tuple[RetrievalWarning, ...]` | `()` |
| error | `RetrievalErrorDetail \| None` | `None` |
| retrieved_at | `datetime` | `Required (không default)` |
| consistency | `Literal['BEST_EFFORT']` | `'BEST_EFFORT'` |

Request model extra forbid/frozen/finite numbers. Query nonblank, mode bm25/dense/hybrid, top_k 1–50, explicit date và allowlist. Rerank bật bằng RerankConfig trong service; string mode="rerank" bị từ chối.

Response OK phải có evidence/no error; NO_MATCH empty/no error; FAILED empty/has error; rank liên tục, evidence unique và đúng method. Hybrid bổ sung fusion; RerankedHybrid bổ sung reranking. Error detail có category/code/stage/message/retryable, không được biến lỗi backend thành thành công rỗng. UnifiedEvidence.content là stored retrieval chunk có thể có breadcrumbs; hash_check không chứng minh legal verification.

## Ví dụ đã chạy

Live question `Trích dẫn: hợp đồng dân sự` → original nguyên câu, intent quote_lookup, domain unknown, temporal_scope=[], subqueries=[{text: hợp đồng dân sự,purpose: lookup}], clarification=None. Mọi probe dùng top_k=5, as_of_date=2026-11-17, allowed_usage_policies=[EXPERIMENTAL_ONLY] từ artifact explicit sẵn có; chỉ mode/config thay đổi.

Tất cả execution thành công đều trả 5 evidence. BM25 và Dense top-5 lần này không có chunk chung; điều đó phù hợp với thuật toán khác nhau. Không dùng sự khác nhau đó để kết luận chất lượng cải thiện. Ngày 31/02/2024 yêu cầu clarification, kiểm offline zero calls ở mọi mode; không live query ngày sai gây đọc DB thừa.
