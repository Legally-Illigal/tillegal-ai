# Search → RetrievalService: delegated execution boundary

[Search47](../../../src/applications/tillegal/agents/search/agent.py) gọi chính xác `response = await retrieval.search(request)`. Dependency annotation là concrete RetrievalService; tests dùng duck-typed Recorder /AsyncMock. Đây không phải call tới legacy LegalRetrieval/ai_core. Bootstrap import service từ src/application/services/retrieval_service.py và các read adapters trong target.

## Signature và đường dispatch

`RetrievalService.search(self, request: RetrievalRequest) -> RetrievalResponse | HybridRetrievalResponse` là async method [service192–305](../../../src/application/services/retrieval_service.py). RerankedHybridRetrievalResponse là subclass HybridRetrievalResponse nên nằm trong return family dù annotation không viết tên subtype riêng.

| Request/config | Call boundary phía service | Ai thực hiện algorithm/model? |
|---|---|---|
|bm25 |Validate request 194; preprocess 239, index 241, sparse search 243, hydrate 245, postcheck 247 |Injected sparse repository/RPC cùng service hydration; không Search Agent |
|dense |Config guard 227–235; index preflight 249–250; encode 251–253; vector search 263–271; map 273 |Injected E 5 encoder và Supabase vector adapter |
|hybrid, rerank disabled |run_hybrid 197–208 →search_hybrid 220 | Hybrid helper gọi self.search cho bm25/dense rồi fusion |
|hybrid, rerank enabled |search_reranked 211–219, nhận run_hybrid và scorer |Reranking helper quản lý pool/scoring/fallback; không fourth mode |

 Hybrid helper [search_hybrid85–196](../../../src/application/services/hybrid_retrieval.py) có strict failure policy, branch budgets riêng. Một Search outer call hybrid có thể gọi service recursively cho hai branches. Đừng báo số RPC hoặc số model inferences bằng số subqueries mà chưa đếm internals.

Phạm vi handoff này dừng ở delegation: thuật toán sâu đọc [BM25](../../../docs/retrieval-learning/01_BM25_TECHNICAL_WALKTHROUGH.md), [Dense E5](../../../docs/retrieval-learning/02_DENSE_E5_TECHNICAL_WALKTHROUGH.md), [Hybrid RRF](../../../docs/retrieval-learning/03_HYBRID_RRF_TECHNICAL_WALKTHROUGH.md), [Reranking](../../../docs/retrieval-learning/04_RERANKING_TECHNICAL_WALKTHROUGH.md). Các guide đó là supporting material; source vẫn authoritative.

## Return, exceptions và timeout

Service validate request trước dependency calls 194. Với single-backend path, try 226 bắt RetrievalService Error, TimeoutError, DatabaseRepositoryError/RetrievalError ở 276–293; tạo public error detail với message an toàn rồi return RetrievalResponse 294–305. Những exception classes không nằm trong catches vẫn có thể propagate. Search không thêm try/except hoặc retry.

Timeout có nhiều tầng khác nhau:

- SearchOptions không có timeout, Search function không tạo deadline.
- Service self._timeout set 183, asyncio.timeout 236; typed RETRIEVAL_TIMEOUT ở 278–285.
- Hybrid có overall timeout riêng theo service config; rerank có total_timeout_seconds và inference_timeout_seconds trong config/helper. Operational rerank failure có thể FALLBACK với warning; retrieval/integrity failure không bị đổi thành thành công.
- GraphExecutor overall workflow timeout áp từ QuerySearchWorkflow.execute; expiry là TimeoutError /lifecycle FAILED, khác service timeout response/handoff RETRIEVAL_FAILED.
- Supabase client có postgrest timeout 10 s trong bootstrap 40. call_rpc chạy synchronous SDK trong asyncio. to_thread, cancellation của await không chứng minh thread hoặc DB operation dừng tức thì.

Không cộng các timeout thành một SLA cố định; branches/outer timeout có thể lồng nhau và dừng trước.

## Identity và trust boundary

 RetrievalRequest không có request ID. Single-backend service sinh response UUID ở 221; Hybrid /rerank helpers có generation riêng. Query request_id / run_id thuộc ExecutionContext /handoff, không bị ép bằng UUID response. Query text/options được service echo trong response. Search không so response.query/options với request; graph handoff validator làm điều đó. Case context_mismatch minh họa direct Search chấp nhận native response context sai rồi handoff reject; không claim fake failure này là defect đã quan sát từ Supabase.

## Evidence mới và lịch sử

Task 6B chạy real service với fake read/model ports cho 4 profiles, không thực hiện Supabase call. Historical Task 4 có live BM25 / Dense -repeat/ Hybrid /rerank; Task 5 chỉ live graph BM25. Không nâng Task 4 standalone live lên proof graph live all modes. Xem 14 để xem artifacts/timing và initial Dense timeout được giữ nguyên.
