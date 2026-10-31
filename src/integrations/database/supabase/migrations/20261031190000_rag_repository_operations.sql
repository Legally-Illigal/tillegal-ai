ALTER TABLE public.dense_chunk_embeddings
    ALTER COLUMN embedding DROP NOT NULL;

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
        document_number,
        title,
        document_type,
        issuing_authority,
        language,
        source_url,
        raw_content_format,
        raw_content,
        issued_on,
        effective_from,
        effective_to,
        effect_status_reported,
        status_observed_at,
        raw_file_ref,
        raw_content_ref,
        raw_file_sha256,
        raw_content_sha256,
        raw_metadata,
        usage_policy,
        legal_approval,
        provenance_status,
        temporal_status,
        rights_status,
        collected_at
    )
    VALUES (
        v_document.source_id,
        v_document.source_record_id,
        v_document.source_snapshot_id,
        v_document.document_number,
        v_document.title,
        v_document.document_type,
        v_document.issuing_authority,
        v_document.language,
        v_document.source_url,
        v_document.raw_content_format,
        v_document.raw_content,
        v_document.issued_on,
        v_document.effective_from,
        v_document.effective_to,
        v_document.effect_status_reported,
        v_document.status_observed_at,
        v_document.raw_file_ref,
        v_document.raw_content_ref,
        v_document.raw_file_sha256,
        v_document.raw_content_sha256,
        COALESCE(v_document.raw_metadata, '{}'::JSONB),
        COALESCE(v_document.usage_policy, 'EXPERIMENTAL_ONLY'),
        COALESCE(v_document.legal_approval, 'QUARANTINE'),
        COALESCE(v_document.provenance_status, 'UNVERIFIED'),
        COALESCE(v_document.temporal_status, 'UNKNOWN'),
        COALESCE(v_document.rights_status, 'UNVERIFIED'),
        v_document.collected_at
    )
    ON CONFLICT (source_id, source_record_id) DO UPDATE SET
        source_snapshot_id = EXCLUDED.source_snapshot_id,
        document_number = EXCLUDED.document_number,
        title = EXCLUDED.title,
        document_type = EXCLUDED.document_type,
        issuing_authority = EXCLUDED.issuing_authority,
        language = EXCLUDED.language,
        source_url = EXCLUDED.source_url,
        raw_content_format = EXCLUDED.raw_content_format,
        raw_content = EXCLUDED.raw_content,
        issued_on = EXCLUDED.issued_on,
        effective_from = EXCLUDED.effective_from,
        effective_to = EXCLUDED.effective_to,
        effect_status_reported = EXCLUDED.effect_status_reported,
        status_observed_at = EXCLUDED.status_observed_at,
        raw_file_ref = EXCLUDED.raw_file_ref,
        raw_content_ref = EXCLUDED.raw_content_ref,
        raw_file_sha256 = EXCLUDED.raw_file_sha256,
        raw_content_sha256 = EXCLUDED.raw_content_sha256,
        raw_metadata = EXCLUDED.raw_metadata,
        usage_policy = EXCLUDED.usage_policy,
        legal_approval = EXCLUDED.legal_approval,
        provenance_status = EXCLUDED.provenance_status,
        temporal_status = EXCLUDED.temporal_status,
        rights_status = EXCLUDED.rights_status,
        collected_at = EXCLUDED.collected_at,
        updated_at = now()
    RETURNING * INTO v_saved;

    RETURN to_jsonb(v_saved);
END;
$$;

