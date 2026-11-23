ALTER TABLE public.vbpl_search_items
    ADD COLUMN ingestion_status TEXT NOT NULL DEFAULT 'PENDING'
        CHECK (ingestion_status IN ('PENDING','RUNNING','SUCCEEDED','FAILED')),
    ADD COLUMN ingestion_attempts INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN ingestion_result JSONB,
    ADD COLUMN ingestion_error TEXT,
    ADD COLUMN ingested_at TIMESTAMPTZ;
CREATE INDEX vbpl_search_items_ingestion ON public.vbpl_search_items(job_id, ingestion_status, record_id);
