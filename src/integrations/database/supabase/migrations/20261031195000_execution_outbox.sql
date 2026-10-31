CREATE TABLE public.executions (
    id UUID PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued', 'running', 'completed', 'failed')),
    input JSONB NOT NULL,
    result JSONB,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_executions_status_created
    ON public.executions (status, created_at);

CREATE TABLE public.outbox_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aggregate_type TEXT NOT NULL,
    aggregate_id UUID NOT NULL,
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    available_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    locked_by TEXT,
    locked_until TIMESTAMPTZ,
    published_at TIMESTAMPTZ,
    last_error TEXT,
    CONSTRAINT uq_outbox_aggregate_event UNIQUE (aggregate_type, aggregate_id, event_type),
    CONSTRAINT chk_outbox_lock_fields CHECK (
        (locked_by IS NULL AND locked_until IS NULL)
        OR (locked_by IS NOT NULL AND locked_until IS NOT NULL)
    )
);

CREATE INDEX idx_outbox_events_dispatch
    ON public.outbox_events (available_at, created_at)
    WHERE published_at IS NULL;

ALTER TABLE public.executions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.outbox_events ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.executions, public.outbox_events FROM PUBLIC;
REVOKE ALL ON TABLE public.executions, public.outbox_events
    FROM anon, authenticated, service_role;
