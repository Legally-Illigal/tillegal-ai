# JudgeHandoff v1: technical readiness, chưa có Judge evaluation

[legal_qa_state.py15–93](../../../src/applications/tillegal/state/legal_qa_state.py) định nghĩa `RetrievalOutcome = RerankedHybridRetrievalResponse | HybridRetrievalResponse | RetrievalResponse` và `JudgeHandoff(BaseModel)`. Model frozen/extra forbid; graph Search node tạo packet, sau đó END. Tên JudgeHandoff không chứng minh Judge Agent đã chạy.

## Full field contract

| Field | Annotation nguyên schema | Default/expression | Source line |
|---|---|---|---|
| schema_version | `Literal['1']` | `'1'` | 23 |
| request_id | `str \| None` | `required; no default` | 24 |
| run_id | `str` | `Field(min_length=1)` | 25 |
| question | `str` | `Field(min_length=1, max_length=10000)` | 26 |
| plan | `QueryPlan` | `required; no default` | 27 |
| options | `SearchOptions` | `required; no default` | 28 |
| requests | `tuple[RetrievalRequest, ...]` | `Field(min_length=1)` | 29 |
| responses | `tuple[RetrievalOutcome, ...]` | `Field(min_length=1)` | 30 |
| search_status | `Literal['COMPLETED', 'FAILED']` | `required; no default` | 31 |
| status | `Literal['READY', 'NO_MATCH', 'RETRIEVAL_FAILED']` | `required; no default` | 32 |

Nguồn của values: question và IDs từ graph state; plan/requests/responses/search_status từ SearchState; options từ injected pipeline; status do from_search quyết định. schema_version mặc định string 1, request_id nullable nhưng required; run_id min_length 1 và question 1..10000. requests/responses min 1 nên clarification không thể có packet rỗng hợp lệ.

## from_search quyết định status ở đâu?

Dòng 76–82: nếu result.status== FAILED thì RETRIEVAL_FAILED; else nếu bất kỳ response.evidence nonempty thì READY; else NO_MATCH. Dòng 83–93 gọi constructor để schema và context validators chạy.

 READY chỉ nói Search nonfailed và có ít nhất một evidence occurrence. Không xét relevance threshold, coverage các vấn đề pháp lý, nguồn còn hiệu lực chắc chắn, content raw quote hoặc citation validity. Nếu một subquery OK và phần khác NO_MATCH, packet vẫn có thể READY. Nếu trước có OK rồi sau FAILED, RETRIEVAL_FAILED thắng. Không tự rerun/refine để tìm thêm evidence.

## Context validator đầy đủ theo thứ tự

Source validate_context 44–64:

1. question phải bằng plan.original và plan.clarification falsy.
2. len(requests)==len(responses) và không nhiều hơn plan.subqueries.
3. Zip theo order: request.query==subquery.text.
4. Mọi SearchOptions field trên request bằng options value.
5. Mọi RetrievalRequest field echo trên response bằng request value.
6. Chỉ response cuối được FAILED; không được tiếp tục sau failure.
7. status/search_status phải đúng derived outcome.
8. Nếu không failed, phải xử lý đủ mọi subqueries.

Không có check response. request_id uniqueness bằng graph ID, không deep semantic check query_used /content relevance. Packet validator thêm consistency boundary mạnh hơn Search function; không thay chứng minh evidence đã đúng luật.

## Warnings/errors: properties chứ không top-level serialized fields

warnings 35–37 flatten response.warnings theo response order, giữ duplicates. errors 40–41 lấy non- None response.error. Hai @property không @computed_field, nên không xuất thành top-level keys của model_dump_json; data vẫn nằm trong từng response và properties được derive khi access. Graph chỉ đưa error.code list vào errors channel; không làm mất typed details vì packet vẫn giữ responses.

## Subtype preservation và JSON round-trip

Explicit union đặt most-specific subtype trước: reranked→hybrid→base. Mỗi subtype yêu cầu extension fields tương ứng. model_dump_json serialize actual response fields qua union; model_validate_json dựng lại subtype. Đây là mechanism đã test cho 4 profiles, không dựa giả định mọi base-type serializer tự giữ extension.

 OBSERVED graph_bm25/dense/hybrid/rerank:round-trip equal, true; type preserved, fusion/reranking hiện khi cần. Native response identity giữa SearchState và handoff giữ trong cùng process theo tests; JSON round-trip tạo object mới bằng value, không hứa `is` sau JSON. UUID, date, tuple được biểu diễn string/array rồi reconstruct typed objects.

Tests [graph130–152](../../../tests/graph/test_query_search_workflow.py) kiểm equality, type, evidence, fusion/reranking;[314–349](../../../tests/graph/test_query_search_workflow.py) kiểm tampering/extra/context;[155–165](../../../tests/graph/test_query_search_workflow.py) kiểm failure history. Diagnostics context_mismatch/graph_context_mismatch phân biệt Search accepts vs packet rejects.

## Failure boundary

Handoff constructor/serializer có thể raise ValidationError hoặc serialization error với payload không JSON -serializable. Node không catch để tạo READY giả. Metadata dict[str, object] không chứng minh mọi arbitrary object đều JSON serializable; sample round-trip pass không cover mọi metadata object. Probe đã chạy với synthetic object() trong metadata trả PydanticSerializationError, ghi ở [supplemental-probes.json](evidence/supplemental-probes.json); không tự coi kiểu dữ liệu thô là universal safety guarantee.
