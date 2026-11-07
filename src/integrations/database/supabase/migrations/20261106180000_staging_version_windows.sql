-- Additive experimental E5 storage. Existing vector(1536) tables and RPCs keep their contracts.
CREATE TABLE public.staging_version_windows (
    retrieval_chunk_id uuid NOT NULL REFERENCES public.retrieval_chunks(id) ON DELETE CASCADE,
    window_id text PRIMARY KEY,
    profile jsonb NOT NULL CHECK (profile->>'dimension' = '384'),
    ordinal integer NOT NULL CHECK (ordinal >= 0),
    locator jsonb NOT NULL,
    embedding vector(384) NOT NULL,
    UNIQUE (retrieval_chunk_id, profile, ordinal)
);
ALTER TABLE public.staging_version_windows ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.staging_version_windows FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT ON public.staging_version_windows TO service_role;

CREATE FUNCTION public.save_staging_version(p_source jsonb, p_parsed jsonb, p_profile jsonb, p_windows jsonb)
RETURNS text LANGUAGE plpgsql SECURITY INVOKER SET search_path = public, extensions AS $$
DECLARE
    vid text := p_source->>'source_record_id';
    sid uuid;
    structure_id uuid;
    found_rows integer;
BEGIN
    IF p_source->>'source_id' IS DISTINCT FROM 'tillegal:staging-version:v1'
       OR vid IS DISTINCT FROM p_source#>>'{raw_metadata,staging,document_version_id}'
       OR p_profile->>'dimension' IS DISTINCT FROM '384'
       OR jsonb_array_length(p_windows) < 1 THEN
        RAISE EXCEPTION 'Invalid staging profile or version';
    END IF;
    PERFORM pg_advisory_xact_lock(hashtextextended(vid, 0));
    SELECT id INTO sid FROM public.source_documents WHERE source_id=p_source->>'source_id' AND source_record_id=vid;
    IF sid IS NULL THEN
        sid := (public.upsert_source_document(p_source)->>'id')::uuid;
        -- New immutable structure only. The legacy replacement RPC invalidates
        -- READY indexes globally; this isolated E5 corpus must not do that.
        INSERT INTO public.document_structures(source_document_id, schema_version, parser_version,
            content_sha256, max_chars, excluded_segments, issues)
        SELECT sid, v.schema_version, v.parser_version, v.content_sha256, v.max_chars, v.excluded_segments, v.issues
        FROM jsonb_populate_record(NULL::public.document_structures,p_parsed->'structure') v
        RETURNING id INTO structure_id;
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
        structure_id,
        node.node_id,
        node.parent_node_id,
        node.kind,
        node.label,
        node.scope,
        node.heading_block_id,
        node.ordinal,
        COALESCE(node.metadata, '{}'::JSONB)
    FROM jsonb_populate_recordset(NULL::public.document_nodes, COALESCE(p_parsed->'nodes', '[]'::JSONB)) AS node;

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
        structure_id,
        block.block_id,
        block.node_id,
        COALESCE(block.block_type, 'paragraph'),
        block.content,
        COALESCE(block.ordinal, 0),
        block.start_offset,
        block.end_offset,
        COALESCE(block.metadata, '{}'::JSONB)
    FROM jsonb_populate_recordset(NULL::public.document_blocks, COALESCE(p_parsed->'blocks', '[]'::JSONB)) AS block;

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
        sid,
        structure_id,
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
    FROM jsonb_populate_recordset(NULL::public.retrieval_chunks, COALESCE(p_parsed->'chunks', '[]'::JSONB)) AS chunk;
    ELSE
        SELECT id INTO STRICT structure_id FROM public.document_structures
        WHERE source_document_id=sid AND content_sha256=p_parsed#>>'{structure,content_sha256}'
          AND parser_version=p_parsed#>>'{structure,parser_version}'
          AND max_chars=(p_parsed#>>'{structure,max_chars}')::integer;
    END IF;
    IF EXISTS (SELECT 1 FROM jsonb_array_elements(p_windows) w
               LEFT JOIN public.retrieval_chunks c ON c.document_structure_id=structure_id AND c.chunk_key=w->>'chunk_id'
               WHERE c.id IS NULL OR w->>'document_version_id' IS DISTINCT FROM vid)
    THEN RAISE EXCEPTION 'Window identity mismatch'; END IF;
    INSERT INTO public.staging_version_windows(retrieval_chunk_id, window_id, profile, ordinal, locator, embedding)
    SELECT c.id, w->>'window_id', p_profile, (w->>'ordinal')::integer, w-'vector', (w->>'vector')::vector(384)
    FROM jsonb_array_elements(p_windows) w JOIN public.retrieval_chunks c
      ON c.document_structure_id=structure_id AND c.chunk_key=w->>'chunk_id'
    ON CONFLICT (window_id) DO NOTHING;
    SELECT count(*) INTO found_rows FROM public.staging_version_windows w JOIN public.retrieval_chunks c
      ON c.id=w.retrieval_chunk_id WHERE c.document_structure_id=structure_id AND w.profile=p_profile;
    IF found_rows <> jsonb_array_length(p_windows) OR EXISTS (
        SELECT 1 FROM public.retrieval_chunks c WHERE c.document_structure_id=structure_id
        AND NOT EXISTS (SELECT 1 FROM public.staging_version_windows w WHERE w.retrieval_chunk_id=c.id AND w.profile=p_profile)
    ) THEN RAISE EXCEPTION 'Incomplete staging window set'; END IF;
    RETURN vid;
END;
$$;

CREATE FUNCTION public.read_staging_version(p_version text, p_profile jsonb)
RETURNS jsonb LANGUAGE sql STABLE SECURITY INVOKER SET search_path = public, extensions AS $$
    SELECT jsonb_build_object(
      'document', (s.raw_metadata->'staging') || jsonb_build_object('content',s.raw_content),
      'parsed', jsonb_build_object('schema_version', st.schema_version, 'parser_version', st.parser_version,
        'max_chars', st.max_chars, 'document_id', s.raw_metadata#>>'{staging,document_id}',
        'document_version_id', p_version, 'content_sha256', st.content_sha256,
        'excluded_segments', st.excluded_segments,
        'issues', COALESCE((SELECT jsonb_agg(x->'code') FROM jsonb_array_elements(st.issues) x),'[]'::jsonb),
        'nodes',(SELECT jsonb_agg(n.metadata ORDER BY n.ordinal) FROM public.document_nodes n WHERE n.document_structure_id=st.id),
        'blocks',(SELECT jsonb_agg(b.metadata ORDER BY b.ordinal) FROM public.document_blocks b WHERE b.document_structure_id=st.id),
        'chunks',(SELECT jsonb_agg(c.metadata ORDER BY c.ordinal) FROM public.retrieval_chunks c WHERE c.document_structure_id=st.id)),
      'profile', p_profile, 'windows', win.rows)
    FROM public.source_documents s JOIN public.document_structures st ON st.source_document_id=s.id
    CROSS JOIN LATERAL (
      SELECT jsonb_agg(w.locator || jsonb_build_object('vector',w.embedding::text::jsonb) ORDER BY c.ordinal,w.ordinal) AS rows
      FROM public.staging_version_windows w JOIN public.retrieval_chunks c ON c.id=w.retrieval_chunk_id
      WHERE c.document_structure_id=st.id AND w.profile=p_profile
    ) win
    WHERE s.source_id='tillegal:staging-version:v1' AND s.source_record_id=p_version AND win.rows IS NOT NULL
      AND s.usage_policy='EXPERIMENTAL_ONLY' AND s.legal_approval='QUARANTINE'
      AND s.temporal_status='UNKNOWN' AND s.provenance_status='UNVERIFIED' AND s.rights_status='UNVERIFIED';
$$;
REVOKE ALL ON FUNCTION public.save_staging_version(jsonb,jsonb,jsonb,jsonb), public.read_staging_version(text,jsonb) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.save_staging_version(jsonb,jsonb,jsonb,jsonb), public.read_staging_version(text,jsonb) TO service_role;
