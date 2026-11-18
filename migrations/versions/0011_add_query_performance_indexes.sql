-- Composite indexes aligned with the API's filtering, ordering and cursor paths.

CREATE INDEX IF NOT EXISTS idx_conversations_user_updated
    ON conversations(user_id, last_updated_at DESC, id DESC);

CREATE INDEX IF NOT EXISTS idx_messages_conversation_created
    ON messages(conversation_id, created_at DESC, id DESC);

CREATE INDEX IF NOT EXISTS idx_tasks_user_created
    ON tasks(user_id, created_at DESC, id DESC);

CREATE INDEX IF NOT EXISTS idx_tasks_conversation_created
    ON tasks(conversation_id, created_at DESC, id DESC);

CREATE INDEX IF NOT EXISTS idx_tasks_status_created
    ON tasks(task_status, created_at DESC, id DESC);

CREATE INDEX IF NOT EXISTS idx_task_executions_task_created
    ON task_executions(task_id, created_at, id);

CREATE INDEX IF NOT EXISTS idx_device_action_logs_task_executed
    ON device_action_logs(task_id, executed_at, sequence_number, id);

CREATE INDEX IF NOT EXISTS idx_device_action_logs_executed
    ON device_action_logs(executed_at DESC, id DESC);

CREATE INDEX IF NOT EXISTS idx_devices_brand_created
    ON devices(brand_id, created_at DESC, id DESC);

CREATE INDEX IF NOT EXISTS idx_devices_category_created
    ON devices(category_id, created_at DESC, id DESC);

CREATE UNIQUE INDEX IF NOT EXISTS idx_devices_hostname_lower
    ON devices(lower(hostname));

CREATE INDEX IF NOT EXISTS idx_benchmark_runs_started
    ON benchmark_runs(started_at DESC, id DESC);

CREATE INDEX IF NOT EXISTS idx_benchmark_runs_source_message
    ON benchmark_runs(source_message_id)
    WHERE source_message_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_benchmark_scenarios_name
    ON benchmark_scenarios(name, id);

CREATE INDEX IF NOT EXISTS idx_task_evaluations_created
    ON task_evaluations(created_at DESC, id DESC);

CREATE INDEX IF NOT EXISTS idx_pending_approvals_expiry
    ON operation_device_approvals(expires_at)
    WHERE approval_status = 'PENDING' AND expires_at IS NOT NULL;
