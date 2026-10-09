\set ON_ERROR_STOP on

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ==========================================================================
-- ENUM TYPES
-- ==========================================================================
CREATE TYPE user_status AS ENUM ('ACTIVE', 'DISABLED');
CREATE TYPE message_sender AS ENUM ('USER', 'AGENT');
CREATE TYPE task_status AS ENUM (
    'PENDING', 'PLANNING', 'RUNNING', 'SUCCESS',
    'PARTIAL_SUCCESS', 'FAILED', 'REJECTED'
);
CREATE TYPE operation_status AS ENUM (
    'PENDING', 'WAITING_APPROVAL', 'RUNNING', 'SUCCESS',
    'PARTIAL_SUCCESS', 'FAILED', 'REJECTED', 'SKIPPED'
);
CREATE TYPE operation_device_status AS ENUM (
    'PENDING', 'WAITING_APPROVAL', 'RUNNING', 'SUCCESS',
    'FAILED', 'REJECTED', 'SKIPPED'
);
CREATE TYPE device_role AS ENUM ('SOURCE', 'TARGET', 'CONTEXT');
CREATE TYPE access_mode AS ENUM ('READ', 'WRITE');
CREATE TYPE dependency_type AS ENUM ('ON_SUCCESS', 'ON_COMPLETION');
CREATE TYPE execution_status AS ENUM ('PENDING', 'RUNNING', 'SUCCESS', 'FAILED');
CREATE TYPE device_action_status AS ENUM ('SUCCESS', 'FAILED');
CREATE TYPE device_action_type AS ENUM (
    'READ', 'PRE_CHECK', 'APPLY', 'POST_CHECK', 'ROLLBACK', 'ROLLBACK_VERIFY'
);
CREATE TYPE change_set_strategy AS ENUM (
    'NATIVE_CHECKPOINT', 'SNAPSHOT_RESTORE', 'COMPENSATING_COMMANDS'
);
CREATE TYPE change_set_status AS ENUM (
    'PLANNED', 'WAITING_APPROVAL', 'APPROVED', 'APPLYING', 'APPLIED',
    'VERIFYING', 'VERIFIED', 'ROLLING_BACK', 'ROLLED_BACK', 'ROLLBACK_FAILED'
);

-- ==========================================================================
-- 2.1 AUTHENTICATION & AUTHORIZATION
-- ==========================================================================
CREATE TABLE roles (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_updated_at TIMESTAMPTZ
);

