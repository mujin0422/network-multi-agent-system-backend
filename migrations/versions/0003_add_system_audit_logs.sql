CREATE TYPE audit_actor_type AS ENUM ('USER', 'SYSTEM', 'AGENT');
CREATE TYPE audit_event_status AS ENUM ('SUCCESS', 'FAILED', 'DENIED');

CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_user_id VARCHAR(64) REFERENCES users(id) ON DELETE SET NULL,
    actor_display_name VARCHAR(255),
    actor_type audit_actor_type NOT NULL,
    action VARCHAR(100) NOT NULL CHECK (length(btrim(action)) > 0),
    resource_type VARCHAR(100) NOT NULL
        CHECK (length(btrim(resource_type)) > 0),
    resource_id VARCHAR(64),
    event_status audit_event_status NOT NULL,
    summary TEXT,
    event_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    request_id UUID,
    source_ip VARCHAR(45),
    user_agent TEXT,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_audit_logs_actor CHECK (
        actor_type <> 'USER' OR actor_user_id IS NOT NULL
    ),
    CONSTRAINT ck_audit_logs_event_data_object CHECK (
        jsonb_typeof(event_data) = 'object'
    )
);

CREATE INDEX idx_audit_logs_occurred_at
    ON audit_logs(occurred_at DESC);
CREATE INDEX idx_audit_logs_actor_time
    ON audit_logs(actor_user_id, occurred_at DESC);
CREATE INDEX idx_audit_logs_resource_time
    ON audit_logs(resource_type, resource_id, occurred_at DESC);
CREATE INDEX idx_audit_logs_action_status_time
    ON audit_logs(action, event_status, occurred_at DESC);
CREATE INDEX idx_audit_logs_request_id ON audit_logs(request_id);
