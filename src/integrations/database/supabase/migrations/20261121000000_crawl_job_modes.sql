-- Existing history and legacy search tables are deliberately untouched.
ALTER TABLE public.crawl_jobs
    ADD COLUMN crawl_mode text NOT NULL DEFAULT 'LASTMOD',
    ADD COLUMN issued_from date,
    ADD COLUMN issued_to date,
    ALTER COLUMN crawl_date DROP NOT NULL;

ALTER TABLE public.crawl_jobs ADD CONSTRAINT crawl_jobs_mode_dates CHECK (
    (crawl_mode = 'LASTMOD' AND crawl_date IS NOT NULL
        AND issued_from IS NULL AND issued_to IS NULL)
    OR
    (crawl_mode = 'ISSUED_RANGE' AND crawl_date IS NULL
        AND issued_from IS NOT NULL AND issued_to IS NOT NULL AND issued_from <= issued_to)
);

-- Fail safely if pre-existing active duplicates require operator reconciliation.
CREATE UNIQUE INDEX crawl_jobs_active_lastmod
    ON public.crawl_jobs (source_id, crawl_mode, crawl_date)
    WHERE status IN ('PENDING', 'RUNNING') AND crawl_mode = 'LASTMOD';
CREATE UNIQUE INDEX crawl_jobs_active_issued_range
    ON public.crawl_jobs (source_id, crawl_mode, issued_from, issued_to)
    WHERE status IN ('PENDING', 'RUNNING') AND crawl_mode = 'ISSUED_RANGE';
