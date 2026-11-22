# Crawl VBPL bằng crawl_jobs

Đối chiếu pipeline ở commit `7ff0a90`: tiếp tục dùng `VbplDocumentIngestionService`
cho tải file, Supabase Storage, Markdown (HTML rồi fallback Word khi không có HTML),
upsert source document, parse/chunk, embedding và sparse postings. Không thay schema
corpus/index/Storage. Không ép index READY. Thiếu antiword vẫn thành công ở cấp lưu
văn bản và ghi `markdown_skipped_reason`. Markdown rỗng là `EmptyMarkdownError` cho
riêng văn bản, các văn bản tiếp theo vẫn chạy.

## Triển khai schema (người vận hành thực hiện riêng)

Migration mới: [20261121000000_crawl_job_modes.sql](../src/integrations/database/supabase/migrations/20261121000000_crawl_job_modes.sql).
Chỉ thay `crawl_jobs`: thêm `crawl_mode` mặc định LASTMOD, `issued_from`, `issued_to`;
cho `crawl_date` NULL; CHECK hai chế độ loại trừ nhau; hai partial unique index chỉ
áp dụng PENDING/RUNNING. `created_at` giữ nguyên. Unique index sẽ làm migration
thất bại an toàn nếu có job active trùng; cần kiểm tra và thống nhất xử lý riêng,
không tự xóa/cancel job để vượt qua lỗi.

1. Dừng worker cũ trước khi triển khai; đối chiếu migration đã áp dụng trong
   `schema_migrations`. Kiểm tra active duplicates theo source/date trước khi tạo index.
2. Review migration mới và các migration đang pending. Migrator của dự án chạy **mọi**
   migration pending: không chạy mù trên database chưa đối chiếu lịch sử.
3. Sau khi duyệt, người vận hành chạy `uv run python -m src.integrations.database.migrator`.
   Tác vụ refactor này không chạy lệnh đó hoặc truy cập Supabase.
4. Triển khai API và worker mới cùng nhau. Để `SUPABASE_AUTO_MIGRATE=false` khi chạy API
   nếu schema đã được áp dụng riêng.

Hai migration lịch sử tạo `vbpl_search_jobs`/`vbpl_search_items` được giữ nguyên.
Runtime mới không đọc/ghi hai bảng này. Migration bổ sung
[20261121010000_drop_legacy_vbpl_search_tables.sql](../src/integrations/database/supabase/migrations/20261121010000_drop_legacy_vbpl_search_tables.sql)
sẽ xóa vĩnh viễn hai bảng cùng dữ liệu khi người vận hành chạy migrator.
Migration không dùng CASCADE, không chuyển job tự động, không tác động corpus/Storage/crawl_jobs.
Trước khi áp dụng trên database cũ, dừng worker search cũ và xuất lịch sử cần giữ.
Job ở hai bảng cũ không xuất hiện qua API mới. Nếu cần chuyển: xuất metadata/checkpoint,
đối chiếu trạng thái ingestion từng item, lập mapping UUID cũ/mới, review rồi import
thành `crawl_jobs` trong đợt riêng. Chỉ đánh SUCCEEDED item đã có bằng chứng ingestion
thành công; không suy từ trạng thái discovery. Hoàn tất chuyển và kiểm chứng trước khi áp dụng migration xóa bảng.

## Chạy crawl văn bản ban hành tháng 01/2024

Các bước dưới đây dành cho người vận hành; chưa được thực hiện trong refactor.

1. Hoàn thành bước schema ở trên. Chuẩn bị cấu hình database, Supabase URL/service role,
   model embedding và `VBPL_SEARCH_ACTION_ID` hiện hành ở môi trường vận hành.
   Không đưa giá trị bí mật vào terminal output/tài liệu. Giữ timeout/giới hạn dung lượng
   hiện có; cấu hình khoảng nghỉ bằng `VBPL_REQUEST_PAUSE_SECONDS`.
