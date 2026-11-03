CREATE TABLE public.idempotency_records (
    key_hash BYTEA PRIMARY KEY CHECK (octet_length(key_hash) = 32),
    request_hash BYTEA NOT NULL CHECK (octet_length(request_hash) = 32),
    status TEXT NOT NULL CHECK (status IN ('in_progress', 'completed')),
    result JSONB,
    lease_owner UUID,
    lease_expires_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_idempotency_record_state CHECK (
        (
            status = 'in_progress'
            AND result IS NULL
            AND lease_owner IS NOT NULL
            AND lease_expires_at IS NOT NULL
        )
        OR (
            status = 'completed'
            AND lease_owner IS NULL
            AND lease_expires_at IS NULL
        )
    )
);

CREATE INDEX idx_idempotency_records_expiry
    ON public.idempotency_records (expires_at);

ALTER TABLE public.idempotency_records ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.idempotency_records FROM PUBLIC;
REVOKE ALL ON TABLE public.idempotency_records
    FROM anon, authenticated, service_role;