CREATE OR REPLACE FUNCTION public.get_source_document(p_source_document_id UUID)
RETURNS JSONB
LANGUAGE SQL
STABLE
SECURITY INVOKER
SET search_path = public, extensions
AS $$
    SELECT to_jsonb(document)
    FROM public.source_documents AS document
    WHERE document.id = p_source_document_id;
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
        excluded_segments,
        issues,
        parsed_at
    )
    VALUES (
        v_structure.source_document_id,
        v_structure.schema_version,
        v_structure.parser_version,
        v_structure.content_sha256,
        v_structure.max_chars,
        COALESCE(v_structure.excluded_segments, '[]'::JSONB),
        COALESCE(v_structure.issues, '[]'::JSONB),
        COALESCE(v_structure.parsed_at, now())
    )
    ON CONFLICT (source_document_id) DO UPDATE SET
        schema_version = EXCLUDED.schema_version,
        parser_version = EXCLUDED.parser_version,
        content_sha256 = EXCLUDED.content_sha256,
        max_chars = EXCLUDED.max_chars,
        excluded_segments = EXCLUDED.excluded_segments,
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

    UPDATE public.dense_indexes
    SET status = 'STALE', updated_at = now()
    WHERE status = 'READY'
        OR id = ANY(COALESCE(v_affected_dense_indexes, ARRAY[]::UUID[]));

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
        WHERE sparse_index_id = ANY(COALESCE(v_affected_sparse_indexes, ARRAY[]::UUID[]))
        GROUP BY sparse_index_id
    ) AS stats
    WHERE sparse_index.id = stats.sparse_index_id;

    UPDATE public.sparse_indexes
    SET status = 'STALE', updated_at = now()
    WHERE status = 'READY'
        OR id = ANY(COALESCE(v_affected_sparse_indexes, ARRAY[]::UUID[]));

    UPDATE public.sparse_indexes
    SET document_count = 0, total_token_count = 0, average_document_length = 0
    WHERE id = ANY(COALESCE(v_affected_sparse_indexes, ARRAY[]::UUID[]))
        AND NOT EXISTS (
            SELECT 1
            FROM public.sparse_chunk_documents AS sparse_document
            WHERE sparse_document.sparse_index_id = sparse_indexes.id
                AND sparse_document.status = 'INDEXED'
        );

    RETURN v_structure_id;
END;
$$;

CREATE OR REPLACE FUNCTION public.get_retrieval_chunks(p_chunk_ids UUID[])
RETURNS SETOF JSONB
LANGUAGE SQL
STABLE
SECURITY INVOKER
SET search_path = public, extensions
AS $$
    SELECT to_jsonb(chunk)
    FROM public.retrieval_chunks AS chunk
    WHERE chunk.id = ANY(p_chunk_ids)
    ORDER BY chunk.source_document_id, chunk.ordinal, chunk.id;
$$;

CREATE OR REPLACE FUNCTION public.list_retrieval_chunks_for_document(p_source_document_id UUID)
RETURNS SETOF JSONB
LANGUAGE SQL
STABLE
SECURITY INVOKER
SET search_path = public, extensions
AS $$
    SELECT to_jsonb(chunk)
    FROM public.retrieval_chunks AS chunk
    WHERE chunk.source_document_id = p_source_document_id
    ORDER BY chunk.ordinal, chunk.id;
$$;

CREATE OR REPLACE FUNCTION public.upsert_dense_index(p_index JSONB)
RETURNS JSONB
LANGUAGE PLPGSQL
SECURITY INVOKER
SET search_path = public, extensions
AS $$
DECLARE
    v_index public.dense_indexes%ROWTYPE;
    v_saved public.dense_indexes%ROWTYPE;
BEGIN
    v_index := jsonb_populate_record(NULL::public.dense_indexes, p_index);

    INSERT INTO public.dense_indexes (
        index_name, provider, model_name, embedding_dimension, distance_metric,
        index_version, status, metadata
    )
    VALUES (
        v_index.index_name, v_index.provider, v_index.model_name,
        COALESCE(v_index.embedding_dimension, 1536),
        COALESCE(v_index.distance_metric, 'cosine'),
        COALESCE(v_index.index_version, 'v1'),
        COALESCE(v_index.status, 'BUILDING'),
        COALESCE(v_index.metadata, '{}'::JSONB)
    )
    ON CONFLICT (index_name) DO UPDATE SET
        provider = EXCLUDED.provider,
        model_name = EXCLUDED.model_name,
        embedding_dimension = EXCLUDED.embedding_dimension,
        distance_metric = EXCLUDED.distance_metric,
        index_version = EXCLUDED.index_version,
        status = EXCLUDED.status,
        metadata = EXCLUDED.metadata,
        updated_at = now()
    RETURNING * INTO v_saved;

    RETURN to_jsonb(v_saved);
END;
$$;

CREATE OR REPLACE FUNCTION public.get_dense_index(p_index_name TEXT)
RETURNS JSONB
LANGUAGE SQL
STABLE
SECURITY INVOKER
SET search_path = public, extensions
AS $$
    SELECT to_jsonb(index_row)
    FROM public.dense_indexes AS index_row
    WHERE index_row.index_name = p_index_name;
$$;

CREATE OR REPLACE FUNCTION public.upsert_dense_embeddings(p_index_name TEXT, p_embeddings JSONB)
RETURNS INTEGER
LANGUAGE PLPGSQL
SECURITY INVOKER
SET search_path = public, extensions
AS $$
DECLARE
    v_index_id UUID;
    v_count INTEGER;
