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
        raw_file_ref,
        raw_file_sha256,
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
        v_document.raw_file_ref,
        v_document.raw_file_sha256,
        v_document.raw_content_ref,
        v_document.raw_content_sha256,
        COALESCE(v_document.raw_metadata, '{}'::JSONB),
        COALESCE(v_document.usage_policy, 'EXPERIMENTAL_ONLY'),
        v_document.collected_at
    )
    ON CONFLICT (source_id, source_record_id) DO UPDATE SET
        source_snapshot_id = COALESCE(EXCLUDED.source_snapshot_id, source_documents.source_snapshot_id),
        title = EXCLUDED.title,
        language = COALESCE(EXCLUDED.language, source_documents.language),
        source_url = COALESCE(EXCLUDED.source_url, source_documents.source_url),
        issued_on = COALESCE(EXCLUDED.issued_on, source_documents.issued_on),
        effective_from = COALESCE(EXCLUDED.effective_from, source_documents.effective_from),
        effective_to = COALESCE(EXCLUDED.effective_to, source_documents.effective_to),
        effect_status_reported = COALESCE(
            EXCLUDED.effect_status_reported,
            source_documents.effect_status_reported
        ),
        raw_file_ref = COALESCE(EXCLUDED.raw_file_ref, source_documents.raw_file_ref),
        raw_file_sha256 = COALESCE(EXCLUDED.raw_file_sha256, source_documents.raw_file_sha256),
        raw_content_ref = COALESCE(EXCLUDED.raw_content_ref, source_documents.raw_content_ref),
        raw_content_sha256 = COALESCE(EXCLUDED.raw_content_sha256, source_documents.raw_content_sha256),
        raw_metadata = source_documents.raw_metadata || EXCLUDED.raw_metadata,
        usage_policy = COALESCE(EXCLUDED.usage_policy, source_documents.usage_policy),
        collected_at = COALESCE(EXCLUDED.collected_at, source_documents.collected_at),
        updated_at = now()
    RETURNING * INTO v_saved;

    RETURN to_jsonb(v_saved);
END;
$$;
