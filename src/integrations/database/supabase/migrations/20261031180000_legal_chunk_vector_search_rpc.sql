CREATE OR REPLACE FUNCTION public.search_legal_chunks(
    p_query_embedding vector(1536),
    p_dense_index_name TEXT,
    p_top_k INTEGER,
    p_as_of_date DATE,
    p_legal_approvals TEXT[],
    p_usage_policies TEXT[],
    p_provenance_statuses TEXT[],
    p_temporal_statuses TEXT[],
    p_rights_statuses TEXT[]
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
    document_number TEXT,
    title TEXT,
    document_type TEXT,
    issuing_authority TEXT,
    language TEXT,
    source_url TEXT,
    issued_on DATE,
    effective_from DATE,
    effective_to DATE,
    effect_status_reported TEXT,
    usage_policy TEXT,
    legal_approval TEXT,
    provenance_status TEXT,
    temporal_status TEXT,
    rights_status TEXT,
    source_metadata JSONB
)
LANGUAGE SQL
STABLE
SECURITY INVOKER
SET search_path = public, extensions
AS $$
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
        document.document_number,
        document.title,
        document.document_type,
        document.issuing_authority,
        document.language,
        document.source_url,
        document.issued_on,
        document.effective_from,
        document.effective_to,
        document.effect_status_reported,
        document.usage_policy,
        document.legal_approval,
        document.provenance_status,
        document.temporal_status,
        document.rights_status,
        document.raw_metadata
    FROM public.dense_chunk_embeddings AS embedding
    JOIN public.dense_indexes AS dense_index
        ON dense_index.id = embedding.dense_index_id
    JOIN public.retrieval_chunks AS chunk
        ON chunk.id = embedding.retrieval_chunk_id
    JOIN public.source_documents AS document
        ON document.id = chunk.source_document_id
    WHERE dense_index.index_name = p_dense_index_name
        AND dense_index.status = 'READY'
        AND dense_index.embedding_dimension = 1536
        AND dense_index.distance_metric = 'cosine'
        AND embedding.status = 'INDEXED'
        AND document.legal_approval = ANY(p_legal_approvals)
        AND document.usage_policy = ANY(p_usage_policies)
        AND document.provenance_status = ANY(p_provenance_statuses)
        AND document.temporal_status = ANY(p_temporal_statuses)
        AND document.rights_status = ANY(p_rights_statuses)
        AND (document.effective_from IS NULL OR document.effective_from <= p_as_of_date)
        AND (document.effective_to IS NULL OR document.effective_to >= p_as_of_date)
    ORDER BY embedding.embedding <=> p_query_embedding, chunk.id
    LIMIT LEAST(GREATEST(p_top_k, 1), 50);
$$;

REVOKE ALL ON FUNCTION public.search_legal_chunks(
    vector, TEXT, INTEGER, DATE, TEXT[], TEXT[], TEXT[], TEXT[], TEXT[]
) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.search_legal_chunks(
    vector, TEXT, INTEGER, DATE, TEXT[], TEXT[], TEXT[], TEXT[], TEXT[]
) FROM anon, authenticated;
GRANT EXECUTE ON FUNCTION public.search_legal_chunks(
    vector, TEXT, INTEGER, DATE, TEXT[], TEXT[], TEXT[], TEXT[], TEXT[]
) TO service_role;
