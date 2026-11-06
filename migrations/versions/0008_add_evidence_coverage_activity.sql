-- Cho phép lưu quyết định evidence coverage gate trong task timeline.
ALTER TYPE activity_event_type
    ADD VALUE IF NOT EXISTS 'EVIDENCE_COVERAGE_EVALUATED';
