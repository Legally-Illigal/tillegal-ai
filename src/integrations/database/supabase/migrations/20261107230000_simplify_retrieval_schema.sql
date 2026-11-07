DROP FUNCTION IF EXISTS public.search_legal_chunks(
    vector(1536), TEXT, INTEGER, DATE, TEXT[], TEXT[], TEXT[], TEXT[], TEXT[]
);

DROP FUNCTION IF EXISTS public.search_sparse_legal_chunks(
    TEXT[], TEXT, INTEGER, DATE, TEXT[], TEXT[], TEXT[], TEXT[], TEXT[]
);

ALTER TABLE public.source_documents
    DROP COLUMN IF EXISTS status_observed_at,
    DROP COLUMN IF EXISTS legal_approval,
    DROP COLUMN IF EXISTS provenance_status,
    DROP COLUMN IF EXISTS temporal_status,
    DROP COLUMN IF EXISTS rights_status;

ALTER TABLE public.document_structures
    DROP COLUMN IF EXISTS excluded_segments;

CREATE TABLE IF NOT EXISTS public.crawl_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id TEXT NOT NULL,
    crawl_date DATE NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING', 'RUNNING', 'SUCCEEDED', 'FAILED', 'CANCELLED')),
    result JSONB NOT NULL DEFAULT '{}'::JSONB,
    error_message TEXT,
    owner TEXT,
    lease_until TIMESTAMPTZ,
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE OR REPLACE FUNCTION public.upsert_source_document(p_document JSONB)
RETURNS JSONB
LANGUAGE PLPGSQL
SECURITY INVOKER
SET search_path = public, extensions
AS $$
DECLARE
    v_document public.source_documents%ROWTYPE;
    v_saved public.source_documents%ROWTYPE;
BEGIN
    v_document := jsonb_populate_record(NULL::public.source_documents, p_document);

    INSERT INTO public.source_documents (
        source_id,
        source_record_id,
        source_snapshot_id,
        title,
        language,
        source_url,
        issued_on,
        effective_from,
        effective_to,
        effect_status_reported,
        raw_content_ref,
        raw_content_sha256,
        raw_metadata,
        usage_policy,
        collected_at
    )
    VALUES (
        v_document.source_id,
        v_document.source_record_id,
        v_document.source_snapshot_id,
        v_document.title,
        v_document.language,
        v_document.source_url,
        v_document.issued_on,
        v_document.effective_from,
        v_document.effective_to,
        v_document.effect_status_reported,
        v_document.raw_content_ref,
        v_document.raw_content_sha256,
        COALESCE(v_document.raw_metadata, '{}'::JSONB),
        COALESCE(v_document.usage_policy, 'EXPERIMENTAL_ONLY'),
        v_document.collected_at
    )
    ON CONFLICT (source_id, source_record_id) DO UPDATE SET
        source_snapshot_id = EXCLUDED.source_snapshot_id,
        title = EXCLUDED.title,
        language = EXCLUDED.language,
        source_url = EXCLUDED.source_url,
        issued_on = EXCLUDED.issued_on,
        effective_from = EXCLUDED.effective_from,
        effective_to = EXCLUDED.effective_to,
        effect_status_reported = EXCLUDED.effect_status_reported,
        raw_content_ref = EXCLUDED.raw_content_ref,
        raw_content_sha256 = EXCLUDED.raw_content_sha256,
        raw_metadata = EXCLUDED.raw_metadata,
        usage_policy = EXCLUDED.usage_policy,
        collected_at = EXCLUDED.collected_at,
        updated_at = now()
    RETURNING * INTO v_saved;

    RETURN to_jsonb(v_saved);
END;
$$;

CREATE OR REPLACE FUNCTION public.save_parsed_document(
    p_structure JSONB,
    p_nodes JSONB,
    p_blocks JSONB,
    p_chunks JSONB
)
RETURNS UUID
LANGUAGE PLPGSQL
SECURITY INVOKER
SET search_path = public, extensions
AS $$
DECLARE
    v_structure public.document_structures%ROWTYPE;
    v_structure_id UUID;
    v_affected_dense_indexes UUID[];
    v_affected_sparse_indexes UUID[];
