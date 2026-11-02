-- Chuẩn hóa ID benchmark và tách khóa nghiệp vụ của scenario khỏi primary key.
BEGIN;

ALTER TABLE benchmark_scenarios
    ADD COLUMN scenario_key VARCHAR(100);

CREATE TEMP TABLE benchmark_scenario_id_mapping ON COMMIT DROP AS
SELECT
    id AS old_id,
    'benc-' || to_char(created_at AT TIME ZONE 'UTC', 'DDMMYY') || '-' ||
        substr(md5(id || random()::text), 1, 8) AS new_id
FROM benchmark_scenarios;

UPDATE benchmark_scenarios AS scenario
SET scenario_key = mapping.old_id
FROM benchmark_scenario_id_mapping AS mapping
WHERE scenario.id = mapping.old_id;

ALTER TABLE benchmark_runs
    DROP CONSTRAINT benchmark_runs_scenario_id_fkey;

UPDATE benchmark_scenarios AS scenario
SET id = mapping.new_id
FROM benchmark_scenario_id_mapping AS mapping
WHERE scenario.id = mapping.old_id;

UPDATE benchmark_runs AS run
SET
    scenario_id = mapping.new_id,
    scenario_snapshot =
        (run.scenario_snapshot - 'id' - 'scenario_key') ||
        jsonb_build_object('scenario_key', mapping.old_id)
FROM benchmark_scenario_id_mapping AS mapping
WHERE run.scenario_id = mapping.old_id;

CREATE TEMP TABLE benchmark_run_id_mapping ON COMMIT DROP AS
SELECT
    id AS old_id,
    'benr-' || to_char(started_at AT TIME ZONE 'UTC', 'DDMMYY') || '-' ||
        substr(md5(id || random()::text), 1, 8) AS new_id
FROM benchmark_runs
WHERE id NOT LIKE 'benr-%';

UPDATE benchmark_runs AS run
SET id = mapping.new_id
FROM benchmark_run_id_mapping AS mapping
WHERE run.id = mapping.old_id;

UPDATE task_evaluation_metrics AS metric
SET evidence = jsonb_set(
    metric.evidence,
    '{benchmark_run_id}',
    to_jsonb(mapping.new_id)
)
FROM benchmark_run_id_mapping AS mapping
WHERE metric.evidence ->> 'benchmark_run_id' = mapping.old_id;

ALTER TABLE benchmark_scenarios
    ALTER COLUMN scenario_key SET NOT NULL,
    ADD CONSTRAINT uq_benchmark_scenarios_scenario_key UNIQUE (scenario_key),
    ADD CONSTRAINT ck_benchmark_scenario_id_format
        CHECK (id ~ '^benc-[0-9]{6}-[0-9a-f]{8}$'),
    ADD CONSTRAINT ck_benchmark_scenario_key_format
        CHECK (scenario_key ~ '^[a-z0-9][a-z0-9-]*$');

ALTER TABLE benchmark_runs
    ADD CONSTRAINT benchmark_runs_scenario_id_fkey
        FOREIGN KEY (scenario_id)
        REFERENCES benchmark_scenarios(id)
        ON DELETE RESTRICT,
    ADD CONSTRAINT ck_benchmark_run_id_format
        CHECK (id ~ '^benr-[0-9]{6}-[0-9a-f]{8}$');

COMMIT;
