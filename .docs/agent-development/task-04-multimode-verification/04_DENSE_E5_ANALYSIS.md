# Dense E5 thực tế

## Model và provisioning

Source `src/integrations/embeddings/e5_query_encoder.py` công bố intfloat/multilingual-e5-small, prefix `query: `. Local path đã kiểm:

`C:/Users/Admin/.cache/huggingface/hub/models--intfloat--multilingual-e5-small/snapshots/614241f622f53c4eeff9890bdc4f31cfecc418b3`

Revision là thư mục snapshot và refs/main local quan sát được. [Model/index manifest](evidence/model-and-index.json) giữ SHA256/size weights, tokenizer/config và các file cấu hình. Chưa so hash với registry từ network; không coi tên thư mục là cryptographic attestation của checkpoint.

Model config local: Transformer + mean-token Pooling + Normalize module. sentence_bert_config max_seq_length=512, do_lower_case=false. Pooling config dimension384, mean_tokens=true, CLS/max/sqrt pooling=false. Package SentenceTransformers đang dùng có implementation ở `.venv/Lib/site-packages/sentence_transformers/sentence_transformer/modules/pooling.py` dòng225–230, tính sum(token_embeddings * weighted_mask)/clamped sum(mask). Normalize module cùng thư mục, normalize.py dòng23, dùng F.normalize(p=2,dim=1). Không dump token IDs hoặc embeddings của câu hỏi trong report.

## Query-time processing

1. Query Agent NFC text; encoder strip, giữ case/dấu. Blank query là EMPTY_QUERY.
2. Encoder lazy load SentenceTransformer(device=cpu,local_files_only=True,trust_remote_code=False). Chỉ load directory có sẵn, không download.
3. `_get_model` kiểm dimension384 và token limit thuộc1–512; không tự chứng minh model revision đã dùng lúc indexing.
4. `_encode` thêm query prefix đúng một lần; tokenizer add_special_tokens=true,truncation=false để kiểm token limit trước encode. Nếu vượt max_seq_length → QUERY_TOKEN_LIMIT.
5. model.encode một row, batch_size1, numpy, normalize_embeddings=True, show_progress_bar=False,prompt="". Empty prompt ngăn checkpoint tự thêm default prompt lần hai.
6. validate_query_vector yêu cầu 384 finite numeric values, không bool, norm lệch1 tối đa1e-4. Không tự pad/truncate vector.

Thread lock giữ tới khi native worker xong; caller timeout có thể trả trước khi load/inference thread kết thúc. Không gọi vector RPC sau service coroutine đã bị hủy ở encoding. Probe đầu cho thấy startup-sensitive timeout, chưa chứng minh nguyên nhân chính là disk cache hoặc model load.

## Index/RPC

Observed dense index là vbpl-multilingual-e5-small-v1, UUID 0fe7b3a9-d051-41c5-ae61-257790c997f9, versionv1, READY, updated_at2026-11-14T08:27:44.253063+00:00, provider sentence-transformers, model multilingual-e5-small, dimension384, cosine; metadata normalized=true, query_prefix=query:, passage_prefix=passage: với trailing spaces theo JSON manifest.

Service so metadata với contract trước encode; kiểm lại sau retrieval. Vector request serialize tuple thành string `[v1,v2,...]` với `.9g`, truyền p_query_embedding, index_name, top_k, as_of_date, policies cho RPC search_legal_chunks. Repository đưa sync HTTP off-thread, parse typed RetrievedEvidence, service kiểm thêm stored chunk/hash/eligibility.

SQL mới `20261111130000_multilingual_e5_embeddings.sql` có vector variable dimension và nhánh384/1536; nhánh384 filter index READY/dim384/cosine/embedding INDEXED/policy/date; cosine similarity=1-distance, ORDER BY vector distance rồi chunk UUID. Migration cũ có1536 vẫn tồn tại lịch sử; Task4 không chạy hoặc sửa migration. Live metadata + successful vector paths xác nhận cấu hình384 hiện có, không suy chỉ từ tên file.

## Kết quả và giới hạn

Dense standalone đầu FAILED/RETRIEVAL_TIMEOUT ở encoding sau30.001632s. Repeat process mới cùng deadline đạt OK/5 evidence sau16.217589s; Hybrid/rerank cũng thực hiện Dense branch thành công. Dimension runtime384; hash content đạt; warnings temporal được giữ. Đây là VERIFIED REAL SUPABASE cho case thành công, PARTIAL về lặp lại cold-start. Không đổi timeout để ép kết quả, không rebuild index hoặc đánh giá quality/Recall.
