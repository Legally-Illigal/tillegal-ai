# Reranking stage

Reranking bật bằng RerankConfig(enabled=True) được create_query_search chuyển tiếp bootstrap. SearchOptions.mode vẫn hybrid. Mode string rerank bị contract từ chối. Pipeline giữ original RRF raw_score và thêm cross_encoder_score/ranking metadata riêng; consumer dùng evidence order/rank để đọc thứ tự cuối.

## Model đã provision

Model constant `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`, revision1427fd652930e4ba29e8149678df786c240d8825. Local snapshot cùng revision ở C:/Users/Admin/.cache/huggingface/hub/models--cross-encoder--mmarco-mMiniLMv2-L12-H384-v1/snapshots/. Manifest lưu path đầy đủ và SHA256 weights/config/tokenizer.

LocalCrossEncoder `_load` dùng AutoTokenizer/AutoModelForSequenceClassification local_files_only,trust_remote_code=False; CPU float32, eval. Kiểm xlm-roberta, num_labels1,hidden_size384,12 layers và token limit đủ. Metadata response model_name/revision là constants của source; loader tự nó không hash-pin mọi checkpoint đưa vào. Probe dùng snapshot đã quan sát/hash, không suy model identity chỉ từ metadata response.

## Cặp query–passage và scores

candidate pool=max(config.candidate_pool,user top_k), default20. Hybrid trả RRF candidates; validate_candidates kiểm unique IDs, đúng rank/method, stored hash. Scorer nhận query.strip và tuple content. Query được tokenize để kiểm không rỗng/quá dài, tính pair special-token overhead. Từng passage được kiểm độ dài để ghi truncated. Tokenization pairs padding=true,truncation=only_second,max_length512,return_tensors=pt; chỉ passage bị cắt cho model, stored content không đổi.

torch.inference_mode chấm batches default4, logits shape(batch,1). Raw logits có thể âm; không sigmoid, không phải probability/legal confidence. select_candidates sort (-cross_encoder_score,original RRF rank,UUID), giữ user top_k, đổi final rank. Source identity/hash/content/metadata và raw RRF score giữ nguyên. Diagnostics cold/load_seconds/inference_seconds/truncated và mọi CandidateScore được trả trong RerankingMetadata.

## Deadlines và failure

Defaults inference_timeout10s,total40s; total bao Hybrid và closing index reads, Hybrid bên trong vẫn deadline30s. Operational model/tokenization/inference/invalid score/timeout lỗi được phân loại allowlist safe codes, giữ RRF order với reranking.status=FALLBACK và RERANKING_FALLBACK warning. Retrieval/integrity/closing-index/total timeout lỗi → FAILED, không gọi fallback model hoặc ai_core. Empty candidates → SKIPPED_EMPTY/NO_MATCH, không chấm model. Lock giữ tới worker native thoát khi async caller hủy.

## Kết quả

Live response RerankedHybridRetrievalResponse OK/5 evidence, APPLIED;20 candidates; total24.154172s. Model cold=true, load3.964188s, inference1.584810s;20 truncated flags đều false. Các timers này là một sample, total gồm thêm E5/import/DB và checks. Không coi latency single-run là throughput hoặc quality benchmark.

Offline missing-model test dùng directory không tồn tại, nhận FALLBACK explicit thay vì giả APPLIED. Test scorer/total timeout, invalid logits, ranks, duplicate/hash và model cancellation đã chạy trong suite. Không có legal verification stage trong task.
