CREATE OR REPLACE FUNCTION public.mark_affected_dense_indexes_stale(p_index_ids UUID[])
RETURNS VOID
LANGUAGE SQL
SECURITY INVOKER
SET search_path = public, extensions
AS $$
    UPDATE public.dense_indexes
    SET status = 'STALE', updated_at = now()
    WHERE status = 'READY'
        OR id = ANY(COALESCE(p_index_ids, ARRAY[]::UUID[]));
$$;

CREATE OR REPLACE FUNCTION public.mark_affected_sparse_indexes_stale(p_index_ids UUID[])
RETURNS VOID
LANGUAGE PLPGSQL
SECURITY INVOKER
SET search_path = public, extensions
AS $$
BEGIN
    UPDATE public.sparse_indexes AS sparse_index
    SET
        status = 'STALE',
        document_count = stats.document_count,
        total_token_count = stats.total_token_count,
        average_document_length = CASE
            WHEN stats.document_count = 0 THEN 0
            ELSE stats.total_token_count::DOUBLE PRECISION / stats.document_count
        END,
        updated_at = now()
    FROM (
        SELECT
            sparse_index_id,
            count(*) FILTER (WHERE status = 'INDEXED') AS document_count,
            COALESCE(sum(token_count) FILTER (WHERE status = 'INDEXED'), 0) AS total_token_count
        FROM public.sparse_chunk_documents
        WHERE sparse_index_id = ANY(COALESCE(p_index_ids, ARRAY[]::UUID[]))
        GROUP BY sparse_index_id
    ) AS stats
    WHERE sparse_index.id = stats.sparse_index_id;

    UPDATE public.sparse_indexes
    SET status = 'STALE', updated_at = now()
    WHERE status = 'READY'
        OR id = ANY(COALESCE(p_index_ids, ARRAY[]::UUID[]));

    UPDATE public.sparse_indexes
    SET document_count = 0, total_token_count = 0, average_document_length = 0
    WHERE id = ANY(COALESCE(p_index_ids, ARRAY[]::UUID[]))
        AND NOT EXISTS (
            SELECT 1
            FROM public.sparse_chunk_documents AS sparse_document
            WHERE sparse_document.sparse_index_id = sparse_indexes.id
                AND sparse_document.status = 'INDEXED'
        );
END;
$$;

REVOKE ALL ON FUNCTION public.mark_affected_dense_indexes_stale(UUID[]) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.mark_affected_dense_indexes_stale(UUID[]) TO service_role;
REVOKE ALL ON FUNCTION public.mark_affected_sparse_indexes_stale(UUID[]) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.mark_affected_sparse_indexes_stale(UUID[]) TO service_role;
