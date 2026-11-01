# System Audit Domain

Domain này quản lý `audit_logs`, là lịch sử bất biến của các hành động quản trị
và sự kiện nghiệp vụ quan trọng trong hệ thống.

## Phạm vi

- `schemas`: contract ghi log nội bộ và response chỉ đọc.
- `models`: ánh xạ bảng `audit_logs`.
- `repositories`: insert và truy vấn có bộ lọc; không có update/delete.
- `services`: sinh UUID/thời gian ở Backend và cung cấp use case tra cứu.
- `routers`: API danh sách và chi tiết, yêu cầu quyền `Audit Log + View`.

## API

- `GET /api/v1/audit-logs/`: lọc theo actor, action, resource, status và thời gian.
- `GET /api/v1/audit-logs/{audit_log_id}`: xem một bản ghi theo UUID.
- `GET /api/v1/device-action-logs/`: lịch sử command thực tế trên thiết bị;
  endpoint này thuộc Execution domain và không phải system audit log.

API không cho phép client tạo, sửa hoặc xóa audit log. Các use case nội bộ gọi
`AuditLogService.record()` sau khi hành động nghiệp vụ đã có kết quả xác định.

## Quy tắc bảo mật

- Actor USER phải lấy từ identity đã xác thực.
- Không ghi password, token, secret, credential hoặc Authorization header.
- `event_data` chỉ chứa metadata tối thiểu cần cho truy vết.
- Bản ghi chỉ được append; retention/archive là quy trình quản trị riêng.
