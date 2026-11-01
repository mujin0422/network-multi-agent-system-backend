-- Quản lý benchmark scenario và lịch sử chạy trong PostgreSQL.
BEGIN;

CREATE TABLE benchmark_scenarios (
    id VARCHAR(64) PRIMARY KEY,
    version VARCHAR(30) NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    topology VARCHAR(100) NOT NULL,
    initial_message TEXT NOT NULL,
    definition JSONB NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_by VARCHAR(64) REFERENCES users(id) ON DELETE SET NULL,
    last_updated_by VARCHAR(64) REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_benchmark_scenario_definition CHECK (
        jsonb_typeof(definition) = 'object'
        AND definition ?& ARRAY[
            'preconditions', 'injection', 'fault_verification', 'ground_truth',
            'evaluation_required_terms', 'cleanup'
        ]
    ),
    CONSTRAINT ck_benchmark_scenario_time CHECK (last_updated_at >= created_at)
);

CREATE TABLE benchmark_runs (
    id VARCHAR(64) PRIMARY KEY,
    scenario_id VARCHAR(64) NOT NULL
        REFERENCES benchmark_scenarios(id) ON DELETE RESTRICT,
    scenario_version VARCHAR(30) NOT NULL,
    scenario_name VARCHAR(100) NOT NULL,
    scenario_snapshot JSONB NOT NULL,
    status VARCHAR(20) NOT NULL,
    started_by VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    initial_message TEXT NOT NULL,
    conversation_id VARCHAR(64) REFERENCES conversations(id) ON DELETE SET NULL,
    source_message_id VARCHAR(64) REFERENCES messages(id) ON DELETE SET NULL,
    task_id VARCHAR(64) REFERENCES tasks(id) ON DELETE SET NULL,
    evaluation_id UUID REFERENCES task_evaluations(id) ON DELETE SET NULL,
    evaluation_result VARCHAR(30),
    cleanup_required BOOLEAN NOT NULL DEFAULT FALSE,
    error_message TEXT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    cleaned_at TIMESTAMPTZ,
    CONSTRAINT ck_benchmark_run_status CHECK (
        status IN ('PREPARING', 'READY', 'RUNNING', 'COMPLETED', 'FAILED', 'CLEANED')
    ),
    CONSTRAINT ck_benchmark_run_snapshot CHECK (jsonb_typeof(scenario_snapshot) = 'object'),
    CONSTRAINT ck_benchmark_run_time CHECK (
        (completed_at IS NULL OR completed_at >= started_at)
        AND (cleaned_at IS NULL OR cleaned_at >= started_at)
    )
);

CREATE INDEX idx_benchmark_scenarios_active_name
    ON benchmark_scenarios(is_active, name);
CREATE INDEX idx_benchmark_runs_scenario_time
    ON benchmark_runs(scenario_id, started_at DESC);
CREATE INDEX idx_benchmark_runs_status_time
    ON benchmark_runs(status, started_at DESC);

INSERT INTO benchmark_scenarios (
    id, version, name, description, topology, initial_message, definition
) VALUES (
    'p3-interface-link-down',
    '1.0',
    'P3 interface link-down diagnosis',
    'Chẩn đoán liên kết FastEthernet0/0 trên P3 bị tắt trong topology MPLS GNS3.',
    'mpls-core',
    'Hãy chẩn đoán nguyên nhân khiến thiết bị P3 mất kết nối trên liên kết FastEthernet0/0. Chỉ thu thập dữ liệu và xác định nguyên nhân, không khắc phục.',
    '{
      "preconditions": [{"device":"P3","command":"show interfaces FastEthernet0/0 | include line protocol","assertion":{"contains":"FastEthernet0/0 is up, line protocol is up"}}],
      "injection": [{"device":"P3","action":"interface_shutdown","interface":"FastEthernet0/0"}],
      "fault_verification": [{"device":"P3","command":"show interfaces FastEthernet0/0 | include line protocol","assertion":{"contains":"FastEthernet0/0 is administratively down"}}],
      "ground_truth": [{"fault_type":"link_down","device":"P3","interface":"FastEthernet0/0"}],
      "evaluation_required_terms": ["P3","FastEthernet0/0","down"],
      "cleanup": [{"device":"P3","action":"interface_no_shutdown","interface":"FastEthernet0/0"}]
    }'::jsonb
);

COMMIT;
