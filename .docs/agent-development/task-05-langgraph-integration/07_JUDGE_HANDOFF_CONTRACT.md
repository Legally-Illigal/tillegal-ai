# JudgeHandoff schema v1

Boundary này version hóa technical retrieval output. READY nghĩa là tất cả planned queries đã xử lý không FAILED và có ít nhất một evidence. Chưa có assessment về sufficiency, điều kiện/ngoại lệ, hiệu lực hoặc applicability. Judge tương lai chịu trách nhiệm đánh giá đó.

## Canonical fields và provenance

- question giữ original input, plan typed QueryPlan có cùng original.
- request_id correlation optional, run_id ExecutionContext; mỗi native response giữ request UUID riêng.
- options trusted SearchOptions; requests/responses tuples theo thứ tự subquery thực thi.
- responses[i].evidence chứa UnifiedEvidence, không flatten/dedup qua query hoặc map sang legacy EvidenceBundle.
- responses[i].warnings/error chứa typed warning IDs và category/code/stage/retryable. packet.warnings/errors là convenience properties; JSON không có keys property top-level riêng.
- Fusion/reranking và config/index/date/policy/consistency được giữ qua union subtype.
- status READY/NO_MATCH/RETRIEVAL_FAILED, search_status COMPLETED/FAILED; không có confidence hoặc legal correctness labels.

Context validator kiểm original/plan, không clarification, số requests/responses bằng nhau và không vượt số subquery, request.query khớp text, options khớp request, response context khớp request. Completed packet phải bao đủ subqueries. Nếu có FAILED, chỉ response cuối được FAILED để bảo đảm stop-first-failure. Đây là consistency validation, không đọc DB hoặc kiểm claim support.

## Handoff và serialization

```python
packet = state["handoff"]
payload = packet.model_dump_json()
restored = JudgeHandoff.model_validate_json(payload)
```

Caller kiểm graph/packet status trước khi consume. Serialize chính JudgeHandoff với RetrievalOutcome union gồm reranked/hybrid/base; không projection qua base-only response schema. Tests whole-packet round-trip equality và exact subtype giữ UUID/date/nulls/metadata/fusion/reranking. Graph in-memory giữ native objects, không cần JSON mỗi edge. Durable checkpoint/resume serializer chưa attach/test end-to-end.

## Evidence mới

Live BM25 graph tạo READY/OK/5 evidence; warnings temporal incomplete giữ nguyên. [Summary live](evidence/live-bm25.json) không lưu raw source metadata. [Full offline packet](evidence/offline-handoff-example.json) là output graph dùng FakeRetrieval, statusNO_MATCH và FIXTURE_WARNING; đó là fixture kỹ thuật, không phải Supabase result.

## Gaps cho Judge task

UnifiedEvidence.content là retrieval_chunk_content có thể chứa breadcrumbs; hash_check MATCHED_STORED/PAYLOAD_ONLY không chứng minh raw-source hoặc legal verification. Document/source/structure UUID khác legacy document_version_id. Source URL/snapshot/offset có thể None; không tự điền. Index consistency BEST_EFFORT không immutable snapshot. Temporal mentions trong plan chưa được resolve với as_of_date runtime. Rerank fallback có thể vẫn technical READY kèm warning; consumer cần đọc giới hạn.

RETRIEVAL_FAILED có thể giữ prior successful responses cho diagnostic, không dùng như normal READY. Clarification/execution failure/cancel không tạo packet mới cho Judge. Frozen model không deep-freeze nested metadata: caller không mutate evidence sau bàn giao.
