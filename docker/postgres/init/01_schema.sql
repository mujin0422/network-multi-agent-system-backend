\set ON_ERROR_STOP on

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- =============================================================================
-- ENUM TYPES
-- =============================================================================
CREATE TYPE user_status AS ENUM ('ACTIVE', 'DISABLED');
CREATE TYPE message_sender AS ENUM ('USER', 'AGENT');
CREATE TYPE task_status AS ENUM (
    'PENDING', 'PLANNING', 'RUNNING', 'SUCCESS',
    'PARTIAL_SUCCESS', 'FAILED', 'REJECTED'
);
CREATE TYPE task_type AS ENUM (
    'UNCLASSIFIED', 'INFORMATION_RETRIEVAL', 'DIAGNOSIS',
    'CONFIGURATION', 'REMEDIATION', 'COMPOSITE'
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
CREATE TYPE device_action_status AS ENUM ('SUCCESS', 'FAILED', 'UNKNOWN');
CREATE TYPE device_action_type AS ENUM ('READ', 'WRITE');
CREATE TYPE device_action_phase AS ENUM (
    'READ', 'PRE_CHECK', 'APPLY', 'POST_CHECK', 'ROLLBACK', 'ROLLBACK_VERIFY'
);
CREATE TYPE evaluation_status AS ENUM ('PENDING', 'COMPLETED', 'ERROR');
CREATE TYPE evaluation_result AS ENUM ('PASS', 'FAIL', 'UNKNOWN', 'NOT_APPLICABLE');
CREATE TYPE evaluator_type AS ENUM ('AUTOMATED', 'HUMAN');

-- PostgreSQL CHECK không nhận subquery trực tiếp. Helper immutable này dùng để
-- bảo đảm danh sách driver JSONB chỉ chứa string duy nhất, không có phần tử rỗng.
CREATE FUNCTION is_unique_nonempty_jsonb_text_array(value JSONB)
RETURNS BOOLEAN
LANGUAGE sql
IMMUTABLE
STRICT
AS $$
    SELECT jsonb_typeof(value) = 'array'
       AND NOT EXISTS (
           SELECT 1
           FROM jsonb_array_elements(value) AS item
           WHERE jsonb_typeof(item) <> 'string'
              OR btrim(item #>> '{}') = ''
       )
       AND (
           SELECT count(*) = count(DISTINCT item #>> '{}')
           FROM jsonb_array_elements(value) AS item
       );
$$;

-- =============================================================================
-- 2.1 AUTHENTICATION & AUTHORIZATION
-- =============================================================================
-- Hai FK audit của roles được thêm sau users để giải quyết vòng tham chiếu
-- roles.created_by -> users.id -> roles.id.
CREATE TABLE roles (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    created_by VARCHAR(64),
    last_updated_by VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_updated_at TIMESTAMPTZ,
    CONSTRAINT ck_roles_updated_at CHECK (
        last_updated_at IS NULL OR last_updated_at >= created_at
    )
);

CREATE TABLE management_functions (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE actions (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE permissions (
    id VARCHAR(64) PRIMARY KEY,
    function_id VARCHAR(64) NOT NULL
        REFERENCES management_functions(id) ON DELETE RESTRICT,
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
    password_hash TEXT NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    user_status user_status NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_updated_at TIMESTAMPTZ,
    last_login_at TIMESTAMPTZ,
    CONSTRAINT ck_users_email CHECK (
        email = lower(email)
        AND email ~ '^[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}$'
    ),
    CONSTRAINT ck_users_updated_at CHECK (
        last_updated_at IS NULL OR last_updated_at >= created_at
    ),
    CONSTRAINT ck_users_last_login_at CHECK (
        last_login_at IS NULL OR last_login_at >= created_at
    )
);

ALTER TABLE roles
    ADD CONSTRAINT fk_roles_created_by
        FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL,
    ADD CONSTRAINT fk_roles_last_updated_by
        FOREIGN KEY (last_updated_by) REFERENCES users(id) ON DELETE SET NULL;

CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    refresh_token_hash TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMPTZ,
    CONSTRAINT ck_user_sessions_expires_at CHECK (expires_at > created_at),
    CONSTRAINT ck_user_sessions_revoked_at CHECK (
        revoked_at IS NULL OR revoked_at >= created_at
    )
);

-- =============================================================================
-- 2.2 NETWORK INVENTORY
-- Password/secret là ASCII-armored PGP ciphertext. Khóa giải mã luôn nằm ngoài
-- database và chỉ được backend đưa vào đúng lúc thiết lập kết nối thiết bị.
-- =============================================================================
CREATE TABLE categories (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE brands (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    supported_drivers JSONB NOT NULL DEFAULT '[]'::jsonb,
    CONSTRAINT ck_brands_supported_drivers
        CHECK (is_unique_nonempty_jsonb_text_array(supported_drivers))
);

CREATE TABLE credentials (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(150) NOT NULL UNIQUE,
    description TEXT,
    username VARCHAR(255) NOT NULL,
    password TEXT NOT NULL,
    secret TEXT,
    encryption_type VARCHAR(100) NOT NULL,
    created_by VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    last_updated_by VARCHAR(64) REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_credentials_updated_at CHECK (last_updated_at >= created_at)
);

CREATE TABLE devices (
    id VARCHAR(64) PRIMARY KEY,
    credential_id VARCHAR(64) REFERENCES credentials(id) ON DELETE SET NULL,
    brand_id VARCHAR(64) NOT NULL REFERENCES brands(id) ON DELETE RESTRICT,
    category_id VARCHAR(64) NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
    created_by VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    last_updated_by VARCHAR(64) REFERENCES users(id) ON DELETE RESTRICT,
    hostname VARCHAR(255) NOT NULL UNIQUE,
    host VARCHAR(255) NOT NULL DEFAULT '127.0.0.1',
    port INTEGER NOT NULL CHECK (port BETWEEN 1 AND 65535),
    device_type VARCHAR(100) NOT NULL,
    location VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_devices_host_port UNIQUE (host, port),
    CONSTRAINT ck_devices_updated_at CHECK (last_updated_at >= created_at)
);

CREATE FUNCTION validate_device_driver()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM brands b
        WHERE b.id = NEW.brand_id
          AND b.supported_drivers ? NEW.device_type
    ) THEN
        RAISE EXCEPTION 'Driver % is not supported by brand %',
            NEW.device_type, NEW.brand_id;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_validate_device_driver
BEFORE INSERT OR UPDATE OF brand_id, device_type ON devices
FOR EACH ROW EXECUTE FUNCTION validate_device_driver();

-- =============================================================================
-- 2.4 CONVERSATION MANAGEMENT
-- Tạo trước nhóm runtime vì tasks tham chiếu conversation và source message.
-- =============================================================================
CREATE TABLE conversations (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    title VARCHAR(255) NOT NULL CHECK (length(btrim(title)) > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_conversations_updated_at CHECK (last_updated_at >= created_at)
);

CREATE TABLE messages (
    id VARCHAR(64) PRIMARY KEY,
    conversation_id VARCHAR(64) NOT NULL
        REFERENCES conversations(id) ON DELETE CASCADE,
    sender_by message_sender NOT NULL,
    message TEXT NOT NULL CHECK (length(btrim(message)) > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE FUNCTION touch_conversation_after_message()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE conversations
       SET last_updated_at = GREATEST(last_updated_at, NEW.created_at)
     WHERE id = NEW.conversation_id;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_touch_conversation_after_message
AFTER INSERT ON messages
FOR EACH ROW EXECUTE FUNCTION touch_conversation_after_message();

-- =============================================================================
-- 2.3 AI EXECUTION MANAGEMENT
-- =============================================================================
CREATE TABLE tasks (
    id VARCHAR(64) PRIMARY KEY,
    conversation_id VARCHAR(64) NOT NULL
        REFERENCES conversations(id) ON DELETE RESTRICT,
    source_message_id VARCHAR(64) NOT NULL UNIQUE
        REFERENCES messages(id) ON DELETE RESTRICT,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    input_message TEXT NOT NULL CHECK (length(btrim(input_message)) > 0),
    task_status task_status NOT NULL DEFAULT 'PENDING',
    task_type task_type NOT NULL DEFAULT 'UNCLASSIFIED',
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_tasks_started_at CHECK (
        started_at IS NULL OR started_at >= created_at
    ),
    CONSTRAINT ck_tasks_completed_at CHECK (
        completed_at IS NULL
        OR (completed_at >= created_at
            AND (started_at IS NULL OR completed_at >= started_at))
    ),
    CONSTRAINT ck_tasks_lifecycle CHECK (
        (task_status = 'PENDING' AND started_at IS NULL AND completed_at IS NULL)
        OR (task_status IN ('PLANNING', 'RUNNING')
            AND started_at IS NOT NULL AND completed_at IS NULL)
        OR (task_status IN ('SUCCESS', 'PARTIAL_SUCCESS', 'FAILED', 'REJECTED')
            AND completed_at IS NOT NULL)
    )
);

CREATE FUNCTION validate_task_source()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    source_conversation_id VARCHAR(64);
    source_sender message_sender;
    source_message TEXT;
    conversation_user_id VARCHAR(64);
BEGIN
    SELECT conversation_id, sender_by, message
      INTO source_conversation_id, source_sender, source_message
      FROM messages
     WHERE id = NEW.source_message_id;
    SELECT user_id INTO conversation_user_id
      FROM conversations
     WHERE id = NEW.conversation_id;

    IF source_sender <> 'USER'
       OR source_conversation_id IS DISTINCT FROM NEW.conversation_id
       OR conversation_user_id IS DISTINCT FROM NEW.user_id
       OR source_message IS DISTINCT FROM NEW.input_message THEN
        RAISE EXCEPTION
            'Task source message, conversation, user, or input_message is inconsistent';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_validate_task_source
BEFORE INSERT OR UPDATE OF conversation_id, source_message_id, user_id, input_message
ON tasks FOR EACH ROW EXECUTE FUNCTION validate_task_source();

CREATE TABLE task_operations (
    id VARCHAR(64) PRIMARY KEY,
    task_id VARCHAR(64) NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    operation_intent VARCHAR(100) NOT NULL
        CHECK (length(btrim(operation_intent)) > 0),
    display_order INTEGER NOT NULL CHECK (display_order > 0),
    operation_status operation_status NOT NULL DEFAULT 'PENDING',
    operation_parameters JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    CONSTRAINT uq_task_operations_order UNIQUE (task_id, display_order),
    CONSTRAINT ck_task_operations_parameters_object
        CHECK (jsonb_typeof(operation_parameters) = 'object'),
    CONSTRAINT ck_task_operations_started_at CHECK (
        started_at IS NULL OR started_at >= created_at
    ),
    CONSTRAINT ck_task_operations_completed_at CHECK (
        completed_at IS NULL
        OR (completed_at >= created_at
            AND (started_at IS NULL OR completed_at >= started_at))
    ),
    CONSTRAINT ck_task_operations_lifecycle CHECK (
        (operation_status IN ('PENDING', 'WAITING_APPROVAL') AND completed_at IS NULL)
        OR (operation_status = 'RUNNING'
            AND started_at IS NOT NULL AND completed_at IS NULL)
        OR (operation_status IN (
                'SUCCESS', 'PARTIAL_SUCCESS', 'FAILED', 'REJECTED', 'SKIPPED'
            )
            AND completed_at IS NOT NULL)
    )
);

CREATE TABLE operation_dependencies (
    id VARCHAR(64) PRIMARY KEY,
    operation_id VARCHAR(64) NOT NULL
        REFERENCES task_operations(id) ON DELETE CASCADE,
    depends_on_operation_id VARCHAR(64) NOT NULL
        REFERENCES task_operations(id) ON DELETE CASCADE,
    dependency_type dependency_type NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_operation_dependency
        UNIQUE (operation_id, depends_on_operation_id),
    CONSTRAINT ck_operation_not_self_dependent
        CHECK (operation_id <> depends_on_operation_id)
);

CREATE TABLE task_operation_devices (
    id VARCHAR(64) PRIMARY KEY,
    operation_id VARCHAR(64) NOT NULL
        REFERENCES task_operations(id) ON DELETE CASCADE,
    device_id VARCHAR(64) NOT NULL REFERENCES devices(id) ON DELETE RESTRICT,
    operation_device_status operation_device_status NOT NULL DEFAULT 'PENDING',
    device_role device_role NOT NULL,
    access_mode access_mode NOT NULL,
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    CONSTRAINT uq_operation_device UNIQUE (operation_id, device_id),
    CONSTRAINT ck_operation_device_role_access CHECK (
        (device_role IN ('SOURCE', 'CONTEXT') AND access_mode = 'READ')
        OR device_role = 'TARGET'
    ),
    CONSTRAINT ck_operation_devices_time CHECK (
        completed_at IS NULL OR started_at IS NULL OR completed_at >= started_at
    ),
    CONSTRAINT ck_operation_devices_lifecycle CHECK (
        (operation_device_status IN ('PENDING', 'WAITING_APPROVAL', 'RUNNING')
            AND completed_at IS NULL)
        OR (operation_device_status IN ('SUCCESS', 'FAILED', 'REJECTED', 'SKIPPED')
            AND completed_at IS NOT NULL)
    ),
    CONSTRAINT ck_operation_devices_error CHECK (
        operation_device_status <> 'FAILED' OR length(btrim(error_message)) > 0
    )
);

CREATE TABLE task_executions (
    id VARCHAR(64) PRIMARY KEY,
    task_id VARCHAR(64) NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    operation_id VARCHAR(64) REFERENCES task_operations(id) ON DELETE SET NULL,
    operation_device_id VARCHAR(64)
        REFERENCES task_operation_devices(id) ON DELETE SET NULL,
    agent_name VARCHAR(100) NOT NULL CHECK (length(btrim(agent_name)) > 0),
    tool_name VARCHAR(100),
    step_order INTEGER NOT NULL CHECK (step_order > 0),
    input JSONB,
    output JSONB,
    execution_status execution_status NOT NULL DEFAULT 'PENDING',
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    duration_ms BIGINT CHECK (duration_ms IS NULL OR duration_ms >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_task_executions_time CHECK (
        completed_at IS NULL OR started_at IS NULL OR completed_at >= started_at
    ),
    CONSTRAINT ck_task_executions_lifecycle CHECK (
        (execution_status = 'PENDING'
            AND started_at IS NULL AND completed_at IS NULL)
        OR (execution_status = 'RUNNING'
            AND started_at IS NOT NULL AND completed_at IS NULL)
        OR (execution_status IN ('SUCCESS', 'FAILED')
            AND started_at IS NOT NULL AND completed_at IS NOT NULL)
    ),
    CONSTRAINT ck_task_executions_error CHECK (
        execution_status <> 'FAILED' OR length(btrim(error_message)) > 0
    )
);

CREATE TABLE device_action_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id VARCHAR(64) NOT NULL REFERENCES tasks(id) ON DELETE RESTRICT,
    operation_id VARCHAR(64) NOT NULL
        REFERENCES task_operations(id) ON DELETE RESTRICT,
    operation_device_id VARCHAR(64) NOT NULL
        REFERENCES task_operation_devices(id) ON DELETE RESTRICT,
    execution_id VARCHAR(64) NOT NULL
        REFERENCES task_executions(id) ON DELETE RESTRICT,
    device_id VARCHAR(64) NOT NULL REFERENCES devices(id) ON DELETE RESTRICT,
    rollback_of_action_id UUID
        REFERENCES device_action_logs(id) ON DELETE SET NULL,
    action_type device_action_type NOT NULL,
    action_phase device_action_phase NOT NULL DEFAULT 'READ',
    sequence_number INTEGER NOT NULL DEFAULT 1 CHECK (sequence_number > 0),
    command TEXT NOT NULL CHECK (length(btrim(command)) > 0),
    result TEXT,
    action_log_status device_action_status NOT NULL,
    error_message TEXT,
    executed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_device_action_type_phase CHECK (
        (action_type = 'READ' AND action_phase IN ('READ', 'PRE_CHECK',
                                                   'POST_CHECK', 'ROLLBACK_VERIFY'))
        OR (action_type = 'WRITE' AND action_phase IN ('APPLY', 'ROLLBACK'))
    ),
    CONSTRAINT ck_device_action_error CHECK (
        action_log_status <> 'FAILED' OR length(btrim(error_message)) > 0
    )
);

-- =============================================================================
-- 2.5 AI EVALUATION & BENCHMARKING
-- =============================================================================
CREATE TABLE task_evaluations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id VARCHAR(64) NOT NULL UNIQUE REFERENCES tasks(id) ON DELETE RESTRICT,
    evaluation_status evaluation_status NOT NULL DEFAULT 'PENDING',
    expected_outcome JSONB,
    actual_outcome JSONB,
    goal_result evaluation_result NOT NULL DEFAULT 'UNKNOWN',
    expected_root_cause JSONB,
    predicted_root_cause JSONB,
    rca_result evaluation_result NOT NULL DEFAULT 'NOT_APPLICABLE',
    remediation_required BOOLEAN NOT NULL DEFAULT FALSE,
    remediation_attempted BOOLEAN NOT NULL DEFAULT FALSE,
    remediation_result evaluation_result NOT NULL DEFAULT 'NOT_APPLICABLE',
    safety_result evaluation_result NOT NULL DEFAULT 'NOT_APPLICABLE',
    evaluation_evidence JSONB,
    evaluator_type evaluator_type NOT NULL,
    evaluator_version VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    evaluated_at TIMESTAMPTZ,
    CONSTRAINT ck_task_evaluations_time CHECK (
        evaluated_at IS NULL OR evaluated_at >= created_at
    ),
    CONSTRAINT ck_task_evaluations_lifecycle CHECK (
        (evaluation_status = 'PENDING' AND evaluated_at IS NULL)
        OR (evaluation_status IN ('COMPLETED', 'ERROR')
            AND evaluated_at IS NOT NULL)
    ),
    CONSTRAINT ck_task_evaluations_remediation CHECK (
        (remediation_required = FALSE
            AND remediation_attempted = FALSE
            AND remediation_result = 'NOT_APPLICABLE')
        OR remediation_required = TRUE
    )
);

-- =============================================================================
-- CROSS-TABLE CONSISTENCY TRIGGERS
-- =============================================================================
CREATE FUNCTION validate_operation_dependency()
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

CREATE FUNCTION validate_task_execution_links()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    linked_task_id VARCHAR(64);
    linked_operation_id VARCHAR(64);
BEGIN
    IF NEW.operation_id IS NOT NULL THEN
        SELECT task_id INTO linked_task_id
          FROM task_operations WHERE id = NEW.operation_id;
        IF linked_task_id IS DISTINCT FROM NEW.task_id THEN
            RAISE EXCEPTION 'Execution operation does not belong to its task';
        END IF;
    END IF;

    IF NEW.operation_device_id IS NOT NULL THEN
        IF NEW.operation_id IS NULL THEN
            RAISE EXCEPTION 'Device execution requires operation_id';
        END IF;
        SELECT operation_id INTO linked_operation_id
          FROM task_operation_devices WHERE id = NEW.operation_device_id;
        IF linked_operation_id IS DISTINCT FROM NEW.operation_id THEN
            RAISE EXCEPTION 'Execution device mapping does not belong to operation';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_validate_task_execution_links
BEFORE INSERT OR UPDATE OF task_id, operation_id, operation_device_id
ON task_executions FOR EACH ROW EXECUTE FUNCTION validate_task_execution_links();

CREATE FUNCTION validate_device_action_log()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    operation_task_id VARCHAR(64);
    mapping_operation_id VARCHAR(64);
    mapping_device_id VARCHAR(64);
    execution_task_id VARCHAR(64);
    execution_operation_id VARCHAR(64);
    execution_mapping_id VARCHAR(64);
BEGIN
    SELECT task_id INTO operation_task_id
      FROM task_operations WHERE id = NEW.operation_id;
    SELECT operation_id, device_id
      INTO mapping_operation_id, mapping_device_id
      FROM task_operation_devices WHERE id = NEW.operation_device_id;
    SELECT task_id, operation_id, operation_device_id
      INTO execution_task_id, execution_operation_id, execution_mapping_id
      FROM task_executions WHERE id = NEW.execution_id;

    IF operation_task_id IS DISTINCT FROM NEW.task_id
       OR mapping_operation_id IS DISTINCT FROM NEW.operation_id
       OR mapping_device_id IS DISTINCT FROM NEW.device_id
       OR execution_task_id IS DISTINCT FROM NEW.task_id
       OR execution_operation_id IS DISTINCT FROM NEW.operation_id
       OR execution_mapping_id IS DISTINCT FROM NEW.operation_device_id THEN
        RAISE EXCEPTION 'Device action log references inconsistent runtime entities';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_validate_device_action_log
BEFORE INSERT OR UPDATE ON device_action_logs
FOR EACH ROW EXECUTE FUNCTION validate_device_action_log();

CREATE FUNCTION validate_task_evaluation()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    evaluated_task_status task_status;
BEGIN
    SELECT task_status INTO evaluated_task_status
      FROM tasks WHERE id = NEW.task_id;
    IF evaluated_task_status NOT IN (
        'SUCCESS', 'PARTIAL_SUCCESS', 'FAILED', 'REJECTED'
    ) THEN
        RAISE EXCEPTION 'Only a terminal Task can be evaluated';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_validate_task_evaluation
BEFORE INSERT OR UPDATE OF task_id ON task_evaluations
FOR EACH ROW EXECUTE FUNCTION validate_task_evaluation();

-- =============================================================================
-- INDEXES FOR COMMON LOOKUPS
-- =============================================================================
CREATE INDEX idx_users_role_id ON users(role_id);
CREATE INDEX idx_users_status ON users(user_status);
CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_user_sessions_expires_at ON user_sessions(expires_at);
CREATE INDEX idx_permissions_action_id ON permissions(action_id);
CREATE INDEX idx_role_permissions_permission_id ON role_permissions(permission_id);
CREATE INDEX idx_credentials_username ON credentials(username);
CREATE INDEX idx_credentials_created_by ON credentials(created_by);
CREATE INDEX idx_devices_credential_id ON devices(credential_id);
CREATE INDEX idx_devices_brand_id ON devices(brand_id);
CREATE INDEX idx_devices_category_id ON devices(category_id);
CREATE INDEX idx_conversations_user_updated
    ON conversations(user_id, last_updated_at DESC);
CREATE INDEX idx_messages_conversation_created
    ON messages(conversation_id, created_at);
CREATE INDEX idx_tasks_conversation_id ON tasks(conversation_id);
CREATE INDEX idx_tasks_user_created ON tasks(user_id, created_at DESC);
CREATE INDEX idx_tasks_status ON tasks(task_status);
CREATE INDEX idx_tasks_type ON tasks(task_type);
CREATE INDEX idx_task_operations_task_status
    ON task_operations(task_id, operation_status);
CREATE INDEX idx_operation_dependencies_operation
    ON operation_dependencies(operation_id);
CREATE INDEX idx_operation_dependencies_parent
    ON operation_dependencies(depends_on_operation_id);
CREATE INDEX idx_operation_devices_operation_status
    ON task_operation_devices(operation_id, operation_device_status);
CREATE INDEX idx_operation_devices_device_id
    ON task_operation_devices(device_id);
CREATE INDEX idx_task_executions_task_operation
    ON task_executions(task_id, operation_id);
CREATE INDEX idx_task_executions_operation_device
    ON task_executions(operation_device_id);
CREATE INDEX idx_task_executions_agent_status
    ON task_executions(agent_name, execution_status);
CREATE INDEX idx_device_action_logs_device_time
    ON device_action_logs(device_id, executed_at DESC);
CREATE INDEX idx_device_action_logs_task ON device_action_logs(task_id);
CREATE INDEX idx_device_action_logs_execution ON device_action_logs(execution_id);
CREATE INDEX idx_device_action_logs_action_type ON device_action_logs(action_type);
CREATE INDEX idx_task_evaluations_status
    ON task_evaluations(evaluation_status);

COMMIT;
