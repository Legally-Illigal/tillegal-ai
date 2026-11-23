# Function-level execution trace

Line ranges lấy AST source target hiện tại; runtime source không đổi từ baseline.

| Path từ target root | Symbol thực | Dòng |
|---|---|---|
| [src/query_search_bootstrap.py](../../../src/query_search_bootstrap.py) | `QuerySearch.search` | 20–21 |
| [src/query_search_bootstrap.py](../../../src/query_search_bootstrap.py) | `create_query_search` | 24–42 |
| [src/applications/tillegal/agents/query/agent.py](../../../src/applications/tillegal/agents/query/agent.py) | `understand` | 29–95 |
| [src/applications/tillegal/agents/search/agent.py](../../../src/applications/tillegal/agents/search/agent.py) | `SearchOptions.nonblank_policies` | 25–28 |
| [src/applications/tillegal/agents/search/agent.py](../../../src/applications/tillegal/agents/search/agent.py) | `search` | 38–56 |
| [src/retrieval_bootstrap.py](../../../src/retrieval_bootstrap.py) | `create_retrieval_service` | 22–70 |
| [src/application/services/retrieval_service.py](../../../src/application/services/retrieval_service.py) | `_SparseIndex.aware_timestamp` | 111–114 |
| [src/application/services/retrieval_service.py](../../../src/application/services/retrieval_service.py) | `_SparseIndex.identity` | 116–117 |
| [src/application/services/retrieval_service.py](../../../src/application/services/retrieval_service.py) | `_DenseIndex.identity` | 134–136 |
| [src/application/services/retrieval_service.py](../../../src/application/services/retrieval_service.py) | `_failure` | 139–147 |
| [src/application/services/retrieval_service.py](../../../src/application/services/retrieval_service.py) | `RetrievalService.__init__` | 157–190 |
| [src/application/services/retrieval_service.py](../../../src/application/services/retrieval_service.py) | `RetrievalService.search` | 192–305 |
| [src/application/services/retrieval_service.py](../../../src/application/services/retrieval_service.py) | `RetrievalService._prepare_sparse_terms` | 307–317 |
| [src/application/services/retrieval_service.py](../../../src/application/services/retrieval_service.py) | `RetrievalService._search_sparse` | 319–343 |
| [src/application/services/retrieval_service.py](../../../src/application/services/retrieval_service.py) | `RetrievalService._hydrate_sparse_hits` | 345–409 |
| [src/application/services/retrieval_service.py](../../../src/application/services/retrieval_service.py) | `RetrievalService._check_eligibility` | 412–435 |
| [src/application/services/retrieval_service.py](../../../src/application/services/retrieval_service.py) | `RetrievalService._make_evidence` | 438–467 |
| [src/application/services/retrieval_service.py](../../../src/application/services/retrieval_service.py) | `RetrievalService._evidence_warnings` | 470–490 |
| [src/application/services/retrieval_service.py](../../../src/application/services/retrieval_service.py) | `RetrievalService._read_and_validate_index` | 492–533 |
| [src/application/services/retrieval_service.py](../../../src/application/services/retrieval_service.py) | `RetrievalService._check_index_unchanged` | 535–553 |
| [src/application/services/retrieval_service.py](../../../src/application/services/retrieval_service.py) | `RetrievalService._read_dense_index` | 555–598 |
| [src/application/services/retrieval_service.py](../../../src/application/services/retrieval_service.py) | `RetrievalService._check_dense_index_unchanged` | 600–617 |
| [src/application/services/retrieval_service.py](../../../src/application/services/retrieval_service.py) | `RetrievalService._map_dense_evidence` | 619–724 |
| [src/application/services/hybrid_retrieval.py](../../../src/application/services/hybrid_retrieval.py) | `_invalid_context` | 28–37 |
| [src/application/services/hybrid_retrieval.py](../../../src/application/services/hybrid_retrieval.py) | `_validate_context` | 40–50 |
| [src/application/services/hybrid_retrieval.py](../../../src/application/services/hybrid_retrieval.py) | `_check_closing_index` | 53–82 |
| [src/application/services/hybrid_retrieval.py](../../../src/application/services/hybrid_retrieval.py) | `search_hybrid` | 85–196 |
| [src/application/services/reranking.py](../../../src/application/services/reranking.py) | `search_reranked` | 30–176 |
| [src/integrations/embeddings/e5_query_encoder.py](../../../src/integrations/embeddings/e5_query_encoder.py) | `_encoding_error` | 16–24 |
| [src/integrations/embeddings/e5_query_encoder.py](../../../src/integrations/embeddings/e5_query_encoder.py) | `E5QueryEncoder.__init__` | 35–38 |
| [src/integrations/embeddings/e5_query_encoder.py](../../../src/integrations/embeddings/e5_query_encoder.py) | `E5QueryEncoder.encode_query` | 40–44 |
| [src/integrations/embeddings/e5_query_encoder.py](../../../src/integrations/embeddings/e5_query_encoder.py) | `E5QueryEncoder._get_model` | 46–67 |
| [src/integrations/embeddings/e5_query_encoder.py](../../../src/integrations/embeddings/e5_query_encoder.py) | `E5QueryEncoder._encode` | 69–101 |
| [src/integrations/embeddings/cross_encoder_reranker.py](../../../src/integrations/embeddings/cross_encoder_reranker.py) | `LocalCrossEncoder.__init__` | 13–17 |
| [src/integrations/embeddings/cross_encoder_reranker.py](../../../src/integrations/embeddings/cross_encoder_reranker.py) | `LocalCrossEncoder.score_pairs` | 19–20 |
| [src/integrations/embeddings/cross_encoder_reranker.py](../../../src/integrations/embeddings/cross_encoder_reranker.py) | `LocalCrossEncoder._load` | 22–44 |
| [src/integrations/embeddings/cross_encoder_reranker.py](../../../src/integrations/embeddings/cross_encoder_reranker.py) | `LocalCrossEncoder._score` | 46–100 |
| [src/applications/tillegal/retrieval/rank_fusion.py](../../../src/applications/tillegal/retrieval/rank_fusion.py) | `_invalid` | 21–30 |
| [src/applications/tillegal/retrieval/rank_fusion.py](../../../src/applications/tillegal/retrieval/rank_fusion.py) | `reciprocal_rank_fusion` | 33–95 |
| [src/applications/tillegal/retrieval/reranker.py](../../../src/applications/tillegal/retrieval/reranker.py) | `validate_candidates` | 14–33 |
| [src/applications/tillegal/retrieval/reranker.py](../../../src/applications/tillegal/retrieval/reranker.py) | `select_candidates` | 36–55 |
| [src/integrations/database/repositories/supabase_vector_repository.py](../../../src/integrations/database/repositories/supabase_vector_repository.py) | `SupabaseVectorRepository.__init__` | 22–23 |
| [src/integrations/database/repositories/supabase_vector_repository.py](../../../src/integrations/database/repositories/supabase_vector_repository.py) | `SupabaseVectorRepository.search` | 25–65 |
| [src/integrations/database/repositories/supabase_vector_repository.py](../../../src/integrations/database/repositories/supabase_vector_repository.py) | `SupabaseVectorRepository._execute_search` | 67–78 |
| [src/integrations/database/repositories/supabase_vector_repository.py](../../../src/integrations/database/repositories/supabase_vector_repository.py) | `_format_vector` | 81–83 |
| [src/integrations/database/repositories/supabase_vector_repository.py](../../../src/integrations/database/repositories/supabase_vector_repository.py) | `_duration_ms` | 86–87 |
| [src/integrations/database/repositories/sparse_retrieval_repository.py](../../../src/integrations/database/repositories/sparse_retrieval_repository.py) | `SparseRetrievalRepository.__init__` | 22–23 |
| [src/integrations/database/repositories/sparse_retrieval_repository.py](../../../src/integrations/database/repositories/sparse_retrieval_repository.py) | `SparseRetrievalRepository.search` | 25–40 |

