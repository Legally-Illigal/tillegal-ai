-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

## Refactor decisions

### Keep

| Table | Column | Reason |
|---|---|---|
| source_documents | usage_policy | Giữ để phân loại cách sử dụng tài liệu trong tương lai. |

### Remove

| Table | Column | Reason |
|---|---|---|
| source_documents | status_observed_at | Không lưu lịch sử quan sát trạng thái hiệu lực. |
| source_documents | legal_approval | Không cần quy trình phê duyệt riêng trong retrieval. |
| source_documents | provenance_status | Không cần đánh dấu trạng thái provenance dưới dạng cột độc lập. |
| source_documents | temporal_status | Không cần trạng thái thời gian riêng; lấy effective_from/effective_to làm nguồn tính ngày hiệu lực. |
| source_documents | rights_status | Không cần kiểm soát quyền sử dụng tài liệu. |
| document_structures | excluded_segments | Không lưu danh sách segment bị parser loại bỏ; không tham gia retrieval. |

### Required code changes

- Remove `status_observed_at` from the source-document repository input model.
- Remove `legal_approval`, `provenance_status`, `temporal_status`, and `rights_status` from document models and retrieval request models.
- Remove their RPC parameters, result columns, and SQL predicates from dense and sparse retrieval.
- Keep `usage_policy` in the database schema and document model only if retrieval or application logic still uses it; otherwise remove the remaining unused references too.
- Remove `excluded_segments` from the parsed-document repository model and the `save_parsed_document` RPC payload.