BEGIN
    v_structure := jsonb_populate_record(NULL::public.document_structures, p_structure);

    INSERT INTO public.document_structures (
        source_document_id,
        schema_version,
        parser_version,
        content_sha256,
        max_chars,
        issues,
        parsed_at
    )
    VALUES (
        v_structure.source_document_id,
        v_structure.schema_version,
        v_structure.parser_version,
        v_structure.content_sha256,
        v_structure.max_chars,
        COALESCE(v_structure.issues, '[]'::JSONB),
        COALESCE(v_structure.parsed_at, now())
    )
    ON CONFLICT (source_document_id) DO UPDATE SET
        schema_version = EXCLUDED.schema_version,
        parser_version = EXCLUDED.parser_version,
        content_sha256 = EXCLUDED.content_sha256,
        max_chars = EXCLUDED.max_chars,
        issues = EXCLUDED.issues,
        parsed_at = EXCLUDED.parsed_at
    RETURNING id INTO v_structure_id;

    SELECT array_agg(DISTINCT embedding.dense_index_id)
    INTO v_affected_dense_indexes
    FROM public.dense_chunk_embeddings AS embedding
    JOIN public.retrieval_chunks AS chunk ON chunk.id = embedding.retrieval_chunk_id
    WHERE chunk.document_structure_id = v_structure_id;

    SELECT array_agg(DISTINCT sparse_document.sparse_index_id)
    INTO v_affected_sparse_indexes
    FROM public.sparse_chunk_documents AS sparse_document
    JOIN public.retrieval_chunks AS chunk
        ON chunk.id = sparse_document.retrieval_chunk_id
    WHERE chunk.document_structure_id = v_structure_id;

    DELETE FROM public.retrieval_chunks WHERE document_structure_id = v_structure_id;
    DELETE FROM public.document_blocks WHERE document_structure_id = v_structure_id;
    DELETE FROM public.document_nodes WHERE document_structure_id = v_structure_id;

    INSERT INTO public.document_nodes (
        document_structure_id,
        node_id,
        parent_node_id,
        kind,
        label,
        scope,
        heading_block_id,
        ordinal,
        metadata
    )
    SELECT
        v_structure_id,
        node.node_id,
        node.parent_node_id,
        node.kind,
        node.label,
        node.scope,
        node.heading_block_id,
        node.ordinal,
        COALESCE(node.metadata, '{}'::JSONB)
    FROM jsonb_populate_recordset(NULL::public.document_nodes, COALESCE(p_nodes, '[]'::JSONB)) AS node;

    INSERT INTO public.document_blocks (
        document_structure_id,
        block_id,
        node_id,
        block_type,
        content,
        ordinal,
        start_offset,
        end_offset,
        metadata
    )
    SELECT
        v_structure_id,
        block.block_id,
        block.node_id,
        COALESCE(block.block_type, 'paragraph'),
        block.content,
        COALESCE(block.ordinal, 0),
        block.start_offset,
        block.end_offset,
        COALESCE(block.metadata, '{}'::JSONB)
    FROM jsonb_populate_recordset(NULL::public.document_blocks, COALESCE(p_blocks, '[]'::JSONB)) AS block;

    INSERT INTO public.retrieval_chunks (
        source_document_id,
        document_structure_id,
        chunk_key,
        content,
        content_sha256,
        node_id,
        block_id,
        chunk_type,
        ordinal,
        start_offset,
        end_offset,
        metadata
    )
    SELECT
        v_structure.source_document_id,
        v_structure_id,
        chunk.chunk_key,
        chunk.content,
        chunk.content_sha256,
        chunk.node_id,
        chunk.block_id,
        COALESCE(chunk.chunk_type, 'text'),
        COALESCE(chunk.ordinal, 0),
        chunk.start_offset,
        chunk.end_offset,
        COALESCE(chunk.metadata, '{}'::JSONB)
    FROM jsonb_populate_recordset(NULL::public.retrieval_chunks, COALESCE(p_chunks, '[]'::JSONB)) AS chunk;

    IF v_affected_dense_indexes IS NOT NULL THEN
        PERFORM public.mark_affected_dense_indexes_stale(v_affected_dense_indexes);
    END IF;

    IF v_affected_sparse_indexes IS NOT NULL THEN
        PERFORM public.mark_affected_sparse_indexes_stale(v_affected_sparse_indexes);
    END IF;

    RETURN v_structure_id;
END;
$$;