## Entry, input và output chung

Caller gọi QuerySearch.search(question). understand validate/NFC/split/prefix/time/topic, trả QueryPlan.model_dump. search validate QueryPlan và SearchOptions; clarification trả state sớm. Nếu hợp lệ, comprehension tạo tuple RetrievalRequest(query=subquery.text, **options.model_dump()). Vòng await giữ từng response nguyên object và status; response FAILED dừng vòng. QueryInputError/ValidationError propagate; classified service errors nằm trong response. Không catch chung rồi tạo evidence giả.

## BM25

Search → RetrievalService.search(mode=bm25) → _prepare_sparse_terms(query.strip) dùng tokenize_sparse_text NFC/lower → _read_and_validate_index READY và config đúng → _search_sparse → SparseRetrievalRepository.search → RPC search_sparse_legal_chunks → _hydrate_sparse_hits đọc chunks theo IDs, memoize source theo document → _check_index_unchanged. Output UnifiedEvidence có score BM25; warnings do _warnings tạo. DB errors thành typed DATABASE_READ_FAILED, deadline thành RETRIEVAL_TIMEOUT.

## Dense

Search → service.search(mode=dense) kiểm dependencies → _read_dense_index → E5QueryEncoder.encode_query → asyncio.to_thread(_encode) → lock/_get_model/local SentenceTransformer → prefix/tokenization/token-limit → model.encode normalize → validate_query_vector. Service validate lại vector → VectorSearchRequest → SupabaseVectorRepository.search → _execute_search → _format_vector và search_legal_chunks RPC. _map_dense_evidence hydrate/check hash/identity, _check_dense_index_unchanged rồi response. Missing model/index, malformed vector và invalid repository payload đều có typed failure. Lượt live đầu dừng ở encoding timeout; lần repeat hoàn tất đến vector RPC.

## Hybrid

Service.search nhận mode hybrid → nested run_hybrid → search_hybrid. Nó dựng hai branch requests với candidate budgets 20/20, gọi lại service.search tuần tự bm25 rồi dense. _validate_context xác nhận request filters/index READY; branch errors được prefix stage. Sau hai branch thành công/no-match, _check_closing_index cả hai readers, reciprocal_rank_fusion hợp nhất identity/rank. Failed branch không được xem là NO_MATCH; lỗi làm evidence/ranking final rỗng.

## Reranking

Service nhận Hybrid + config.enabled → search_reranked → internal request top_k=max(candidate_pool, user top_k), run_hybrid với shared deadline. validate_candidates kiểm hashes/ranks. LocalCrossEncoder.score_pairs → thread/_score, lock/_load, query+passage pairs, logits. select_candidates đổi thứ tự/rank, giữ content/provenance/raw RRF score. Closing index reads kéo dài kiểm consistency qua inference. Operational scorer error dùng visible RRF FALLBACK; retrieval/integrity/total deadline lỗi trả FAILED. Subclass response trở lại SearchState không bị flatten.

## Probe và đo lường

`evidence/live_probe.py`: probe(mode) load settings từ dotenv_values mapping, options từ artifact explicit; chạy pipeline dưới outer 45s, service defaults 30s; rerank default total40/inference10. summary(response) xuất IDs/hash/digests thay text và metadata thô. BM25 direct call dùng chính requests[0]. Mỗi model probe chạy process mới, subprocess watchdog90 là giới hạn cleanup process, không tăng service deadline. Các timers chỉ đo await QuerySearch/direct, không đo toàn interpreter launch hoặc thread cleanup sau timeout.
