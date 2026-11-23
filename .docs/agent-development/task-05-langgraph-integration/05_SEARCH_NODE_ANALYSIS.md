# Search node

Owner QuerySearchNodes.search, gọi agents/search/agent.py:search(state.plan, pipeline.retrieval, pipeline.options). Không gọi cả QuerySearch.search vì Query đã chạy ở node trước. Đây là reuse entrypoints đã kiểm, không copy request construction hoặc retrieval algorithm.

Search Agent giữ validation, prebuild RetrievalRequest, tuần tự chạy subqueries và stop tại FAILED. Service dispatch BM25/Dense/Hybrid/rerank theo config. Date/mode/top_k/policies lấy từ injected SearchOptions; rerank/model config thuộc service bootstrap, giữ trong response metadata khi có. User text/state không tự cấp policy.

Sau await, JudgeHandoff.from_search kiểm context consistency. READY → graph SEARCH_COMPLETED; mọi response NO_MATCH → NO_MATCH; nativeFAILED → RETRIEVAL_FAILED. Update giữ nguyên SearchState, packet typed và safe error codes cho append_unique. Warnings/full error details giữ trong canonical responses; properties handoff derive lại.

Native response object không serialize/projection trong node. Tests real service với fake ports cho4 profiles assert cùng object ở search_result/packet, sau JSON round-trip vẫn giữ đúng subtype, UUID/date, evidence, fusion/reranking. Không flatten/dedup xuyên query vì có thể làm mất per-query rank/context.

Khi failure sau query trước đã có kết quả, packet giữ prior history nhưng RETRIEVAL_FAILED. Không tự publish evidence partial như legal answer. NO_MATCH giữ empty evidence thay vì tạo row giả. Exceptions ngoài classified response propagate theo executor.

Live Task 5 chỉ BM25 graph. Các model backends qua graph mới VERIFIED OFFLINE; Task 4 live là historical evidence. Native thread có thể tiếp tục sau coroutine cancellation; graph tests dùng async fakes, không khẳng định dừng inference tức thời. Shared service được compose một lần, không reinitialize theo node/request.
