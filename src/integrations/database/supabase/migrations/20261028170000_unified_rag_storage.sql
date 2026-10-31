-- Unified RAG storage schema for Supabase/PostgreSQL.
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE source_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id TEXT,
    source_record_id TEXT,
    source_snapshot_id TEXT,
    document_number TEXT,
    title TEXT NOT NULL,
    document_type TEXT,
    issuing_authority TEXT,
    language TEXT,
    source_url TEXT,
    raw_content_format TEXT CHECK (raw_content_format IN ('html', 'text')),
    raw_content TEXT,
    issued_on DATE,
    effective_from DATE,
    effective_to DATE,
    effect_status_reported TEXT,
    status_observed_at TIMESTAMPTZ,
    raw_file_ref TEXT,
    raw_content_ref TEXT,
    raw_file_sha256 TEXT,
    raw_content_sha256 TEXT,
    raw_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    usage_policy TEXT NOT NULL DEFAULT 'EXPERIMENTAL_ONLY',
    legal_approval TEXT NOT NULL DEFAULT 'QUARANTINE',
    provenance_status TEXT NOT NULL DEFAULT 'UNVERIFIED',
    temporal_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    rights_status TEXT NOT NULL DEFAULT 'UNVERIFIED',
    collected_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_source_document UNIQUE (source_id, source_record_id),
    CONSTRAINT chk_source_effective_dates CHECK (
        effective_to IS NULL
        OR effective_from IS NULL
        OR effective_to >= effective_from
    )
);

CREATE INDEX idx_source_documents_number ON source_documents (document_number);
CREATE INDEX idx_source_documents_effective_dates ON source_documents (effective_from, effective_to);
CREATE INDEX idx_source_documents_metadata ON source_documents USING GIN (raw_metadata);
CREATE INDEX idx_source_documents_title_fts
    ON source_documents USING GIN (to_tsvector('simple', coalesce(title, '')));

CREATE TABLE document_structures (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_document_id UUID NOT NULL UNIQUE
        REFERENCES source_documents(id) ON DELETE CASCADE,
    schema_version TEXT NOT NULL,
    parser_version TEXT NOT NULL,
    content_sha256 TEXT NOT NULL,
    max_chars INTEGER,
    excluded_segments JSONB NOT NULL DEFAULT '[]'::jsonb,
    issues JSONB NOT NULL DEFAULT '[]'::jsonb,
    parsed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_document_structure_source UNIQUE (id, source_document_id)
);

CREATE TABLE document_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_structure_id UUID NOT NULL
        REFERENCES document_structures(id) ON DELETE CASCADE,
    node_id TEXT NOT NULL,
    parent_node_id TEXT,
    kind TEXT NOT NULL,
    label TEXT,
    scope TEXT,
    heading_block_id TEXT,
    ordinal INTEGER,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_document_node UNIQUE (document_structure_id, node_id),
    CONSTRAINT chk_document_node_ordinal CHECK (ordinal IS NULL OR ordinal >= 0),
    CONSTRAINT fk_document_node_parent
        FOREIGN KEY (document_structure_id, parent_node_id)
        REFERENCES document_nodes(document_structure_id, node_id)
        DEFERRABLE INITIALLY DEFERRED
);

CREATE INDEX idx_document_nodes_parent ON document_nodes (document_structure_id, parent_node_id);
CREATE INDEX idx_document_nodes_kind ON document_nodes (document_structure_id, kind);

CREATE TABLE document_blocks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_structure_id UUID NOT NULL
        REFERENCES document_structures(id) ON DELETE CASCADE,
    block_id TEXT NOT NULL,
    node_id TEXT,
    block_type TEXT NOT NULL DEFAULT 'paragraph',
    content TEXT NOT NULL,
    ordinal INTEGER NOT NULL DEFAULT 0,
    start_offset INTEGER,
    end_offset INTEGER,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_document_block UNIQUE (document_structure_id, block_id),
    CONSTRAINT fk_document_block_node
        FOREIGN KEY (document_structure_id, node_id)
        REFERENCES document_nodes(document_structure_id, node_id),
    CONSTRAINT chk_document_block_offsets CHECK (
        start_offset IS NULL
        OR end_offset IS NULL
        OR end_offset >= start_offset
    )
);