CREATE OR REPLACE FUNCTION public.search_legal_chunks(
    p_query_embedding vector(1536),
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
        AND document.usage_policy = ANY(p_usage_policies)
        AND (document.effective_from IS NULL OR document.effective_from <= p_as_of_date)
        AND (document.effective_to IS NULL OR document.effective_to >= p_as_of_date)
    ORDER BY embedding.embedding <=> p_query_embedding, chunk.id
    LIMIT LEAST(GREATEST(p_top_k, 1), 50);
$$;

CREATE OR REPLACE FUNCTION public.search_sparse_legal_chunks(
    p_terms TEXT[],
    p_sparse_index_name TEXT,
    p_top_k INTEGER,
    p_as_of_date DATE,
    p_usage_policies TEXT[]
)
RETURNS TABLE (retrieval_chunk_id UUID, score DOUBLE PRECISION)
LANGUAGE SQL
STABLE
SECURITY INVOKER
SET search_path = public, extensions
AS $$
    WITH selected_index AS (
        SELECT sparse_index.*
        FROM public.sparse_indexes AS sparse_index
        WHERE sparse_index.index_name = p_sparse_index_name
            AND sparse_index.status = 'READY'
            AND sparse_index.document_count > 0
    ),
    query_terms AS (
        SELECT DISTINCT lower(query_term.value) AS term
        FROM unnest(p_terms) AS query_term(value)
        WHERE length(trim(query_term.value)) > 0
    ),
    term_frequencies AS (
        SELECT
            posting.sparse_chunk_document_id,
            posting.term,
            sum(posting.term_frequency)::DOUBLE PRECISION AS term_frequency
        FROM public.sparse_postings AS posting
        JOIN selected_index ON selected_index.id = posting.sparse_index_id
        JOIN query_terms ON query_terms.term = lower(posting.term)
        GROUP BY posting.sparse_chunk_document_id, posting.term
    ),
    term_document_frequencies AS (
        SELECT
            posting.term,
            count(DISTINCT posting.sparse_chunk_document_id)::DOUBLE PRECISION AS document_frequency
        FROM public.sparse_postings AS posting
        JOIN selected_index ON selected_index.id = posting.sparse_index_id
        JOIN query_terms ON query_terms.term = lower(posting.term)
        GROUP BY posting.term
    ),
    eligible_chunks AS (
        SELECT sparse_document.id, sparse_document.retrieval_chunk_id, sparse_document.token_count
        FROM public.sparse_chunk_documents AS sparse_document
        JOIN selected_index ON selected_index.id = sparse_document.sparse_index_id
        JOIN public.retrieval_chunks AS chunk
            ON chunk.id = sparse_document.retrieval_chunk_id
        JOIN public.source_documents AS document
            ON document.id = chunk.source_document_id
        WHERE sparse_document.status = 'INDEXED'
            AND document.usage_policy = ANY(p_usage_policies)
            AND (document.effective_from IS NULL OR document.effective_from <= p_as_of_date)
            AND (document.effective_to IS NULL OR document.effective_to >= p_as_of_date)
    )
    SELECT
        eligible.retrieval_chunk_id,
        sum(
            ln(
                1 + (
                    selected_index.document_count - term_df.document_frequency + 0.5
                ) / (term_df.document_frequency + 0.5)
            )
            * (
                term_frequency.term_frequency * (selected_index.k1 + 1)
                / (
                    term_frequency.term_frequency
                    + selected_index.k1 * (
                        1 - selected_index.b
                        + selected_index.b * eligible.token_count
                        / GREATEST(selected_index.average_document_length, 1)
                    )
                )
            )
        )::DOUBLE PRECISION AS score
    FROM term_frequencies AS term_frequency
    JOIN eligible_chunks AS eligible
        ON eligible.id = term_frequency.sparse_chunk_document_id
    JOIN term_document_frequencies AS term_df
        ON term_df.term = term_frequency.term
    CROSS JOIN selected_index
    GROUP BY eligible.retrieval_chunk_id
    ORDER BY score DESC, eligible.retrieval_chunk_id
    LIMIT LEAST(GREATEST(p_top_k, 1), 50);
$$;

REVOKE ALL ON FUNCTION public.search_legal_chunks(
    vector, TEXT, INTEGER, DATE, TEXT[]
) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.search_legal_chunks(
    vector, TEXT, INTEGER, DATE, TEXT[]
) TO service_role;

REVOKE ALL ON FUNCTION public.search_sparse_legal_chunks(
    TEXT[], TEXT, INTEGER, DATE, TEXT[]
) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.search_sparse_legal_chunks(
    TEXT[], TEXT, INTEGER, DATE, TEXT[]
) TO service_role;