CREATE TABLE public.schema_migrations (
  version text NOT NULL,
  applied_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT schema_migrations_pkey PRIMARY KEY (version)
);
CREATE TABLE public.source_documents (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  source_id text,
  source_record_id text,
  source_snapshot_id text,
  title text NOT NULL,
  language text,
  source_url text,
  issued_on date,
  effective_from date,
  effective_to date,
  effect_status_reported text,
  status_observed_at timestamp with time zone,
  raw_content_ref text,
  raw_content_sha256 text,
  raw_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  usage_policy text NOT NULL DEFAULT 'EXPERIMENTAL_ONLY'::text,
  legal_approval text NOT NULL DEFAULT 'QUARANTINE'::text,
  provenance_status text NOT NULL DEFAULT 'UNVERIFIED'::text,
  temporal_status text NOT NULL DEFAULT 'UNKNOWN'::text,
  rights_status text NOT NULL DEFAULT 'UNVERIFIED'::text,
  collected_at timestamp with time zone,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT source_documents_pkey PRIMARY KEY (id)
);
CREATE TABLE public.document_structures (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  source_document_id uuid NOT NULL UNIQUE,
  schema_version text NOT NULL,
  parser_version text NOT NULL,
  content_sha256 text NOT NULL,
  max_chars integer,
  excluded_segments jsonb NOT NULL DEFAULT '[]'::jsonb,
  issues jsonb NOT NULL DEFAULT '[]'::jsonb,
  parsed_at timestamp with time zone NOT NULL DEFAULT now(),
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT document_structures_pkey PRIMARY KEY (id),
  CONSTRAINT document_structures_source_document_id_fkey FOREIGN KEY (source_document_id) REFERENCES public.source_documents(id)
);
CREATE TABLE public.document_nodes (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  document_structure_id uuid NOT NULL,
  node_id text NOT NULL,
  parent_node_id text,
  kind text NOT NULL,
  label text,
  scope text,
  heading_block_id text,
  ordinal integer CHECK (ordinal IS NULL OR ordinal >= 0),
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT document_nodes_pkey PRIMARY KEY (id),
  CONSTRAINT document_nodes_document_structure_id_fkey FOREIGN KEY (document_structure_id) REFERENCES public.document_structures(id),
  CONSTRAINT fk_document_node_parent FOREIGN KEY (document_structure_id) REFERENCES public.document_nodes(document_structure_id),
  CONSTRAINT fk_document_node_parent FOREIGN KEY (parent_node_id) REFERENCES public.document_nodes(node_id)
);
CREATE TABLE public.document_blocks (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  document_structure_id uuid NOT NULL,
  block_id text NOT NULL,
  node_id text,
  block_type text NOT NULL DEFAULT 'paragraph'::text,
  content text NOT NULL,
  ordinal integer NOT NULL DEFAULT 0,
  start_offset integer,
  end_offset integer,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT document_blocks_pkey PRIMARY KEY (id),
  CONSTRAINT document_blocks_document_structure_id_fkey FOREIGN KEY (document_structure_id) REFERENCES public.document_structures(id),
  CONSTRAINT fk_document_block_node FOREIGN KEY (document_structure_id) REFERENCES public.document_nodes(document_structure_id),
  CONSTRAINT fk_document_block_node FOREIGN KEY (node_id) REFERENCES public.document_nodes(node_id)
);
CREATE TABLE public.retrieval_chunks (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  source_document_id uuid NOT NULL,
  document_structure_id uuid NOT NULL,
  chunk_key text NOT NULL,
  content text NOT NULL,
  content_sha256 text NOT NULL,
  node_id text,
  block_id text,
  chunk_type text NOT NULL DEFAULT 'text'::text,
  ordinal integer NOT NULL DEFAULT 0,
  start_offset integer,
  end_offset integer,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT retrieval_chunks_pkey PRIMARY KEY (id),
  CONSTRAINT fk_chunk_structure_source FOREIGN KEY (document_structure_id) REFERENCES public.document_structures(id),
  CONSTRAINT fk_chunk_structure_source FOREIGN KEY (source_document_id) REFERENCES public.document_structures(source_document_id),
  CONSTRAINT fk_chunk_node FOREIGN KEY (document_structure_id) REFERENCES public.document_nodes(document_structure_id),
  CONSTRAINT fk_chunk_node FOREIGN KEY (node_id) REFERENCES public.document_nodes(node_id),
  CONSTRAINT fk_chunk_block FOREIGN KEY (document_structure_id) REFERENCES public.document_blocks(document_structure_id),
  CONSTRAINT fk_chunk_block FOREIGN KEY (block_id) REFERENCES public.document_blocks(block_id)
);
CREATE TABLE public.sparse_indexes (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  index_name text NOT NULL UNIQUE,
  algorithm text NOT NULL DEFAULT 'BM25'::text,
  tokenizer text NOT NULL DEFAULT 'unicode'::text,
  language_config text NOT NULL DEFAULT 'simple'::text,
  k1 double precision NOT NULL DEFAULT 1.2 CHECK (k1 > 0::double precision),
  b double precision NOT NULL DEFAULT 0.75 CHECK (b >= 0::double precision AND b <= 1::double precision),
  document_count bigint NOT NULL DEFAULT 0 CHECK (document_count >= 0),
  total_token_count bigint NOT NULL DEFAULT 0 CHECK (total_token_count >= 0),
  average_document_length double precision NOT NULL DEFAULT 0 CHECK (average_document_length >= 0::double precision),
  index_version text NOT NULL DEFAULT 'v1'::text,
  status text NOT NULL DEFAULT 'BUILDING'::text CHECK (status = ANY (ARRAY['BUILDING'::text, 'READY'::text, 'STALE'::text, 'FAILED'::text, 'DISABLED'::text])),
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT sparse_indexes_pkey PRIMARY KEY (id)
);
CREATE TABLE public.sparse_chunk_documents (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  sparse_index_id uuid NOT NULL,
  retrieval_chunk_id uuid NOT NULL,
  token_count integer NOT NULL DEFAULT 0 CHECK (token_count >= 0),
  indexed_text_sha256 text NOT NULL,
  status text NOT NULL DEFAULT 'PENDING'::text CHECK (status = ANY (ARRAY['PENDING'::text, 'INDEXED'::text, 'STALE'::text, 'FAILED'::text, 'SKIPPED'::text])),
  indexed_at timestamp with time zone,
  error_message text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT sparse_chunk_documents_pkey PRIMARY KEY (id),
  CONSTRAINT sparse_chunk_documents_sparse_index_id_fkey FOREIGN KEY (sparse_index_id) REFERENCES public.sparse_indexes(id),
  CONSTRAINT sparse_chunk_documents_retrieval_chunk_id_fkey FOREIGN KEY (retrieval_chunk_id) REFERENCES public.retrieval_chunks(id)
);
CREATE TABLE public.sparse_postings (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  sparse_index_id uuid NOT NULL,
  sparse_chunk_document_id uuid NOT NULL,
  term text NOT NULL,
  term_frequency integer NOT NULL DEFAULT 1 CHECK (term_frequency > 0),
  positions ARRAY,
  CONSTRAINT sparse_postings_pkey PRIMARY KEY (id),
  CONSTRAINT fk_sparse_posting_chunk_index FOREIGN KEY (sparse_chunk_document_id) REFERENCES public.sparse_chunk_documents(id),
  CONSTRAINT fk_sparse_posting_chunk_index FOREIGN KEY (sparse_index_id) REFERENCES public.sparse_chunk_documents(sparse_index_id)
);
CREATE TABLE public.dense_indexes (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  index_name text NOT NULL UNIQUE,
  provider text NOT NULL,
  model_name text NOT NULL,
  embedding_dimension integer NOT NULL DEFAULT 1536 CHECK (embedding_dimension > 0),
  distance_metric text NOT NULL DEFAULT 'cosine'::text CHECK (distance_metric = ANY (ARRAY['cosine'::text, 'l2'::text, 'inner_product'::text])),
  index_version text NOT NULL DEFAULT 'v1'::text,
  status text NOT NULL DEFAULT 'BUILDING'::text CHECK (status = ANY (ARRAY['BUILDING'::text, 'READY'::text, 'STALE'::text, 'FAILED'::text, 'DISABLED'::text])),
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT dense_indexes_pkey PRIMARY KEY (id)
);
CREATE TABLE public.dense_chunk_embeddings (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  dense_index_id uuid NOT NULL,
  retrieval_chunk_id uuid NOT NULL,
  embedding USER-DEFINED,
  embedded_text_sha256 text NOT NULL,
  status text NOT NULL DEFAULT 'INDEXED'::text CHECK (status = ANY (ARRAY['PENDING'::text, 'INDEXED'::text, 'STALE'::text, 'FAILED'::text, 'SKIPPED'::text])),
  embedded_at timestamp with time zone,
  error_message text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT dense_chunk_embeddings_pkey PRIMARY KEY (id),
  CONSTRAINT dense_chunk_embeddings_dense_index_id_fkey FOREIGN KEY (dense_index_id) REFERENCES public.dense_indexes(id),
  CONSTRAINT dense_chunk_embeddings_retrieval_chunk_id_fkey FOREIGN KEY (retrieval_chunk_id) REFERENCES public.retrieval_chunks(id)
);
CREATE TABLE public.executions (
  id uuid NOT NULL,
  status text NOT NULL DEFAULT 'queued'::text CHECK (status = ANY (ARRAY['queued'::text, 'running'::text, 'completed'::text, 'failed'::text])),
  input jsonb NOT NULL,
  result jsonb,
  error_message text,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  started_at timestamp with time zone,
  completed_at timestamp with time zone,
  CONSTRAINT executions_pkey PRIMARY KEY (id)
);
CREATE TABLE public.outbox_events (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  aggregate_type text NOT NULL,
  aggregate_id uuid NOT NULL,
  event_type text NOT NULL,
  payload jsonb NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  available_at timestamp with time zone NOT NULL DEFAULT now(),
  attempts integer NOT NULL DEFAULT 0 CHECK (attempts >= 0),
  locked_by text,
  locked_until timestamp with time zone,
  published_at timestamp with time zone,
  last_error text,
  CONSTRAINT outbox_events_pkey PRIMARY KEY (id)
);
CREATE TABLE public.idempotency_records (
  key_hash bytea NOT NULL CHECK (octet_length(key_hash) = 32),
  request_hash bytea NOT NULL CHECK (octet_length(request_hash) = 32),
  status text NOT NULL CHECK (status = ANY (ARRAY['in_progress'::text, 'completed'::text])),
  result jsonb,
  lease_owner uuid,
  lease_expires_at timestamp with time zone,
  expires_at timestamp with time zone NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT idempotency_records_pkey PRIMARY KEY (key_hash)
);
CREATE TABLE public.crawl_jobs (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  source_id text NOT NULL,
  crawl_date date NOT NULL,
  status text NOT NULL DEFAULT 'PENDING'::text CHECK (status = ANY (ARRAY['PENDING'::text, 'RUNNING'::text, 'SUCCEEDED'::text, 'FAILED'::text, 'CANCELLED'::text])),
  result jsonb NOT NULL DEFAULT '{}'::jsonb,
  error_message text,
  owner text,
  lease_until timestamp with time zone,
  attempts integer NOT NULL DEFAULT 0,
  max_attempts integer NOT NULL DEFAULT 3,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  started_at timestamp with time zone,
  completed_at timestamp with time zone,
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT crawl_jobs_pkey PRIMARY KEY (id)
);