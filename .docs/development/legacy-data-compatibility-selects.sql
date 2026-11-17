-- Legacy compatibility audit. SELECT only; no RPC calls and no secrets output.
-- NOT EXECUTED against PostgreSQL in this task. Run numbered sections separately.
-- Run L0/L1 first. Stop if required tables/columns/types differ or access is denied.
-- L2+ targets the CURRENT local schema, not an assumed legacy schema.
-- Counts reflect the executing role/snapshot. SQL Editor is not the application role.
-- Hash/vector/posting scans can be expensive: run separately on a quiet system.

-- L0. Role, relation inventory, columns, extensions. No connection strings.
SELECT current_database() AS database_name, current_user AS executing_role,
       current_setting('server_version') AS postgres_version,
       current_setting('transaction_read_only') AS transaction_read_only,
       now() AS observed_at;

SELECT n.nspname AS schema_name, c.relname AS relation_name, c.relkind,
       c.reltuples::bigint AS estimated_rows_not_exact, c.relrowsecurity,
       has_table_privilege(c.oid, 'SELECT') AS can_select
FROM pg_catalog.pg_class c
JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind IN ('r', 'p', 'v', 'm', 'f')
  AND n.nspname NOT IN ('pg_catalog', 'information_schema', 'auth', 'storage',
                        'extensions', 'realtime', 'vault', 'supabase_migrations')
  AND n.nspname NOT LIKE 'pg_toast%' AND n.nspname NOT LIKE 'pg_temp_%'
ORDER BY n.nspname, c.relname;

SELECT c.table_schema, c.table_name, c.column_name, c.data_type, c.udt_name
FROM information_schema.columns c
WHERE c.table_schema NOT IN ('pg_catalog', 'information_schema', 'auth', 'storage',
                            'extensions', 'realtime', 'vault', 'supabase_migrations')
  AND c.table_schema NOT LIKE 'pg_toast%' AND c.table_schema NOT LIKE 'pg_temp_%'
ORDER BY c.table_schema, c.table_name, c.ordinal_position;

SELECT e.extname, e.extversion, n.nspname AS extension_schema
FROM pg_catalog.pg_extension e
JOIN pg_catalog.pg_namespace n ON n.oid = e.extnamespace
WHERE e.extname IN ('vector', 'pgcrypto');

-- Generate counts for candidate legacy chunk/vector tables. Does NOT execute them.
-- Review relation names before copying the generated SELECTs; no row contents exposed.
SELECT format('SELECT %L AS relation_name, count(*) AS exact_visible_rows FROM %I.%I;',
              n.nspname || '.' || c.relname, n.nspname, c.relname) AS count_select
FROM pg_catalog.pg_class c
JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind IN ('r', 'p', 'm', 'f')
  AND n.nspname NOT IN ('pg_catalog', 'information_schema', 'auth', 'storage',
                        'extensions', 'realtime', 'vault', 'supabase_migrations')
  AND n.nspname NOT LIKE 'pg_toast%' AND n.nspname NOT LIKE 'pg_temp_%'
  AND (c.relname ~* '(chunk|document|passage|embedding|vector|collection)'
       OR EXISTS (SELECT 1 FROM pg_catalog.pg_attribute a
                  WHERE a.attrelid = c.oid AND a.attnum > 0 AND NOT a.attisdropped
                    AND a.attname ~* '^(chunk_id|embedding|page_content|content|text)$'))
ORDER BY n.nspname, c.relname;

-- L1. Required-column gate: zero rows means names present, NOT type compatibility.
WITH required(table_name, names) AS (VALUES
 ('source_documents', ARRAY['id','source_id','source_record_id','source_url','title',
   'usage_policy','effective_from','effective_to','raw_content','raw_content_format',
   'raw_file_ref','raw_content_ref','raw_file_sha256','raw_content_sha256','raw_metadata']),
 ('document_structures', ARRAY['id','source_document_id','schema_version','parser_version','content_sha256']),
 ('document_nodes', ARRAY['document_structure_id','node_id']),
 ('document_blocks', ARRAY['document_structure_id','block_id']),
 ('retrieval_chunks', ARRAY['id','source_document_id','document_structure_id','chunk_key',
   'content','content_sha256','node_id','block_id','chunk_type','start_offset','end_offset','metadata']),
 ('sparse_indexes', ARRAY['id','index_name','algorithm','tokenizer','language_config',
   'index_version','status','document_count','total_token_count','average_document_length','k1','b','updated_at']),
 ('sparse_chunk_documents', ARRAY['id','sparse_index_id','retrieval_chunk_id','status','token_count','indexed_text_sha256']),
 ('sparse_postings', ARRAY['sparse_index_id','sparse_chunk_document_id','term','term_frequency','positions']),
 ('dense_indexes', ARRAY['id','index_name','provider','model_name','embedding_dimension',
   'distance_metric','index_version','status','metadata','updated_at']),
 ('dense_chunk_embeddings', ARRAY['id','dense_index_id','retrieval_chunk_id','embedding',
   'embedded_text_sha256','status','metadata'])
)
SELECT r.table_name, x.column_name AS missing_column
FROM required r CROSS JOIN LATERAL unnest(r.names) x(column_name)
WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns c
                  WHERE c.table_schema = 'public' AND c.table_name = r.table_name
                    AND c.column_name = x.column_name)
