-- Chuẩn hóa mỗi tiêu chí đánh giá thành một bản ghi metric độc lập.
BEGIN;

CREATE TYPE evaluation_metric_type AS ENUM (
    'GOAL', 'RCA', 'REMEDIATION', 'SAFETY'
);

CREATE TABLE task_evaluation_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    evaluation_id UUID NOT NULL
        REFERENCES task_evaluations(id) ON DELETE CASCADE,
    metric_type evaluation_metric_type NOT NULL,
    result evaluation_result NOT NULL DEFAULT 'UNKNOWN',
    is_required BOOLEAN NOT NULL DEFAULT TRUE,
    was_attempted BOOLEAN,
    expected_value JSONB,
    actual_value JSONB,
    evidence JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_task_evaluation_metric_type
        UNIQUE (evaluation_id, metric_type),
    CONSTRAINT ck_task_evaluation_metric_attempted CHECK (
        metric_type = 'REMEDIATION' OR was_attempted IS NULL
    )
);

INSERT INTO task_evaluation_metrics (
    evaluation_id, metric_type, result, is_required,
    expected_value, actual_value, evidence, created_at
)
SELECT id, 'GOAL', goal_result, TRUE,
       expected_outcome, actual_outcome, evaluation_evidence, created_at
  FROM task_evaluations;

INSERT INTO task_evaluation_metrics (
    evaluation_id, metric_type, result, is_required,
    expected_value, actual_value, evidence, created_at
)
SELECT id, 'RCA', rca_result, rca_result <> 'NOT_APPLICABLE',
       expected_root_cause, predicted_root_cause, evaluation_evidence, created_at
  FROM task_evaluations;

INSERT INTO task_evaluation_metrics (
    evaluation_id, metric_type, result, is_required, was_attempted,
    expected_value, actual_value, evidence, created_at
)
SELECT id, 'REMEDIATION', remediation_result, remediation_required,
       remediation_attempted,
       jsonb_build_object('required', remediation_required),
       jsonb_build_object('attempted', remediation_attempted),
       evaluation_evidence, created_at
  FROM task_evaluations;

INSERT INTO task_evaluation_metrics (
    evaluation_id, metric_type, result, is_required,
    evidence, created_at
)
SELECT id, 'SAFETY', safety_result, safety_result <> 'NOT_APPLICABLE',
       evaluation_evidence, created_at
  FROM task_evaluations;

ALTER TABLE task_evaluations
    DROP CONSTRAINT ck_task_evaluations_remediation,
    DROP COLUMN expected_outcome,
    DROP COLUMN actual_outcome,
    DROP COLUMN goal_result,
    DROP COLUMN expected_root_cause,
    DROP COLUMN predicted_root_cause,
    DROP COLUMN rca_result,
    DROP COLUMN remediation_required,
    DROP COLUMN remediation_attempted,
    DROP COLUMN remediation_result,
    DROP COLUMN safety_result,
    DROP COLUMN evaluation_evidence;

CREATE INDEX idx_task_evaluation_metrics_type_result
    ON task_evaluation_metrics(metric_type, result);
CREATE INDEX idx_task_evaluation_metrics_evaluation
    ON task_evaluation_metrics(evaluation_id);

COMMIT;