BEGIN
    SELECT id INTO STRICT v_index_id
    FROM public.dense_indexes
    WHERE index_name = p_index_name;

    INSERT INTO public.dense_chunk_embeddings (
        dense_index_id, retrieval_chunk_id, embedding, embedded_text_sha256,
        status, embedded_at, error_message, metadata
    )
    SELECT
        v_index_id,
        (embedding_row->>'retrieval_chunk_id')::UUID,
        (embedding_row->'embedding')::TEXT::VECTOR(1536),
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
        WHERE id = v_index_id AND status = 'READY';
    END IF;
    RETURN v_count;
END;
$$;

CREATE OR REPLACE FUNCTION public.upsert_dense_embedding_statuses(
    p_index_name TEXT,
    p_statuses JSONB
)
RETURNS INTEGER
LANGUAGE PLPGSQL
SECURITY INVOKER
SET search_path = public, extensions
AS $$
DECLARE
    v_index_id UUID;
    v_count INTEGER;
BEGIN
    SELECT id INTO STRICT v_index_id
    FROM public.dense_indexes
    WHERE index_name = p_index_name;

    INSERT INTO public.dense_chunk_embeddings (
        dense_index_id, retrieval_chunk_id, embedding, embedded_text_sha256,
        status, embedded_at, error_message, metadata
    )
    SELECT
        v_index_id,
        (status_row->>'retrieval_chunk_id')::UUID,
        NULL,
        status_row->>'embedded_text_sha256',
        status_row->>'status',
        NULL,
        status_row->>'error_message',
        COALESCE(status_row->'metadata', '{}'::JSONB)
    FROM jsonb_array_elements(COALESCE(p_statuses, '[]'::JSONB)) AS status_row
    ON CONFLICT (dense_index_id, retrieval_chunk_id) DO UPDATE SET
        embedding = NULL,
        embedded_text_sha256 = EXCLUDED.embedded_text_sha256,
        status = EXCLUDED.status,
        embedded_at = NULL,
        error_message = EXCLUDED.error_message,
        metadata = EXCLUDED.metadata,
        updated_at = now();

    GET DIAGNOSTICS v_count = ROW_COUNT;
    IF v_count > 0 THEN
        UPDATE public.dense_indexes
        SET status = 'STALE', updated_at = now()
        WHERE id = v_index_id AND status = 'READY';
    END IF;
    RETURN v_count;
END;
$$;

CREATE OR REPLACE FUNCTION public.list_dense_embedding_work(
    p_index_name TEXT,
    p_statuses TEXT[],
    p_limit INTEGER
)
RETURNS SETOF JSONB
LANGUAGE SQL
STABLE
SECURITY INVOKER
SET search_path = public, extensions
AS $$
    SELECT to_jsonb(chunk) || jsonb_build_object(
        'embedding_status', COALESCE(embedding.status, 'PENDING'),
        'embedded_text_sha256', embedding.embedded_text_sha256,
        'error_message', embedding.error_message
    )
    FROM public.dense_indexes AS dense_index
    JOIN public.retrieval_chunks AS chunk ON true
    LEFT JOIN public.dense_chunk_embeddings AS embedding
        ON embedding.dense_index_id = dense_index.id
        AND embedding.retrieval_chunk_id = chunk.id
    WHERE dense_index.index_name = p_index_name
        AND COALESCE(embedding.status, 'PENDING') = ANY(p_statuses)
    ORDER BY chunk.created_at, chunk.id
    LIMIT LEAST(GREATEST(p_limit, 1), 500);
$$;

CREATE OR REPLACE FUNCTION public.upsert_sparse_index(p_index JSONB)
RETURNS JSONB
LANGUAGE PLPGSQL
SECURITY INVOKER
SET search_path = public, extensions
AS $$
DECLARE
    v_index public.sparse_indexes%ROWTYPE;
    v_saved public.sparse_indexes%ROWTYPE;
BEGIN
    v_index := jsonb_populate_record(NULL::public.sparse_indexes, p_index);

    INSERT INTO public.sparse_indexes (
        index_name, algorithm, tokenizer, language_config, k1, b,
        index_version, status, metadata
    )
    VALUES (
        v_index.index_name, COALESCE(v_index.algorithm, 'BM25'),
        COALESCE(v_index.tokenizer, 'unicode'),
        COALESCE(v_index.language_config, 'simple'),
        COALESCE(v_index.k1, 1.2), COALESCE(v_index.b, 0.75),
        COALESCE(v_index.index_version, 'v1'),
        COALESCE(v_index.status, 'BUILDING'),
        COALESCE(v_index.metadata, '{}'::JSONB)
    )
    ON CONFLICT (index_name) DO UPDATE SET
        algorithm = EXCLUDED.algorithm,
        tokenizer = EXCLUDED.tokenizer,
        language_config = EXCLUDED.language_config,
        k1 = EXCLUDED.k1,
        b = EXCLUDED.b,
        index_version = EXCLUDED.index_version,
        status = EXCLUDED.status,
        metadata = EXCLUDED.metadata,
        updated_at = now()
    RETURNING * INTO v_saved;

    RETURN to_jsonb(v_saved);
