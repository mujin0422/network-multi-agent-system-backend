-- Cho phép timeline hiển thị giai đoạn Configuration Agent sinh CLI WRITE.
ALTER TYPE activity_actor_type
    ADD VALUE IF NOT EXISTS 'CONFIGURATION';

ALTER TYPE activity_event_type
    ADD VALUE IF NOT EXISTS 'CONFIGURATION_STARTED';

ALTER TYPE activity_event_type
    ADD VALUE IF NOT EXISTS 'CONFIGURATION_COMPLETED';