ORDER BY r.table_name, x.column_name;

SELECT to_regprocedure('pg_catalog.sha256(bytea)') IS NOT NULL AS builtin_sha256_available,
       to_regclass('storage.objects') IS NOT NULL AS storage_catalog_exists;

-- L2. Exact visible dataset counts and VBPL identity (canonical vs URL candidate).
SELECT (SELECT count(*) FROM public.source_documents) AS sources,
       (SELECT count(*) FROM public.source_documents WHERE source_id = 'vbpl') AS canonical_vbpl_sources,
       (SELECT count(*) FROM public.source_documents
        WHERE source_id IS DISTINCT FROM 'vbpl'
          AND source_url ~* '^https?://([a-z0-9-]+\.)*vbpl\.vn([/:]|$)') AS additional_vbpl_url_candidates,
       (SELECT count(*) FROM public.document_structures) AS structures,
       (SELECT count(*) FROM public.retrieval_chunks) AS chunks,
       (SELECT count(*) FROM public.retrieval_chunks c JOIN public.source_documents s
          ON s.id = c.source_document_id WHERE s.source_id = 'vbpl') AS canonical_vbpl_chunks;

SELECT source_id, count(*) AS sources FROM public.source_documents
GROUP BY source_id ORDER BY count(*) DESC, source_id;

SELECT s.source_id = 'vbpl' AS canonical_vbpl, count(*) AS sources,
       count(*) FILTER (WHERE NOT EXISTS (SELECT 1 FROM public.document_structures d
                         WHERE d.source_document_id = s.id)) AS without_structure,
       count(*) FILTER (WHERE NOT EXISTS (SELECT 1 FROM public.retrieval_chunks c
                         WHERE c.source_document_id = s.id)) AS without_chunks
FROM public.source_documents s GROUP BY (s.source_id = 'vbpl');

-- L3. Parser/schema cohorts; version mismatch alone is NOT a reparse decision.
WITH chunk_counts AS (
 SELECT document_structure_id, count(*) AS n FROM public.retrieval_chunks GROUP BY document_structure_id
)
SELECT d.schema_version, d.parser_version, s.source_id, count(*) AS structures,
       sum(COALESCE(c.n, 0)) AS chunks,
       count(*) FILTER (WHERE COALESCE(c.n, 0) = 0) AS structures_without_chunks
FROM public.document_structures d
LEFT JOIN public.source_documents s ON s.id = d.source_document_id
LEFT JOIN chunk_counts c ON c.document_structure_id = d.id
GROUP BY d.schema_version, d.parser_version, s.source_id
ORDER BY d.schema_version, d.parser_version, s.source_id;