CREATE INDEX idx_document_blocks_node ON document_blocks (document_structure_id, node_id);
CREATE INDEX idx_document_blocks_ordinal ON document_blocks (document_structure_id, ordinal);

CREATE TABLE retrieval_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_document_id UUID NOT NULL,
    document_structure_id UUID NOT NULL,
    chunk_key TEXT NOT NULL,
    content TEXT NOT NULL,
    content_sha256 TEXT NOT NULL,
    node_id TEXT,
    block_id TEXT,
    chunk_type TEXT NOT NULL DEFAULT 'text',
    ordinal INTEGER NOT NULL DEFAULT 0,
    start_offset INTEGER,
    end_offset INTEGER,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_chunk_structure_source
        FOREIGN KEY (document_structure_id, source_document_id)
        REFERENCES document_structures(id, source_document_id)
        ON DELETE CASCADE,
    CONSTRAINT uq_retrieval_chunk_key UNIQUE (document_structure_id, chunk_key),
    CONSTRAINT uq_retrieval_chunk_structure UNIQUE (id, document_structure_id),
    CONSTRAINT fk_chunk_node
        FOREIGN KEY (document_structure_id, node_id)
        REFERENCES document_nodes(document_structure_id, node_id),
    CONSTRAINT fk_chunk_block
        FOREIGN KEY (document_structure_id, block_id)
        REFERENCES document_blocks(document_structure_id, block_id),
    CONSTRAINT chk_retrieval_chunk_offsets CHECK (
        start_offset IS NULL
        OR end_offset IS NULL
        OR end_offset >= start_offset
    )
);

CREATE INDEX idx_retrieval_chunks_source ON retrieval_chunks (source_document_id);
CREATE INDEX idx_retrieval_chunks_structure ON retrieval_chunks (document_structure_id);
CREATE INDEX idx_retrieval_chunks_node ON retrieval_chunks (document_structure_id, node_id);
CREATE INDEX idx_retrieval_chunks_metadata ON retrieval_chunks USING GIN (metadata);

CREATE TABLE sparse_indexes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    index_name TEXT NOT NULL UNIQUE,
    algorithm TEXT NOT NULL DEFAULT 'BM25',
    tokenizer TEXT NOT NULL DEFAULT 'unicode',
    language_config TEXT NOT NULL DEFAULT 'simple',
    k1 DOUBLE PRECISION NOT NULL DEFAULT 1.2,
    b DOUBLE PRECISION NOT NULL DEFAULT 0.75,
    document_count BIGINT NOT NULL DEFAULT 0,
    total_token_count BIGINT NOT NULL DEFAULT 0,
    average_document_length DOUBLE PRECISION NOT NULL DEFAULT 0,
    index_version TEXT NOT NULL DEFAULT 'v1',
    status TEXT NOT NULL DEFAULT 'BUILDING'
        CHECK (status IN ('BUILDING', 'READY', 'STALE', 'FAILED', 'DISABLED')),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_sparse_k1 CHECK (k1 > 0),
    CONSTRAINT chk_sparse_b CHECK (b >= 0 AND b <= 1),
    CONSTRAINT chk_sparse_document_count CHECK (document_count >= 0),
    CONSTRAINT chk_sparse_total_tokens CHECK (total_token_count >= 0),
    CONSTRAINT chk_sparse_avg_length CHECK (average_document_length >= 0)
);

CREATE TABLE sparse_chunk_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sparse_index_id UUID NOT NULL
        REFERENCES sparse_indexes(id) ON DELETE CASCADE,
    retrieval_chunk_id UUID NOT NULL
        REFERENCES retrieval_chunks(id) ON DELETE CASCADE,
    token_count INTEGER NOT NULL DEFAULT 0,
    indexed_text_sha256 TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING', 'INDEXED', 'STALE', 'FAILED', 'SKIPPED')),
    indexed_at TIMESTAMPTZ,
    error_message TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_sparse_chunk_document UNIQUE (sparse_index_id, retrieval_chunk_id),
    CONSTRAINT uq_sparse_chunk_document_id_index UNIQUE (id, sparse_index_id),
    CONSTRAINT chk_sparse_chunk_token_count CHECK (token_count >= 0)
);

