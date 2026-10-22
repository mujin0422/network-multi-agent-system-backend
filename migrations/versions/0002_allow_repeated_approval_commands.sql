-- Ordered CLI commands may repeat in different interface/configuration contexts.
CREATE OR REPLACE FUNCTION is_nonempty_jsonb_text_array(value JSONB)
RETURNS BOOLEAN
LANGUAGE sql
IMMUTABLE
STRICT
AS $$
    SELECT CASE WHEN jsonb_typeof(value) = 'array' THEN
        jsonb_array_length(value) > 0
        AND NOT EXISTS (
            SELECT 1
            FROM jsonb_array_elements(value) AS item
            WHERE jsonb_typeof(item) <> 'string'
               OR btrim(item #>> '{}') = ''
        )
    ELSE FALSE END;
$$;

ALTER TABLE operation_device_approvals
    DROP CONSTRAINT ck_operation_device_approval_commands;

ALTER TABLE operation_device_approvals
    ADD CONSTRAINT ck_operation_device_approval_commands
    CHECK (is_nonempty_jsonb_text_array(commands_snapshot));