END;
$$;

CREATE OR REPLACE FUNCTION public.get_sparse_index(p_index_name TEXT)
RETURNS JSONB
LANGUAGE SQL
STABLE
SECURITY INVOKER
SET search_path = public, extensions
AS $$
    SELECT to_jsonb(index_row)
    FROM public.sparse_indexes AS index_row
    WHERE index_row.index_name = p_index_name;
$$;

CREATE OR REPLACE FUNCTION public.list_sparse_index_work(
    p_index_name TEXT,
    p_statuses TEXT[],
    p_limit INTEGER
)
RETURNS SETOF JSONB
LANGUAGE SQL
STABLE
SECURITY INVOKER
SET search_path = public, extensions
AS $$
    SELECT to_jsonb(chunk) || jsonb_build_object(
        'sparse_status', COALESCE(sparse_document.status, 'PENDING'),
        'token_count', sparse_document.token_count,
        'indexed_text_sha256', sparse_document.indexed_text_sha256
    )
    FROM public.sparse_indexes AS sparse_index
    JOIN public.retrieval_chunks AS chunk ON true
    LEFT JOIN public.sparse_chunk_documents AS sparse_document
        ON sparse_document.sparse_index_id = sparse_index.id
        AND sparse_document.retrieval_chunk_id = chunk.id
    WHERE sparse_index.index_name = p_index_name
        AND COALESCE(sparse_document.status, 'PENDING') = ANY(p_statuses)
    ORDER BY chunk.created_at, chunk.id
    LIMIT LEAST(GREATEST(p_limit, 1), 500);
$$;

CREATE OR REPLACE FUNCTION public.upsert_sparse_chunk_documents(p_index_name TEXT, p_chunks JSONB)
RETURNS INTEGER
LANGUAGE PLPGSQL
SECURITY INVOKER
SET search_path = public, extensions
AS $$
DECLARE
    v_index_id UUID;
    v_chunk JSONB;
    v_sparse_chunk_document_id UUID;
    v_count INTEGER := 0;
BEGIN
    SELECT id INTO STRICT v_index_id
    FROM public.sparse_indexes
    WHERE index_name = p_index_name;

    FOR v_chunk IN
        SELECT chunk_row.value
        FROM jsonb_array_elements(COALESCE(p_chunks, '[]'::JSONB)) AS chunk_row(value)
    LOOP
        INSERT INTO public.sparse_chunk_documents (
            sparse_index_id, retrieval_chunk_id, token_count,
            indexed_text_sha256, status, indexed_at, error_message, metadata
        )
        VALUES (
            v_index_id,
            (v_chunk->>'retrieval_chunk_id')::UUID,
            (v_chunk->>'token_count')::INTEGER,
            v_chunk->>'indexed_text_sha256',
            COALESCE(v_chunk->>'status', 'INDEXED'),
            CASE WHEN COALESCE(v_chunk->>'status', 'INDEXED') = 'INDEXED' THEN now() END,
            NULL,
            COALESCE(v_chunk->'metadata', '{}'::JSONB)
        )
        ON CONFLICT (sparse_index_id, retrieval_chunk_id) DO UPDATE SET
            token_count = EXCLUDED.token_count,
            indexed_text_sha256 = EXCLUDED.indexed_text_sha256,
            status = EXCLUDED.status,
            indexed_at = EXCLUDED.indexed_at,
            error_message = EXCLUDED.error_message,
            metadata = EXCLUDED.metadata,
            updated_at = now()
        RETURNING id INTO v_sparse_chunk_document_id;

        DELETE FROM public.sparse_postings
        WHERE sparse_chunk_document_id = v_sparse_chunk_document_id;

        IF COALESCE(v_chunk->>'status', 'INDEXED') = 'INDEXED' THEN
            INSERT INTO public.sparse_postings (
                sparse_index_id, sparse_chunk_document_id, term, term_frequency, positions
            )
            SELECT
                v_index_id,
                v_sparse_chunk_document_id,
                posting.term,
                posting.term_frequency,
                posting.positions
            FROM jsonb_to_recordset(COALESCE(v_chunk->'postings', '[]'::JSONB))
                AS posting(term TEXT, term_frequency INTEGER, positions INTEGER[]);
        END IF;

        v_count := v_count + 1;
    END LOOP;

    UPDATE public.sparse_indexes AS index_row
    SET
        document_count = stats.document_count,
        total_token_count = stats.total_token_count,
        average_document_length = CASE
            WHEN stats.document_count = 0 THEN 0
            ELSE stats.total_token_count::DOUBLE PRECISION / stats.document_count
        END,
        updated_at = now()
    FROM (
        SELECT
            count(*) FILTER (WHERE status = 'INDEXED') AS document_count,
            COALESCE(sum(token_count) FILTER (WHERE status = 'INDEXED'), 0) AS total_token_count
        FROM public.sparse_chunk_documents
        WHERE sparse_index_id = v_index_id
    ) AS stats
    WHERE index_row.id = v_index_id;

    IF v_count > 0 THEN
        UPDATE public.sparse_indexes
        SET status = 'STALE', updated_at = now()
        WHERE id = v_index_id AND status = 'READY';
    END IF;

    RETURN v_count;