-- L4. Chunk/source contract failures. Output UUIDs/reasons only; no content dump.
WITH checked AS (
 SELECT c.id, c.source_document_id, c.document_structure_id,
   array_remove(ARRAY[
     CASE WHEN s.id IS NULL THEN 'MISSING_SOURCE' END,
     CASE WHEN d.id IS NULL OR d.source_document_id IS DISTINCT FROM c.source_document_id THEN 'STRUCTURE_SOURCE_MISMATCH' END,
     CASE WHEN c.content IS NULL OR btrim(c.content) = '' THEN 'EMPTY_CONTENT' END,
     CASE WHEN c.content_sha256 IS NULL OR c.content_sha256 !~ '^[0-9a-f]{64}$'
                    OR c.content_sha256 IS DISTINCT FROM encode(sha256(convert_to(c.content, 'UTF8')), 'hex') THEN 'CONTENT_HASH_INVALID' END,
     CASE WHEN c.chunk_key IS NULL OR btrim(c.chunk_key) = '' THEN 'EMPTY_CHUNK_KEY' END,
     CASE WHEN c.chunk_type IS NULL OR btrim(c.chunk_type) = '' THEN 'EMPTY_CHUNK_TYPE' END,
     CASE WHEN c.metadata IS NULL OR jsonb_typeof(c.metadata) <> 'object' THEN 'INVALID_CHUNK_METADATA' END,
     CASE WHEN s.title IS NULL OR btrim(s.title) = '' OR s.usage_policy IS NULL OR btrim(s.usage_policy) = ''
                    OR s.raw_metadata IS NULL OR jsonb_typeof(s.raw_metadata) <> 'object' THEN 'INVALID_SOURCE_METADATA' END,
     CASE WHEN c.start_offset < 0 OR c.end_offset < 0 OR c.end_offset < c.start_offset THEN 'INVALID_OFFSETS' END,
     CASE WHEN s.effective_to < s.effective_from THEN 'INVALID_SOURCE_DATES' END,
     CASE WHEN c.node_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM public.document_nodes n
                 WHERE n.document_structure_id = c.document_structure_id AND n.node_id = c.node_id) THEN 'MISSING_NODE' END,
     CASE WHEN c.block_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM public.document_blocks b
                 WHERE b.document_structure_id = c.document_structure_id AND b.block_id = c.block_id) THEN 'MISSING_BLOCK' END
   ], NULL) AS reasons
 FROM public.retrieval_chunks c
 LEFT JOIN public.source_documents s ON s.id = c.source_document_id
 LEFT JOIN public.document_structures d ON d.id = c.document_structure_id
)
SELECT id, source_document_id, document_structure_id, reasons,
       count(*) OVER () AS affected_chunks_total
FROM checked WHERE cardinality(reasons) > 0 ORDER BY id LIMIT 100;

SELECT document_structure_id, chunk_key, count(*) AS duplicate_count
FROM public.retrieval_chunks GROUP BY document_structure_id, chunk_key
HAVING count(*) > 1 ORDER BY duplicate_count DESC LIMIT 100;

SELECT (SELECT count(*) FROM public.document_structures d
          LEFT JOIN public.source_documents s ON s.id=d.source_document_id WHERE s.id IS NULL) AS orphan_structures,
       (SELECT count(*) FROM public.sparse_chunk_documents sd
          LEFT JOIN public.retrieval_chunks c ON c.id=sd.retrieval_chunk_id
          LEFT JOIN public.sparse_indexes i ON i.id=sd.sparse_index_id
          WHERE c.id IS NULL OR i.id IS NULL) AS orphan_sparse_documents,
       (SELECT count(*) FROM public.sparse_postings p
          LEFT JOIN public.sparse_chunk_documents sd ON sd.id=p.sparse_chunk_document_id
             AND sd.sparse_index_id=p.sparse_index_id WHERE sd.id IS NULL) AS orphan_postings,
       (SELECT count(*) FROM public.dense_chunk_embeddings e
          LEFT JOIN public.retrieval_chunks c ON c.id=e.retrieval_chunk_id
          LEFT JOIN public.dense_indexes i ON i.id=e.dense_index_id
          WHERE c.id IS NULL OR i.id IS NULL) AS orphan_embeddings;

-- L5. Source recovery candidates, not proof that bytes can be read or match hashes.
SELECT source_id, raw_content_format, count(*) AS sources,
 count(*) FILTER (WHERE NULLIF(btrim(raw_content), '') IS NOT NULL) AS with_inline_raw,
 count(*) FILTER (WHERE NULLIF(btrim(raw_content_ref), '') IS NOT NULL) AS with_raw_content_ref,
 count(*) FILTER (WHERE NULLIF(btrim(raw_file_ref), '') IS NOT NULL) AS with_raw_file_ref,
 count(*) FILTER (WHERE jsonb_typeof(raw_metadata->'stored_files') = 'array') AS with_stored_files_array,
 count(*) FILTER (WHERE raw_metadata ? 'stored_files'
                 AND jsonb_typeof(raw_metadata->'stored_files') <> 'array') AS malformed_stored_files
FROM public.source_documents GROUP BY source_id, raw_content_format;

