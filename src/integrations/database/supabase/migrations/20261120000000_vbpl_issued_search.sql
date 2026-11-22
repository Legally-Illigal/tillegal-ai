CREATE TABLE public.vbpl_search_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    issued_from DATE NOT NULL,
    issued_to DATE NOT NULL CHECK (issued_to >= issued_from AND issued_to - issued_from <= 365),
    status TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING','RUNNING','SUCCEEDED','FAILED')),
    next_page INTEGER NOT NULL DEFAULT 1,
    total INTEGER,
    attempts INTEGER NOT NULL DEFAULT 0,
    owner TEXT,
    lease_until TIMESTAMPTZ,
    available_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX vbpl_search_active_range ON public.vbpl_search_jobs(issued_from, issued_to)
    WHERE status IN ('PENDING','RUNNING');
CREATE INDEX vbpl_search_pending ON public.vbpl_search_jobs(available_at, created_at);
CREATE TABLE public.vbpl_search_items (
    job_id UUID NOT NULL REFERENCES public.vbpl_search_jobs(id) ON DELETE CASCADE,
    record_id TEXT NOT NULL,
    issued_on DATE NOT NULL,
    source_url TEXT NOT NULL,
    metadata JSONB NOT NULL,
    PRIMARY KEY(job_id, record_id)
);
ALTER TABLE public.vbpl_search_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.vbpl_search_items ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.vbpl_search_jobs, public.vbpl_search_items FROM anon, authenticated;
GRANT ALL ON public.vbpl_search_jobs, public.vbpl_search_items TO service_role;
