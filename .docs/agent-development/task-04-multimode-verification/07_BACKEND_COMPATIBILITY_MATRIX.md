# Ma trận backend và consistency

| Mode/stage | Tài nguyên | Contract / dependencies | Offline | Live mới | Blocker/giới hạn |
|---|---|---|---|---|---|
| BM25 | READY sparse index, tokenizer tương thích | RetrievalResponse; sparse/chunk/source/index read repositories | VERIFIED | VERIFIED REAL SUPABASE,5 evidence; direct parity | BEST_EFFORT, không transaction snapshot |
| Dense E5 | Local E5,384,cosine READY index | RetrievalResponse; E5/vector/index/chunk readers | VERIFIED | VERIFIED REAL SUPABASE ở repeat;5 evidence | First cold attempt timeout encoding30s; startup stability PARTIAL |
| Hybrid RRF | Cả hai backend, candidate20/20,rrf60 | HybridRetrievalResponse.fusion | VERIFIED | VERIFIED REAL SUPABASE,5 evidence | Shared30s deadline, strict failures |
| Hybrid + rerank | Local cross-encoder, pool20,batch4 | RerankedHybridRetrievalResponse.reranking | VERIFIED | VERIFIED REAL SUPABASE,APPLIED,5 evidence | Total40s/scorer10s; operational fallback phải đọc metadata |

Tất cả dùng cùng QueryPlan và trusted date/policies/top_k; chỉ mode/config backend khác. Test mới kiểm mapping, dispatch, propagation toàn response, provenance/hash/index/warnings và absence ai_core. Model inputs/ranking có thể khác nhau theo mode, không đòi top5 giống nhau.

Live cross-mode từ [cross-mode.json](evidence/cross-mode.json): mọi successful plan bằng nhau, mọi returned content hash khớp; không load ai_core modules. BM25/Dense-repeat shared0; BM25/Hybrid shared2; Hybrid/rerank shared2; Dense-repeat/Hybrid shared2. Mọi shared chunk được so digest tất cả UnifiedEvidence fields ngoại trừ rank/raw_score/score_kind/retrieval_method, không conflict. Cặp shared0 không cung cấp bằng chứng provenance parity trên chunk chung, không ghi nhận như một so sánh thành công có samples.

Source metadata được so digest, không ghi toàn raw metadata vào log. Index identifiers/updated_at được lưu ở response/fusion; cùng observed index không chứng minh corpus immutable hoặc cùng transaction. Từ khoảnh khắc checks đến lần sau dữ liệu có thể đổi.

Compatibility dimension: source DTO/encoder/service preflight và live dense index đều384. SQL lịch sử1536 đã có migration variable-dimension với nhánh384; không thay schema trong Task4. Native response giữ UUID/date/model subclass, caller JSON cần model_dump(mode=json) đúng subtype. Không map sang quote/citation legacy hoặc nâng legally verified.