-- L6. OPTIONAL: requires storage.objects SELECT. No Storage API or downloads.
-- Current refs are bucket/key. Other legacy formats are flagged, not assumed missing.
WITH refs AS (
 SELECT s.id AS source_document_id, s.source_id, 'raw_content' AS role,
        s.raw_content_ref AS ref, s.raw_content_sha256 AS recorded_sha256
 FROM public.source_documents s WHERE NULLIF(btrim(s.raw_content_ref), '') IS NOT NULL
 UNION ALL
 SELECT s.id, s.source_id, 'raw_file', s.raw_file_ref, s.raw_file_sha256
 FROM public.source_documents s WHERE NULLIF(btrim(s.raw_file_ref), '') IS NOT NULL
 UNION ALL
 SELECT s.id, s.source_id, f.item->>'role', f.item->>'storage_ref', f.item->>'sha256'
 FROM public.source_documents s
 CROSS JOIN LATERAL jsonb_array_elements(CASE
   WHEN jsonb_typeof(s.raw_metadata->'stored_files') = 'array' THEN s.raw_metadata->'stored_files'
   ELSE '[]'::jsonb END) f(item)
), checked AS (
 SELECT r.*, CASE WHEN r.ref ~ '^[^/:]+/.+' THEN true ELSE false END AS current_ref_format,
   EXISTS (SELECT 1 FROM storage.objects o WHERE o.bucket_id = split_part(r.ref, '/', 1)
      AND o.name = substring(r.ref FROM position('/' IN r.ref) + 1)) AS catalog_object_present,
   EXISTS (SELECT 1 FROM public.document_structures d WHERE d.source_document_id = r.source_document_id
      AND d.content_sha256 = r.recorded_sha256) AS recorded_hash_matches_structure
 FROM refs r
)
SELECT source_id, role, count(*) AS reference_rows,
 count(DISTINCT source_document_id) AS sources,
 count(*) FILTER (WHERE current_ref_format) AS supported_ref_format,
 count(*) FILTER (WHERE current_ref_format AND catalog_object_present) AS catalog_matches,
 count(*) FILTER (WHERE current_ref_format AND NOT catalog_object_present) AS catalog_not_visible_or_missing,
 count(*) FILTER (WHERE recorded_sha256 ~ '^[0-9a-f]{64}$') AS with_sha256_format,
 count(*) FILTER (WHERE recorded_hash_matches_structure) AS recorded_hash_matches_structure
FROM checked GROUP BY source_id, role ORDER BY source_id, role;

-- L7. BM25 target presence/config/statistics. Left join gives a row when missing.
WITH actual AS (
 SELECT sparse_index_id, count(*) AS sparse_documents,
   count(*) FILTER (WHERE status = 'INDEXED') AS n,
   COALESCE(sum(token_count) FILTER (WHERE status = 'INDEXED'), 0) AS tokens
 FROM public.sparse_chunk_documents GROUP BY sparse_index_id
)
SELECT target.name AS requested_index, i.id, i.status, i.algorithm, i.tokenizer,
 i.language_config, i.index_version, i.k1, i.b, i.updated_at,
 i.document_count, i.total_token_count, i.average_document_length,
 COALESCE(a.sparse_documents, 0) AS sparse_documents,
 COALESCE(a.n, 0) AS recomputed_indexed_documents, COALESCE(a.tokens, 0) AS recomputed_tokens,
 CASE WHEN COALESCE(a.n,0) = 0 THEN 0 ELSE a.tokens::double precision / a.n END AS recomputed_average,
 i.document_count = COALESCE(a.n,0) AND i.total_token_count = COALESCE(a.tokens,0)
   AND abs(i.average_document_length - CASE WHEN COALESCE(a.n,0)=0 THEN 0
                ELSE a.tokens::double precision/a.n END) <= 1e-8 AS statistics_match
FROM (VALUES ('vbpl-bm25-unicode-v1')) target(name)
LEFT JOIN public.sparse_indexes i ON i.index_name = target.name
LEFT JOIN actual a ON a.sparse_index_id = i.id;

-- One row per corpus chunk; zero-count target if absent is distinguished by L7.
WITH checked AS (
 SELECT c.id, s.source_id, sd.id AS sparse_document_id, sd.status,
  sd.indexed_text_sha256 = encode(sha256(convert_to(c.content, 'UTF8')), 'hex') AS hash_match,
  EXISTS (SELECT 1 FROM public.sparse_postings p
          WHERE p.sparse_chunk_document_id = sd.id AND p.sparse_index_id = sd.sparse_index_id) AS has_postings
 FROM public.retrieval_chunks c
 LEFT JOIN public.source_documents s ON s.id = c.source_document_id
 LEFT JOIN public.sparse_indexes i ON i.index_name = 'vbpl-bm25-unicode-v1'
 LEFT JOIN public.sparse_chunk_documents sd ON sd.sparse_index_id = i.id AND sd.retrieval_chunk_id = c.id
)
SELECT source_id, count(*) AS corpus_chunks,
 count(*) FILTER (WHERE sparse_document_id IS NOT NULL) AS chunks_with_sparse_document,
 count(*) FILTER (WHERE has_postings) AS chunks_with_postings,
 count(*) FILTER (WHERE status = 'INDEXED' AND has_postings AND hash_match) AS indexed_with_postings_and_matching_hash,
 count(*) FILTER (WHERE sparse_document_id IS NULL OR status IS DISTINCT FROM 'INDEXED'
                    OR NOT has_postings OR hash_match IS NOT TRUE) AS not_proven_ready