CREATE INDEX idx_sparse_chunk_documents_chunk ON sparse_chunk_documents (retrieval_chunk_id);
CREATE INDEX idx_sparse_chunk_documents_status ON sparse_chunk_documents (sparse_index_id, status);

CREATE TABLE sparse_postings (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sparse_index_id UUID NOT NULL,
    sparse_chunk_document_id UUID NOT NULL,
    term TEXT NOT NULL,
    term_frequency INTEGER NOT NULL DEFAULT 1,
    positions INTEGER[],
    CONSTRAINT fk_sparse_posting_chunk_index
        FOREIGN KEY (sparse_chunk_document_id, sparse_index_id)
        REFERENCES sparse_chunk_documents(id, sparse_index_id)
        ON DELETE CASCADE,
    CONSTRAINT uq_sparse_posting_term UNIQUE (sparse_chunk_document_id, term),
    CONSTRAINT chk_sparse_term_frequency CHECK (term_frequency > 0)
);

CREATE INDEX idx_sparse_postings_term ON sparse_postings (sparse_index_id, term);
CREATE INDEX idx_sparse_postings_chunk ON sparse_postings (sparse_chunk_document_id);

CREATE TABLE dense_indexes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    index_name TEXT NOT NULL UNIQUE,
    provider TEXT NOT NULL,
    model_name TEXT NOT NULL,
    embedding_dimension INTEGER NOT NULL DEFAULT 1536,
    distance_metric TEXT NOT NULL DEFAULT 'cosine'
        CHECK (distance_metric IN ('cosine', 'l2', 'inner_product')),
    index_version TEXT NOT NULL DEFAULT 'v1',
    status TEXT NOT NULL DEFAULT 'BUILDING'
        CHECK (status IN ('BUILDING', 'READY', 'STALE', 'FAILED', 'DISABLED')),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_dense_embedding_dimension CHECK (embedding_dimension > 0)
);

CREATE TABLE dense_chunk_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dense_index_id UUID NOT NULL
        REFERENCES dense_indexes(id) ON DELETE CASCADE,
    retrieval_chunk_id UUID NOT NULL
        REFERENCES retrieval_chunks(id) ON DELETE CASCADE,
    embedding VECTOR(1536) NOT NULL,
    embedded_text_sha256 TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'INDEXED'
        CHECK (status IN ('PENDING', 'INDEXED', 'STALE', 'FAILED', 'SKIPPED')),
    embedded_at TIMESTAMPTZ,
    error_message TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_dense_chunk_embedding UNIQUE (dense_index_id, retrieval_chunk_id)
);

CREATE INDEX idx_dense_embeddings_chunk ON dense_chunk_embeddings (retrieval_chunk_id);
CREATE INDEX idx_dense_embeddings_status ON dense_chunk_embeddings (dense_index_id, status);
CREATE INDEX idx_dense_embeddings_vector
    ON dense_chunk_embeddings USING hnsw (embedding vector_cosine_ops);

-- No client-facing policies are created. Server-side service-role access bypasses RLS;
-- anon/authenticated roles cannot access stored legal documents by default.
ALTER TABLE source_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_structures ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_nodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_blocks ENABLE ROW LEVEL SECURITY;
ALTER TABLE retrieval_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE sparse_indexes ENABLE ROW LEVEL SECURITY;
ALTER TABLE sparse_chunk_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE sparse_postings ENABLE ROW LEVEL SECURITY;
ALTER TABLE dense_indexes ENABLE ROW LEVEL SECURITY;
ALTER TABLE dense_chunk_embeddings ENABLE ROW LEVEL SECURITY;