2. Chạy API theo entry point của dự án (`uv run uvicorn src.main:app --host 127.0.0.1 --port 8000`).
   Nếu dùng worker riêng, đặt `VBPL_API_WORKER_ENABLED=false` trước khi chạy API.
3. Ở terminal khác, chạy worker duy nhất cho cả hai chế độ:

   ```powershell
   uv run python -m src.workers.worker
   ```

4. Tạo **một** job tháng 01/2024, bao gồm ngày 01 và 31:

   ```powershell
   $body = @{ crawl_mode = 'ISSUED_RANGE'; issued_from = '2024-01-01'; issued_to = '2024-01-31' } | ConvertTo-Json
   $job = Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/ingestion/vbpl/crawl' -ContentType 'application/json' -Body $body
   $job.id
   ```

   `POST /ingestion/vbpl/search` với `issued_from`/`issued_to` là alias cho cùng loại job.
   Search qua HTTP, page size 10, khoảng ngày gửi từ 00:00:00 ngày đầu tới 23:59:59.999
   ngày cuối; parser kiểm tra lại ngày từng văn bản. Không dùng Playwright.
5. Xem tiến độ:

   ```powershell
   Invoke-RestMethod -Uri "http://127.0.0.1:8000/ingestion/vbpl/jobs/$($job.id)" | ConvertTo-Json -Depth 12
   ```

   Worker tự chạy hết trang và văn bản; không phải gọi lại theo batch. `result` gồm:
   - `phase`: discovery, ingestion, complete.
   - `discovery`: con trỏ trang/shard tiếp theo, tổng, cờ complete; không lưu toàn văn.
   - `ingestion.documents`: URL/provenance, status, attempts, lỗi, ID đã lưu, số chunk/
     embedding/sparse, lý do bỏ Markdown và `document_indexing_complete` độc lập index chung.
   - `summary`: discovered/succeeded/failed/pending/stored/partial_failure,
     document_indexing_complete/document_indexing_unknown.
   - `index_status`: dense/sparse, checked_at và scope global; GET đọc trạng thái hiện tại.

   SUCCEEDED nghĩa là đã thử hết đợt, không đảm bảo mọi văn bản thành công hoặc retrieval
   sẵn sàng. Số lượng từng văn bản là ảnh chụp, không thay kiểm tra index hiện tại.
   FAILED cấp job dành cho discovery/config/lease recovery hết retry. Lỗi document
   lưu tên loại lỗi, không ghi URL ký hoặc nội dung exception có thể chứa credentials.
6. Retry riêng văn bản lỗi sau khi sửa nguyên nhân:

   ```powershell
   Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/ingestion/vbpl/jobs/$($job.id)/retry-failed"
   ```

   Chỉ áp dụng job SUCCEEDED/FAILED có document FAILED, trả 409 khi đang chạy hoặc có
   job active cùng tiêu chí. Thành công trước đó giữ nguyên, không ingest lại. Restart
   tự resume từ checkpoint, không cần endpoint này cho job đang PENDING/lease hết hạn.

## Lastmod cũ và giới hạn resume

`POST /ingestion/vbpl/crawl` với `{"crawl_date":"2024-01-15"}` vẫn dùng LASTMOD.
Body rỗng mặc định ngày hiện tại Việt Nam. LASTMOD chỉ có một ngày sitemap lastmod,
không phải tháng ban hành; không gửi issued dates cùng job LASTMOD.

Checkpoint ghi sau mỗi trang/shard và mỗi văn bản, giữ các trường result sẵn có.
Transaction chỉ bao quanh thao tác DB ngắn, không tải file/embedding trong transaction.
Job giữ lease suốt đợt, heartbeat giám sát đồng thời và hủy coroutine khi mất lease;
nhường event loop giữa các batch không tăng attempts. Một thao tác đồng bộ đã bắt đầu
trong thread có thể kết thúc sau cancellation; không thể thu hồi I/O đã gửi. Pipeline
upsert/hash Storage hiện có bảo đảm khả năng chạy lại nếu crash giữa side effect và
checkpoint; không hứa exactly-once cho văn bản chưa được checkpoint thành công.

