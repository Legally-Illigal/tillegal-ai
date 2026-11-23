# Từ QueryPlan /Subquery + SearchOptions sang RetrievalRequest

Câu lệnh chính [Search44](../../../src/applications/tillegal/agents/search/agent.py):

```python
requests = tuple(RetrievalRequest(query=subquery.text, **options.model_dump()) for subquery in parsed.subqueries)
```

`options.model_dump()` mặc định Python mode: mode là StrEnum instance, date là date, policies là tuple. RetrievalRequest constructor validate theo [contracts23–44](../../../src/applications/tillegal/retrieval/contracts.py), kế thừa ContractModel(extra=forbid, frozen= True, allow_inf_nan= False). Không serialize JSON tại đây.

| QueryPlan /Subquery hoặc options | Request field | Transformation/validation | Actual consumer |
|---|---|---|---|
|subquery.text |query: StrictStr, length 1..10000 |Giữ nguyên text; nonblank validator dùng strip chỉ để kiểm, return value gốc |Service query.strip trong preprocessing/encoding và query_used |
|options.mode |mode:RetrievalMode | Pydantic enum validation; không infer |Service dispatch 192–220 |
|options. top_k | top_k: StrictInt, 1..50 |Copy cùng k mỗi subquery |Service final output cap/branch request |
|options. as_of_date | as_of_date:date |Copy trusted date; options có thể parse ISO trước đó |Repository filters và eligibility |
|options. allowed_usage_policies |tuple[StrictStr,...], min 1 |Strip+dedup guard đã ở options, request validator áp cùng rule |Repository governance/eligibility |
|plan.original |Không forward |Chỉ ở raw plan/handoff |Provenance question ở packet |
|plan.intent |Không forward |Không đổi algorithm | Search chỉ schema-validate |
|plan.domain |Không forward |Không thành legal-domain filter |Global descriptive label upstream |
|plan. temporal_scope |Không forward |Không resolve mentions, không thay trusted date |Giữ ở plan/handoff |
|subquery.purpose |Không forward |Không quyết định mode/ top_k |Giữ ở plan |
|plan.clarification |Không forward |Truthy →return trước requests |Guard Search /graph |
|Graph request_id / run_id |Không có Request field |Không tự copy IDs |Graph packet/context riêng |

## Điểm dễ nhầm về normalization

- Search không strip query. Request.nonblank_query 34–37 không trả stripped text mà trả value. OBSERVED spaces_retained giữ query=" thuế ", trong response.query cũng giữ raw request, query_used ="thuế" do service/fake thực thi.
- Policy normalization có xảy ra: nonblank_policies ở options và policies ở request cùng strip/dedup stable-order. Không lowercase hoặc map policy aliases. Case-sensitive policy labels có thể còn khác nhau.
- `mode="rerank"` invalid: hybrid + RerankConfig(enabled= True) là stage opt-in; request không chứa enabled/model_path.
- Date parsing là schema behavior cho trusted options/request, không phải Query temporal extraction. `as_of_date="2024-02-31"` bị schema reject; input user mention 31/02/2024 lại tạo clarification upstream.
- Request. top_k có default 10 nhưng Search luôn cung cấp explicit options. top_k; không có implicit fallback trong flow đang kiểm.

## Validation toàn tuple trước I/O

tuple comprehension là eager; mọi constructor phải hoàn tất trước vòng for service. Tab-only subquery thứ hai fail khiến 0 calls, mặc dù request object thứ nhất đã tạo local trong comprehension. Không nói “requests tuple đã tạo đủ 3” trong case đó: assignment 44 chưa hoàn tất nên không có requests tuple cuối. Snapshots ở 11 ghi rõ observable vs source-derived.

Request không có request_id; service tạo UUID riêng ở [service221](../../../src/application/services/retrieval_service.py) hoặc Hybrid /rerank helper. Graph ExecutionContext IDs phục vụ run-level correlation, không phải response UUID. Không có transport-level idempotency key hoặc cross-query dedup được implement trong Search.

Kiểm chứng receiving/mapping: test_unit_request_mapping_and_no_match_identity 56–76, test_unit_invalid_options 100–102, test_invalid_plan_no_calls 108–112 trong [multimode tests](../../../tests/unit/applications/tillegal/test_query_search_multimode.py); số dòng đầy đủ cập nhật ở 18. Diagnostics normalized_options/tab_second/spaces_retained ở 11.