END;
$$;

CREATE OR REPLACE FUNCTION public.search_sparse_legal_chunks(
    p_terms TEXT[],
    p_sparse_index_name TEXT,
    p_top_k INTEGER,
    p_as_of_date DATE,
    p_legal_approvals TEXT[],
    p_usage_policies TEXT[],
    p_provenance_statuses TEXT[],
    p_temporal_statuses TEXT[],
    p_rights_statuses TEXT[]
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
            AND document.legal_approval = ANY(p_legal_approvals)
            AND document.usage_policy = ANY(p_usage_policies)
            AND document.provenance_status = ANY(p_provenance_statuses)
            AND document.temporal_status = ANY(p_temporal_statuses)
            AND document.rights_status = ANY(p_rights_statuses)
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

REVOKE ALL ON FUNCTION public.upsert_source_document(JSONB) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.get_source_document(UUID) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.save_parsed_document(JSONB, JSONB, JSONB, JSONB) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.get_retrieval_chunks(UUID[]) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.list_retrieval_chunks_for_document(UUID) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.upsert_dense_index(JSONB) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.get_dense_index(TEXT) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.upsert_dense_embeddings(TEXT, JSONB) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.upsert_dense_embedding_statuses(TEXT, JSONB) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.list_dense_embedding_work(TEXT, TEXT[], INTEGER) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.upsert_sparse_index(JSONB) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.get_sparse_index(TEXT) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.list_sparse_index_work(TEXT, TEXT[], INTEGER) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.upsert_sparse_chunk_documents(TEXT, JSONB) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.search_sparse_legal_chunks(
    TEXT[], TEXT, INTEGER, DATE, TEXT[], TEXT[], TEXT[], TEXT[], TEXT[]
) FROM PUBLIC, anon, authenticated;

GRANT EXECUTE ON FUNCTION public.upsert_source_document(JSONB) TO service_role;
GRANT EXECUTE ON FUNCTION public.get_source_document(UUID) TO service_role;
GRANT EXECUTE ON FUNCTION public.save_parsed_document(JSONB, JSONB, JSONB, JSONB) TO service_role;
GRANT EXECUTE ON FUNCTION public.get_retrieval_chunks(UUID[]) TO service_role;
GRANT EXECUTE ON FUNCTION public.list_retrieval_chunks_for_document(UUID) TO service_role;
GRANT EXECUTE ON FUNCTION public.upsert_dense_index(JSONB) TO service_role;
GRANT EXECUTE ON FUNCTION public.get_dense_index(TEXT) TO service_role;
GRANT EXECUTE ON FUNCTION public.upsert_dense_embeddings(TEXT, JSONB) TO service_role;
GRANT EXECUTE ON FUNCTION public.upsert_dense_embedding_statuses(TEXT, JSONB) TO service_role;
GRANT EXECUTE ON FUNCTION public.list_dense_embedding_work(TEXT, TEXT[], INTEGER) TO service_role;
GRANT EXECUTE ON FUNCTION public.upsert_sparse_index(JSONB) TO service_role;
GRANT EXECUTE ON FUNCTION public.get_sparse_index(TEXT) TO service_role;
GRANT EXECUTE ON FUNCTION public.list_sparse_index_work(TEXT, TEXT[], INTEGER) TO service_role;
GRANT EXECUTE ON FUNCTION public.upsert_sparse_chunk_documents(TEXT, JSONB) TO service_role;
GRANT EXECUTE ON FUNCTION public.search_sparse_legal_chunks(
    TEXT[], TEXT, INTEGER, DATE, TEXT[], TEXT[], TEXT[], TEXT[], TEXT[]
) TO service_role;