Search phụ thuộc hợp đồng HTTP/Next-Action của VBPL. Response sai, thiếu trang, đổi total
hoặc lặp trang không tiến triển làm job retry/FAILED, không đánh thành công thiếu dữ liệu.
Không có snapshot phía server; tập dữ liệu thay đổi cần người vận hành đối chiếu riêng.

## Các file trong refactor

- [DTO](../src/application/dto/crawl_job.py), [store interface](../src/application/interfaces/crawl_job_store.py),
  [repository](../src/integrations/database/repositories/crawl_job_repository.py).
- [Service](../src/application/services/vbpl_crawl_service.py),
  [schemas](../src/api/schemas/crawl.py), [routes](../src/api/routes/ingestion.py).
- [Worker](../src/workers/tasks.py), [worker entry point/logging](../src/workers/worker.py),
  [HTTP search](../src/applications/tillegal/ingestion/crawler/vbpl_search.py),
  [ingestion](../src/application/services/vbpl_document_ingestion_service.py).
- Migration mới ở trên và tài liệu này.
- [Worker/API tests](../tests/unit/applications/tillegal/ingestion/crawler/test_vbpl_crawl_worker.py),
  [search tests](../tests/unit/applications/tillegal/ingestion/crawler/test_vbpl_search.py),
  [ingestion tests](../tests/unit/applications/tillegal/ingestion/crawler/test_vbpl_document_ingestion_service.py),
  [repository tests](../tests/unit/integrations/database/test_crawl_job_repository.py).
- Loại bỏ implementation hai bảng: `vbpl_search_repository.py`, `vbpl_ingestion_repository.py`,
  `vbpl_search_worker.py`, `vbpl_search_ingestion_worker.py` và ba test riêng tương ứng.
  Thay test discovery worker/API cũ bằng test worker thống nhất; giữ test HTTP parser.

Test dùng HTTP/Storage/DB giả, không chạy crawl hay migration thật. Kiểm tra concurrency
repository dùng transaction model trong bộ nhớ; unique index và advisory lock cần
kiểm chứng thêm trên PostgreSQL staging trước rollout, không phải chứng nhận race test
trên Supabase thật.

## Đồng bộ báo cáo indexing của job cũ (không crawl lại)

Code mới bỏ `retrieval_ready`, thêm `document_indexing_complete` và
`document_indexing_unknown` trong summary. Đây là mức hoàn tất dữ liệu của từng
văn bản, không thay thế điều kiện READY/usage_policy/ngày hiệu lực của truy vấn RAG.
API GET đọc index_status trực tiếp từ DB (scope global, checked_at); checkpoint cuối
job lưu snapshot tương ứng. Checkpoint lịch sử thiếu sparse_chunk_count được báo null
(chưa xác định), không suy từ retrieval_ready cũ.

Để cập nhật JSONB đã lưu theo dữ liệu hiện tại, dừng API/worker, sao lưu result của job,
rồi chạy SQL dưới đây trong Supabase SQL Editor. Đổi UUID ở WHERE nếu muốn đồng bộ job
khác. Script chỉ cập nhật báo cáo của một job đã kết thúc, không tạo chunk/vector,
không sửa status/attempts của job hay trạng thái index. Không cần migration.

