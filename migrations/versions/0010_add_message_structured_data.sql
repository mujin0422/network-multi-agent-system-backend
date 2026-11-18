-- Lưu payload máy đọc được của phản hồi Agent (ví dụ configuration proposals).
ALTER TABLE messages
    ADD COLUMN IF NOT EXISTS structured_data JSONB;

