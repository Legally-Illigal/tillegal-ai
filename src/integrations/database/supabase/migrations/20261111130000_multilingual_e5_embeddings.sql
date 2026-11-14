DROP INDEX IF EXISTS public.idx_dense_embeddings_vector;

ALTER TABLE public.dense_chunk_embeddings
    ALTER COLUMN embedding TYPE vector
    USING embedding::vector;

CREATE INDEX idx_dense_embeddings_vector_384
    ON public.dense_chunk_embeddings USING hnsw ((embedding::vector(384)) vector_cosine_ops)
    WHERE embedding IS NOT NULL AND vector_dims(embedding) = 384;

CREATE INDEX idx_dense_embeddings_vector_1536
    ON public.dense_chunk_embeddings USING hnsw ((embedding::vector(1536)) vector_cosine_ops)
    WHERE embedding IS NOT NULL AND vector_dims(embedding) = 1536;

DROP FUNCTION IF EXISTS public.search_legal_chunks(vector(1536), TEXT, INTEGER, DATE, TEXT[]);

CREATE OR REPLACE FUNCTION public.search_legal_chunks(
    p_query_embedding vector,
    p_dense_index_name TEXT,
    p_top_k INTEGER,
    p_as_of_date DATE,
    p_usage_policies TEXT[]
)
RETURNS TABLE (
    retrieval_chunk_id UUID,
    source_document_id UUID,
    document_structure_id UUID,
    dense_index_id UUID,
    chunk_key TEXT,
    content TEXT,
    similarity DOUBLE PRECISION,
    node_id TEXT,
    block_id TEXT,
    chunk_type TEXT,
    start_offset INTEGER,
    end_offset INTEGER,
    chunk_metadata JSONB,
    source_id TEXT,
    source_record_id TEXT,
    source_snapshot_id TEXT,
    title TEXT,
    language TEXT,
    source_url TEXT,
    issued_on DATE,
    effective_from DATE,
    effective_to DATE,
    effect_status_reported TEXT,
    usage_policy TEXT,
    source_metadata JSONB
)
LANGUAGE PLPGSQL
STABLE
SECURITY INVOKER
SET search_path = public, extensions
AS $$
BEGIN
    IF vector_dims(p_query_embedding) = 384 THEN
        RETURN QUERY
        SELECT
            chunk.id,
            document.id,
            chunk.document_structure_id,
            dense_index.id,
            chunk.chunk_key,
            chunk.content,
            1 - (embedding.embedding <=> p_query_embedding),
            chunk.node_id,
            chunk.block_id,
            chunk.chunk_type,
            chunk.start_offset,
            chunk.end_offset,
            chunk.metadata,
            document.source_id,
            document.source_record_id,
            document.source_snapshot_id,
            document.title,
            document.language,
            document.source_url,
            document.issued_on,
            document.effective_from,
            document.effective_to,
            document.effect_status_reported,
            document.usage_policy,
            document.raw_metadata
        FROM public.dense_chunk_embeddings AS embedding
        JOIN public.dense_indexes AS dense_index ON dense_index.id = embedding.dense_index_id
        JOIN public.retrieval_chunks AS chunk ON chunk.id = embedding.retrieval_chunk_id
        JOIN public.source_documents AS document ON document.id = chunk.source_document_id
        WHERE dense_index.index_name = p_dense_index_name
            AND dense_index.status = 'READY'
            AND dense_index.embedding_dimension = 384
            AND dense_index.distance_metric = 'cosine'
            AND embedding.status = 'INDEXED'
            AND vector_dims(embedding.embedding) = 384
            AND document.usage_policy = ANY(p_usage_policies)
            AND (document.effective_from IS NULL OR document.effective_from <= p_as_of_date)
            AND (document.effective_to IS NULL OR document.effective_to >= p_as_of_date)
        ORDER BY embedding.embedding::vector(384) <=> p_query_embedding, chunk.id
        LIMIT LEAST(GREATEST(p_top_k, 1), 50);
    ELSIF vector_dims(p_query_embedding) = 1536 THEN
        RETURN QUERY
        SELECT
            chunk.id,
            document.id,
            chunk.document_structure_id,
            dense_index.id,
            chunk.chunk_key,
            chunk.content,
            1 - (embedding.embedding <=> p_query_embedding),
            chunk.node_id,
            chunk.block_id,
            chunk.chunk_type,
            chunk.start_offset,
            chunk.end_offset,
            chunk.metadata,
            document.source_id,
            document.source_record_id,
            document.source_snapshot_id,
            document.title,
            document.language,
            document.source_url,
            document.issued_on,
            document.effective_from,
            document.effective_to,
            document.effect_status_reported,
            document.usage_policy,
            document.raw_metadata
        FROM public.dense_chunk_embeddings AS embedding
        JOIN public.dense_indexes AS dense_index ON dense_index.id = embedding.dense_index_id
        JOIN public.retrieval_chunks AS chunk ON chunk.id = embedding.retrieval_chunk_id
        JOIN public.source_documents AS document ON document.id = chunk.source_document_id
        WHERE dense_index.index_name = p_dense_index_name
            AND dense_index.status = 'READY'
            AND dense_index.embedding_dimension = 1536
            AND dense_index.distance_metric = 'cosine'
            AND embedding.status = 'INDEXED'
            AND vector_dims(embedding.embedding) = 1536
            AND document.usage_policy = ANY(p_usage_policies)
            AND (document.effective_from IS NULL OR document.effective_from <= p_as_of_date)
            AND (document.effective_to IS NULL OR document.effective_to >= p_as_of_date)
        ORDER BY embedding.embedding::vector(1536) <=> p_query_embedding, chunk.id
        LIMIT LEAST(GREATEST(p_top_k, 1), 50);
    ELSE
        RAISE EXCEPTION 'Unsupported query embedding dimension: %', vector_dims(p_query_embedding);
    END IF;
