ALTER TABLE public.crawl_jobs ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS idx_crawl_jobs_claimable
    ON public.crawl_jobs (created_at)
    WHERE status IN ('PENDING', 'RUNNING');