FROM checked GROUP BY source_id ORDER BY source_id;

WITH p AS (
 SELECT sparse_index_id, sparse_chunk_document_id, count(*) AS postings,
        sum(term_frequency) AS total_tf,
        count(*) FILTER (WHERE term IS NULL OR btrim(term) = '' OR term_frequency <= 0
           OR (positions IS NOT NULL AND (cardinality(positions) <> term_frequency
                         OR EXISTS (SELECT 1 FROM unnest(positions) pos WHERE pos < 0 OR pos IS NULL)))) AS invalid_postings
 FROM public.sparse_postings GROUP BY sparse_index_id, sparse_chunk_document_id
)
SELECT sd.status, count(*) AS sparse_documents, sum(COALESCE(p.postings,0)) AS posting_rows,
 count(*) FILTER (WHERE sd.token_count IS DISTINCT FROM COALESCE(p.total_tf,0)) AS token_count_tf_mismatch,
 sum(COALESCE(p.invalid_postings,0)) AS invalid_postings
FROM public.sparse_chunk_documents sd
JOIN public.sparse_indexes i ON i.id=sd.sparse_index_id AND i.index_name='vbpl-bm25-unicode-v1'
LEFT JOIN p ON p.sparse_chunk_document_id=sd.id AND p.sparse_index_id=sd.sparse_index_id
GROUP BY sd.status;

-- SQL computes DF at query time; postings on non-INDEXED documents can affect DF.
SELECT p.term, count(DISTINCT p.sparse_chunk_document_id) AS rpc_document_frequency,
 count(DISTINCT p.sparse_chunk_document_id) FILTER (WHERE sd.status='INDEXED') AS indexed_document_frequency,
 count(*) FILTER (WHERE sd.id IS NULL OR sd.status IS DISTINCT FROM 'INDEXED') AS stale_or_orphan_postings
FROM public.sparse_postings p
JOIN public.sparse_indexes i ON i.id=p.sparse_index_id AND i.index_name='vbpl-bm25-unicode-v1'
LEFT JOIN public.sparse_chunk_documents sd ON sd.id=p.sparse_chunk_document_id AND sd.sparse_index_id=p.sparse_index_id
GROUP BY p.term
ORDER BY stale_or_orphan_postings DESC, rpc_document_frequency DESC, p.term LIMIT 100;

-- L8. All dense index metadata; whitelist provenance fields rather than dumping JSON.
SELECT EXISTS (SELECT 1 FROM public.dense_indexes
               WHERE index_name='vbpl-multilingual-e5-small-v1') AS target_dense_index_exists;

SELECT id, index_name, status, provider, model_name, embedding_dimension, distance_metric,
 index_version, updated_at, metadata->'normalized' AS normalized,
 metadata->>'passage_prefix' AS passage_prefix, metadata->>'query_prefix' AS query_prefix,
 metadata->>'revision' AS revision, metadata->>'model_revision' AS model_revision,
 metadata->>'checkpoint_revision' AS checkpoint_revision, metadata->>'pooling' AS pooling,
 metadata->>'max_seq_length' AS max_seq_length
FROM public.dense_indexes ORDER BY index_name;

-- Actual dimension independent of index declaration and extension function schema.
SELECT i.index_name, e.status,
 CASE WHEN e.embedding IS NOT NULL THEN jsonb_array_length(e.embedding::text::jsonb) END AS actual_dimension,
 e.metadata->>'model' AS vector_model, e.metadata->>'revision' AS vector_revision,
 e.metadata->>'model_revision' AS vector_model_revision,
 e.metadata->>'checkpoint_revision' AS vector_checkpoint_revision,
 e.metadata->>'prefix' AS vector_prefix,
 count(*) AS embeddings