CREATE TABLE management_functions (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE actions (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE permissions (
    id VARCHAR(64) PRIMARY KEY,
    function_id VARCHAR(64) NOT NULL REFERENCES management_functions(id) ON DELETE RESTRICT,
    action_id VARCHAR(64) NOT NULL REFERENCES actions(id) ON DELETE RESTRICT,
    CONSTRAINT uq_permissions_function_action UNIQUE (function_id, action_id)
);

CREATE TABLE role_permissions (
    role_id VARCHAR(64) NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id VARCHAR(64) NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE users (
    id VARCHAR(64) PRIMARY KEY,
    role_id VARCHAR(64) NOT NULL REFERENCES roles(id) ON DELETE RESTRICT,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hashed TEXT NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    status user_status NOT NULL DEFAULT 'ACTIVE',
    refresh_token TEXT,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_updated_at TIMESTAMPTZ,
    last_login_at TIMESTAMPTZ
);

-- ==========================================================================
-- 2.2 NETWORK INVENTORY
-- Credential dùng TEXT ASCII-armored PGP để lưu ciphertext, tuyệt đối không
-- lưu plaintext và không đưa khóa giải mã vào database.
-- ==========================================================================
CREATE TABLE credentials (
    id VARCHAR(64) PRIMARY KEY,
    username VARCHAR(255) NOT NULL,
    password TEXT NOT NULL,
    secret TEXT,
    encryption_type VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE categories (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE brands (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE devices (
    id VARCHAR(64) PRIMARY KEY,
    credential_id VARCHAR(64) REFERENCES credentials(id) ON DELETE SET NULL,
    brand_id VARCHAR(64) NOT NULL REFERENCES brands(id) ON DELETE RESTRICT,
    category_id VARCHAR(64) NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
    last_updated_by VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    hostname VARCHAR(255) NOT NULL UNIQUE,
    host VARCHAR(255) NOT NULL DEFAULT '127.0.0.1',
    port INTEGER NOT NULL CHECK (port BETWEEN 1 AND 65535),
    device_type VARCHAR(100) NOT NULL DEFAULT 'cisco_ios_telnet',
    location VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_devices_host_port UNIQUE (host, port)
);

-- ==========================================================================
-- 2.4 CONVERSATION MANAGEMENT
-- Tạo trước nhóm 2.3 vì Tasks tham chiếu Conversation và Message.
-- ==========================================================================
CREATE TABLE conversations (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    title VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE messages (
    id VARCHAR(64) PRIMARY KEY,
    conversation_id VARCHAR(64) NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    sender_by message_sender NOT NULL,
    message TEXT NOT NULL CHECK (length(btrim(message)) > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================================================
-- 2.3 AI EXECUTION MANAGEMENT
-- ==========================================================================
CREATE TABLE tasks (
    id VARCHAR(64) PRIMARY KEY,
    conversation_id VARCHAR(64) NOT NULL REFERENCES conversations(id) ON DELETE RESTRICT,
    source_message_id VARCHAR(64) NOT NULL UNIQUE REFERENCES messages(id) ON DELETE RESTRICT,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    input_message TEXT NOT NULL CHECK (length(btrim(input_message)) > 0),
    status task_status NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ
);

CREATE TABLE task_operations (
    id VARCHAR(64) PRIMARY KEY,
    task_id VARCHAR(64) NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    intent VARCHAR(100) NOT NULL,
    display_order INTEGER NOT NULL CHECK (display_order > 0),
    status operation_status NOT NULL DEFAULT 'PENDING',
    parameters JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    CONSTRAINT uq_task_operations_order UNIQUE (task_id, display_order)
);

CREATE TABLE operation_dependencies (
    id VARCHAR(64) PRIMARY KEY,
    operation_id VARCHAR(64) NOT NULL REFERENCES task_operations(id) ON DELETE CASCADE,
    depends_on_operation_id VARCHAR(64) NOT NULL REFERENCES task_operations(id) ON DELETE CASCADE,
    dependency_type dependency_type NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_operation_dependency UNIQUE (operation_id, depends_on_operation_id),
    CONSTRAINT ck_operation_not_self_dependent CHECK (operation_id <> depends_on_operation_id)
);

CREATE TABLE task_operation_devices (
    id VARCHAR(64) PRIMARY KEY,
    operation_id VARCHAR(64) NOT NULL REFERENCES task_operations(id) ON DELETE CASCADE,
    device_id VARCHAR(64) NOT NULL REFERENCES devices(id) ON DELETE RESTRICT,
    status operation_device_status NOT NULL DEFAULT 'PENDING',
    device_role device_role NOT NULL,
    access_mode access_mode NOT NULL,
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    CONSTRAINT uq_operation_device UNIQUE (operation_id, device_id)
);

CREATE TABLE task_executions (
    id VARCHAR(64) PRIMARY KEY,
    task_id VARCHAR(64) NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    operation_id VARCHAR(64) REFERENCES task_operations(id) ON DELETE SET NULL,
    operation_device_id VARCHAR(64) REFERENCES task_operation_devices(id) ON DELETE SET NULL,
    agent_name VARCHAR(100) NOT NULL,
    tool_name VARCHAR(100),
    step_order INTEGER NOT NULL CHECK (step_order > 0),
    input JSONB,
    output JSONB,
    status execution_status NOT NULL DEFAULT 'PENDING',
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    duration_ms BIGINT CHECK (duration_ms IS NULL OR duration_ms >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Extension cho chiến thuật rollback: một device mapping có một ChangeSet được
-- human duyệt, chứa cả forward plan lẫn rollback plan trước khi WRITE.
CREATE TABLE device_change_sets (
    id VARCHAR(64) PRIMARY KEY,
    operation_device_id VARCHAR(64) NOT NULL UNIQUE
        REFERENCES task_operation_devices(id) ON DELETE CASCADE,
    strategy change_set_strategy NOT NULL DEFAULT 'COMPENSATING_COMMANDS',
    pre_change_snapshot TEXT NOT NULL,
    snapshot_checksum VARCHAR(128),
    planned_commands JSONB NOT NULL,
    rollback_commands JSONB NOT NULL,
    verification_checks JSONB NOT NULL,
    status change_set_status NOT NULL DEFAULT 'PLANNED',
    approved_by VARCHAR(64) REFERENCES users(id) ON DELETE RESTRICT,
    approved_at TIMESTAMPTZ,
    applied_at TIMESTAMPTZ,
    rolled_back_at TIMESTAMPTZ,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_change_set_commands_are_arrays CHECK (
        jsonb_typeof(planned_commands) = 'array'
        AND jsonb_typeof(rollback_commands) = 'array'
        AND jsonb_typeof(verification_checks) = 'array'
    )
);

CREATE TABLE device_action_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id VARCHAR(64) NOT NULL REFERENCES tasks(id) ON DELETE RESTRICT,
    operation_id VARCHAR(64) NOT NULL REFERENCES task_operations(id) ON DELETE RESTRICT,
    operation_device_id VARCHAR(64) NOT NULL REFERENCES task_operation_devices(id) ON DELETE RESTRICT,
    execution_id VARCHAR(64) NOT NULL REFERENCES task_executions(id) ON DELETE RESTRICT,
    device_id VARCHAR(64) NOT NULL REFERENCES devices(id) ON DELETE RESTRICT,
    change_set_id VARCHAR(64) REFERENCES device_change_sets(id) ON DELETE SET NULL,
    rollback_of_action_id UUID REFERENCES device_action_logs(id) ON DELETE SET NULL,
    action_type device_action_type NOT NULL DEFAULT 'READ',
    sequence_number INTEGER NOT NULL DEFAULT 1 CHECK (sequence_number > 0),
    command TEXT NOT NULL,
    result TEXT,
    status device_action_status NOT NULL,
    error_message TEXT,
    executed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================================================
-- INDEXES FOR COMMON LOOKUPS
-- ==========================================================================
CREATE INDEX idx_users_role_id ON users(role_id);
CREATE INDEX idx_devices_credential_id ON devices(credential_id);
CREATE INDEX idx_devices_brand_category ON devices(brand_id, category_id);
CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_messages_conversation_created ON messages(conversation_id, created_at);
CREATE INDEX idx_tasks_user_created ON tasks(user_id, created_at);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_task_operations_task_status ON task_operations(task_id, status);
CREATE INDEX idx_operation_dependencies_operation ON operation_dependencies(operation_id);
CREATE INDEX idx_operation_devices_status ON task_operation_devices(operation_id, status);
CREATE INDEX idx_task_executions_task_operation ON task_executions(task_id, operation_id);
CREATE INDEX idx_device_action_logs_device_time ON device_action_logs(device_id, executed_at);
CREATE INDEX idx_device_action_logs_task ON device_action_logs(task_id);

-- Dependency phải nằm trong cùng Task và không được tạo chu trình DAG.
CREATE OR REPLACE FUNCTION validate_operation_dependency()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    operation_task_id VARCHAR(64);
    dependency_task_id VARCHAR(64);
BEGIN
    SELECT task_id INTO operation_task_id
    FROM task_operations WHERE id = NEW.operation_id;

    SELECT task_id INTO dependency_task_id
    FROM task_operations WHERE id = NEW.depends_on_operation_id;

    IF operation_task_id IS DISTINCT FROM dependency_task_id THEN
        RAISE EXCEPTION 'Operations in a dependency must belong to the same task';
    END IF;

    IF EXISTS (
        WITH RECURSIVE ancestors(operation_id) AS (
            SELECT od.depends_on_operation_id
            FROM operation_dependencies od
            WHERE od.operation_id = NEW.depends_on_operation_id
              AND od.id <> NEW.id
            UNION
            SELECT od.depends_on_operation_id
            FROM operation_dependencies od
            JOIN ancestors a ON od.operation_id = a.operation_id
            WHERE od.id <> NEW.id
        )
        SELECT 1 FROM ancestors WHERE operation_id = NEW.operation_id
    ) THEN
        RAISE EXCEPTION 'Operation dependency would create a cycle';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_validate_operation_dependency
BEFORE INSERT OR UPDATE ON operation_dependencies
FOR EACH ROW EXECUTE FUNCTION validate_operation_dependency();

COMMIT;