END;
$$;

CREATE OR REPLACE FUNCTION public.upsert_dense_embeddings(p_index_name TEXT, p_embeddings JSONB)
RETURNS INTEGER
LANGUAGE PLPGSQL
SECURITY INVOKER
SET search_path = public, extensions
AS $$
DECLARE
    v_index public.dense_indexes%ROWTYPE;
    v_count INTEGER;
BEGIN
    SELECT * INTO STRICT v_index
    FROM public.dense_indexes
    WHERE index_name = p_index_name;

    IF EXISTS (
        SELECT 1
        FROM jsonb_array_elements(COALESCE(p_embeddings, '[]'::JSONB)) AS embedding_row
        WHERE COALESCE(jsonb_typeof(embedding_row->'embedding') <> 'array', TRUE)
            OR vector_dims((embedding_row->'embedding')::TEXT::VECTOR)
                IS DISTINCT FROM v_index.embedding_dimension
    ) THEN
        RAISE EXCEPTION 'Embedding dimension does not match dense index %', p_index_name;
    END IF;

    INSERT INTO public.dense_chunk_embeddings (
        dense_index_id, retrieval_chunk_id, embedding, embedded_text_sha256,
        status, embedded_at, error_message, metadata
    )
    SELECT
        v_index.id,
        (embedding_row->>'retrieval_chunk_id')::UUID,
        (embedding_row->'embedding')::TEXT::VECTOR,
        embedding_row->>'embedded_text_sha256',
        COALESCE(embedding_row->>'status', 'INDEXED'),
        CASE WHEN COALESCE(embedding_row->>'status', 'INDEXED') = 'INDEXED' THEN now() END,
        NULL,
        COALESCE(embedding_row->'metadata', '{}'::JSONB)
    FROM jsonb_array_elements(COALESCE(p_embeddings, '[]'::JSONB)) AS embedding_row
    ON CONFLICT (dense_index_id, retrieval_chunk_id) DO UPDATE SET
        embedding = EXCLUDED.embedding,
        embedded_text_sha256 = EXCLUDED.embedded_text_sha256,
        status = EXCLUDED.status,
        embedded_at = EXCLUDED.embedded_at,
        error_message = EXCLUDED.error_message,
        metadata = EXCLUDED.metadata,
        updated_at = now();

    GET DIAGNOSTICS v_count = ROW_COUNT;
    IF v_count > 0 THEN
        UPDATE public.dense_indexes
        SET status = 'STALE', updated_at = now()
        WHERE id = v_index.id AND status = 'READY';
    END IF;
    RETURN v_count;
END;
$$;

CREATE OR REPLACE FUNCTION public.refresh_dense_index_status(p_index_name TEXT)
RETURNS TEXT
LANGUAGE PLPGSQL
SECURITY INVOKER
SET search_path = public, extensions
AS $$
DECLARE
    v_index_id UUID;
    v_status TEXT;
BEGIN
    SELECT id INTO STRICT v_index_id
    FROM public.dense_indexes
    WHERE index_name = p_index_name;

    UPDATE public.dense_indexes AS dense_index
    SET
        status = CASE WHEN EXISTS (
            SELECT 1
            FROM public.retrieval_chunks AS chunk
            LEFT JOIN public.dense_chunk_embeddings AS embedding
                ON embedding.dense_index_id = dense_index.id
                AND embedding.retrieval_chunk_id = chunk.id
            WHERE embedding.id IS NULL
                OR embedding.embedding IS NULL
                OR embedding.status <> 'INDEXED'
                OR vector_dims(embedding.embedding) <> dense_index.embedding_dimension
        ) THEN 'STALE' ELSE 'READY' END,
        updated_at = now()
    WHERE dense_index.id = v_index_id
    RETURNING dense_index.status INTO v_status;

    RETURN v_status;
END;
$$;

REVOKE ALL ON FUNCTION public.search_legal_chunks(vector, TEXT, INTEGER, DATE, TEXT[]) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.search_legal_chunks(vector, TEXT, INTEGER, DATE, TEXT[]) TO service_role;
REVOKE ALL ON FUNCTION public.refresh_dense_index_status(TEXT) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.refresh_dense_index_status(TEXT) TO service_role;
