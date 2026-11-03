-- Extend existing PostgreSQL enum to persist quantitative benchmark metrics.
-- New values are used only after the migration transaction has committed.
ALTER TYPE evaluation_metric_type ADD VALUE IF NOT EXISTS 'LATENCY';
ALTER TYPE evaluation_metric_type ADD VALUE IF NOT EXISTS 'INTERACTION_TURNS';