```sql
BEGIN;
SET LOCAL search_path = public, extensions;

-- Khóa job để không ghi đè khi retry đang được yêu cầu.
SELECT id, status FROM public.crawl_jobs
WHERE id = '00df87da-7812-4bdd-82b6-b0ba15ce3f1d'
FOR UPDATE;

WITH target AS (
    SELECT * FROM public.crawl_jobs
    WHERE id = '00df87da-7812-4bdd-82b6-b0ba15ce3f1d'
      AND status IN ('SUCCEEDED', 'FAILED', 'CANCELLED')
), measured AS (
    SELECT j.id, item.key, item.value, source.id AS source_id,
           counts.chunks, counts.dense_count, counts.sparse_count
    FROM target j
    CROSS JOIN LATERAL jsonb_each(
        COALESCE(j.result #> '{ingestion,documents}', '{}'::jsonb)
    ) item
    LEFT JOIN public.source_documents source
      ON source.source_id = j.source_id
     AND source.source_url = COALESCE(item.value->>'url', item.key)
    CROSS JOIN LATERAL (
        SELECT count(*) AS chunks,
          count(*) FILTER (WHERE EXISTS (
            SELECT 1 FROM public.dense_chunk_embeddings e
            JOIN public.dense_indexes i ON i.id = e.dense_index_id
            WHERE e.retrieval_chunk_id = c.id
              AND i.index_name = 'vbpl-multilingual-e5-small-v1'
              AND e.status = 'INDEXED' AND e.embedding IS NOT NULL
              AND vector_dims(e.embedding) = i.embedding_dimension
          )) AS dense_count,
          count(*) FILTER (WHERE EXISTS (
            SELECT 1 FROM public.sparse_chunk_documents s
            JOIN public.sparse_indexes i ON i.id = s.sparse_index_id
            WHERE s.retrieval_chunk_id = c.id
              AND i.index_name = 'vbpl-bm25-unicode-v1'
              AND s.status = 'INDEXED'
              AND (s.token_count = 0 OR EXISTS (
                SELECT 1 FROM public.sparse_postings p
                WHERE p.sparse_chunk_document_id = s.id AND p.sparse_index_id = i.id
              ))
          )) AS sparse_count
        FROM public.retrieval_chunks c WHERE c.source_document_id = source.id
    ) counts
), items AS (
    SELECT id, key,
      (value - 'retrieval_ready') || jsonb_build_object(
        'chunk_count', chunks,
        'embedding_count', dense_count,
        'sparse_chunk_count', sparse_count,
        'document_indexing_complete', chunks > 0 AND chunks = dense_count AND chunks = sparse_count,
        'indexing_checked_at', statement_timestamp()
      ) AS value
    FROM measured
), reports AS (
    SELECT id, jsonb_object_agg(key, value) AS documents,
      count(*) FILTER (WHERE (value->>'document_indexing_complete')::boolean) AS complete_count
    FROM items GROUP BY id
)
UPDATE public.crawl_jobs j
SET result = j.result || jsonb_build_object(
    'ingestion', COALESCE(j.result->'ingestion', '{}'::jsonb)
        || jsonb_build_object('documents', r.documents),
    'summary', (COALESCE(j.result->'summary', '{}'::jsonb) - 'retrieval_ready')
        || jsonb_build_object('document_indexing_complete', r.complete_count,
                              'document_indexing_unknown', 0),
    'index_status', jsonb_build_object(
        'dense', (SELECT status FROM public.dense_indexes
                  WHERE index_name = 'vbpl-multilingual-e5-small-v1'),
        'sparse', (SELECT status FROM public.sparse_indexes
                   WHERE index_name = 'vbpl-bm25-unicode-v1'),
        'checked_at', statement_timestamp(), 'scope', 'global'
    )
), updated_at = now()
FROM reports r WHERE j.id = r.id
RETURNING j.id, j.result->'summary' AS summary, j.result->'index_status' AS index_status;

COMMIT;
```

Nếu UPDATE 0 hàng, kiểm tra UUID, trạng thái job và ingestion.documents; không ép job
RUNNING thành terminal chỉ để chạy script. Các count là kết quả đối soát hiện tại,
không phải số lượng của riêng lần retry. Một source chưa có trong DB sẽ có count 0.
Status FAILED của văn bản giữ nguyên kể cả khi đã lưu một phần trước khi lỗi.
Sau đó khởi động API mới và GET `/ingestion/vbpl/jobs/{id}` để xem kết quả. Nếu index
chung STALE, đó là vấn đề dữ liệu index cần kiểm tra riêng; script không ép READY.
