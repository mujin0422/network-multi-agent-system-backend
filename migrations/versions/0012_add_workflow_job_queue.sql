-- Durable PostgreSQL queue used by the standalone AI workflow worker.

CREATE TYPE workflow_job_type AS ENUM ('MESSAGE', 'APPROVAL');
CREATE TYPE workflow_job_status AS ENUM (
    'PENDING', 'RUNNING', 'COMPLETED', 'FAILED'
);

CREATE TABLE workflow_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_type workflow_job_type NOT NULL,
    deduplication_key VARCHAR(160) NOT NULL UNIQUE,
    payload JSONB NOT NULL CHECK (jsonb_typeof(payload) = 'object'),
    job_status workflow_job_status NOT NULL DEFAULT 'PENDING',
    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    max_attempts INTEGER NOT NULL DEFAULT 3 CHECK (max_attempts > 0),
    available_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    locked_at TIMESTAMPTZ,
    locked_by VARCHAR(160),
    last_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    CONSTRAINT ck_workflow_jobs_lock CHECK (
        (job_status = 'RUNNING' AND locked_at IS NOT NULL AND locked_by IS NOT NULL)
        OR job_status <> 'RUNNING'
    ),
    CONSTRAINT ck_workflow_jobs_completed CHECK (
        completed_at IS NULL OR job_status IN ('COMPLETED', 'FAILED')
    )
);

CREATE INDEX idx_workflow_jobs_pending
    ON workflow_jobs(available_at, created_at, id)
    WHERE job_status = 'PENDING';

CREATE INDEX idx_workflow_jobs_running
    ON workflow_jobs(locked_at)
    WHERE job_status = 'RUNNING';
