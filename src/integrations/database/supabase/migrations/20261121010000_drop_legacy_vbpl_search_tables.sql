-- Destructive cleanup: permanently removes legacy search jobs/items and their data.
-- Stop legacy workers and export any required history before applying.
-- Crawl lifecycle/checkpoints now live exclusively in public.crawl_jobs.
-- No CASCADE: unexpected external dependencies must be reviewed explicitly.
DROP TABLE IF EXISTS public.vbpl_search_items;
DROP TABLE IF EXISTS public.vbpl_search_jobs;