FROM public.dense_chunk_embeddings e LEFT JOIN public.dense_indexes i ON i.id=e.dense_index_id
GROUP BY i.index_name, e.status,
 CASE WHEN e.embedding IS NOT NULL THEN jsonb_array_length(e.embedding::text::jsonb) END,
 e.metadata->>'model', e.metadata->>'revision', e.metadata->>'model_revision',
 e.metadata->>'checkpoint_revision', e.metadata->>'prefix'
ORDER BY i.index_name, e.status, actual_dimension;

-- L9. Heavy full scan of target vectors: numeric/hash compatibility, NOT revision proof.
-- pgvector stores finite components; corrupt/non-pgvector legacy columns must stop at L1.
WITH checked AS (
 SELECT c.id, s.source_id, i.id AS index_id, e.id AS embedding_id, e.status,
   CASE WHEN e.embedding IS NOT NULL THEN jsonb_array_length(e.embedding::text::jsonb) END AS dims,
   v.norm,
   e.embedded_text_sha256 = encode(sha256(convert_to('passage: ' || c.content,'UTF8')), 'hex') AS passage_hash_match
 FROM public.retrieval_chunks c
 LEFT JOIN public.source_documents s ON s.id=c.source_document_id
 LEFT JOIN public.dense_indexes i ON i.index_name='vbpl-multilingual-e5-small-v1'
 LEFT JOIN public.dense_chunk_embeddings e ON e.dense_index_id=i.id AND e.retrieval_chunk_id=c.id
 LEFT JOIN LATERAL (SELECT sqrt(sum(power(x.value::double precision, 2))) AS norm
     FROM jsonb_array_elements_text(COALESCE(e.embedding::text::jsonb,'[]'::jsonb)) x(value)) v ON true
)
SELECT source_id, count(*) AS corpus_chunks,
 count(*) FILTER (WHERE index_id IS NOT NULL) AS chunks_with_target_index_present,
 count(*) FILTER (WHERE embedding_id IS NOT NULL) AS chunks_with_target_embedding,
 count(*) FILTER (WHERE status='INDEXED' AND dims=384 AND abs(norm-1)<=1e-4 AND passage_hash_match)
   AS numerically_compatible_and_hash_matching_not_revision_verified,
 count(*) FILTER (WHERE embedding_id IS NULL OR status IS DISTINCT FROM 'INDEXED'
             OR dims IS DISTINCT FROM 384 OR norm IS NULL OR abs(norm-1)>1e-4
             OR passage_hash_match IS NOT TRUE) AS missing_or_numerically_incompatible,
 min(norm) AS min_norm, max(norm) AS max_norm
FROM checked GROUP BY source_id ORDER BY source_id;

-- L10. Eligibility distributions, no arbitrary choice of policy/date for live testing.
SELECT source_id, usage_policy, count(*) AS sources,
 count(*) FILTER (WHERE effective_from IS NULL) AS null_start,
 count(*) FILTER (WHERE effective_to IS NULL) AS null_end,
 count(*) FILTER (WHERE effective_to < effective_from) AS invalid_date_ranges,
 min(effective_from) AS earliest_start, max(effective_to) AS latest_end
FROM public.source_documents GROUP BY source_id, usage_policy ORDER BY source_id, usage_policy;

-- L11. Deployed RPC signatures and role privileges, without executing RPCs.
SELECT p.proname, pg_get_function_identity_arguments(p.oid) AS identity_arguments,
 p.provolatile, p.prosecdef, pg_get_function_result(p.oid) AS result_type,
 has_function_privilege(current_user,p.oid,'EXECUTE') AS executing_role_can_execute,
 has_function_privilege('service_role',p.oid,'EXECUTE') AS service_role_can_execute,
 has_function_privilege('anon',p.oid,'EXECUTE') AS anon_can_execute
FROM pg_catalog.pg_proc p JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace
WHERE n.nspname='public' AND p.proname IN ('get_sparse_index','get_dense_index',
 'get_retrieval_chunks','get_source_document','search_sparse_legal_chunks','search_legal_chunks')
ORDER BY p.proname, identity_arguments;

-- L12. Deployed FK/cascade behavior (catalog only). Never invoke save_parsed_document.
SELECT c.conrelid::regclass AS referencing_table, c.conname,
       c.confrelid::regclass AS referenced_table, pg_get_constraintdef(c.oid) AS definition
FROM pg_catalog.pg_constraint c
WHERE c.contype='f' AND c.connamespace='public'::regnamespace
ORDER BY c.conrelid::regclass::text, c.conname;
