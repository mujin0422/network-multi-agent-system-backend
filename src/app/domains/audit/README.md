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

## Tự động ghi audit cho API nghiệp vụ

`AuditCaptureMiddleware` đăng ký tại `app/main.py`, ghi event **sau khi**
request hoàn tất. Mỗi action được ánh xạ tường minh trong
`app/domains/audit/http_capture.py::AUDITED_ROUTES`.

Các nhóm đã kết nối:

- Authentication: login, refresh, logout (bao gồm kết quả thất bại/từ chối).
- Identity: tạo/sửa User, Role, và cập nhật ma trận Permission.
- Inventory: tạo/sửa Device, Credential, Brand.
- Conversation/Task: tạo Conversation/Message, đổi title, tạo Task/Operation.
- Benchmarks: tạo/sửa Scenario, bắt đầu/cleanup Run.
- Approval: phê duyệt, từ chối (không lưu command snapshot).
- Worker timeout: event `APPROVAL_TIMEOUT` ghi cùng transaction kết thúc Task.

Bản ghi ghi `action`, `resource_type`, `resource_id` (nếu biết),
`event_status`, actor từ backend-auth, IP, thời điểm UTC, HTTP status,
tên route chuẩn hóa và correlation UUID hợp lệ từ `X-Request-ID`.
Không lưu request/response body, query params, Authorization header,
password, token, credential hoặc command. Client không thể tự POST audit.

Lưu ý:
- System Audit Log khác `task_activity_events` và `device_action_logs`.
- Những endpoint inventory **đã tồn tại trước đây và chưa có auth dependency**
  vẫn có thể được gọi không đăng nhập. Event của request không xác thực
  hiển thị `SYSTEM / Unauthenticated request`, không giả mạo người dùng.
  Khi có Bearer token hợp lệ, middleware kiểm tra token/session để gán User.
  Việc bắt buộc RBAC cho các endpoint cũ cần được triển khai riêng để tránh
  làm thay đổi HTTP contract ở đợt tích hợp audit này.
- Audit ghi bằng transaction riêng sau mutation. Nếu Audit DB không lưu được,
  backend ghi lỗi `SYSTEM AUDIT WRITE FAILED` vào server log và giữ HTTP
  response của nghiệp vụ đã commit. **Đây là best-effort audit**, chưa phải
  transactional audit đối với mọi CRUD. Trên production cần alert lỗi này và
  cân nhắc transactional outbox nếu có yêu cầu tuân thủ nghiêm ngặt.

## Kiểm thử

```bash
pytest tests/domains/test_audit.py tests/domains/test_audit_capture.py -q
```

Kiểm thử với PostgreSQL thật (không chạy trên lab sản xuất):

1. Chạy migration, đặc biệt `0003_add_system_audit_logs.sql`:
   `docker compose run --rm migrate`.
2. Khởi động lại API rồi đăng nhập bằng user có quyền `Audit Log / View`.
3. Tạo hoặc cập nhật một Device thử nghiệm qua giao diện.
4. Mở **Monitoring → Audit Logs**, nhấn reload trang.
   Tìm `DEVICE_CREATE` hoặc `DEVICE_UPDATE`, Actor, Resource ID, trạng thái SUCCESS.
5. Thử đăng nhập sai; tìm `AUTH_LOGIN` với `FAILED`. Không có password/token
   trong event_data hoặc Summary.
6. Dùng Swagger `GET /api/v1/audit-logs/?limit=20` với Bearer token đủ quyền
   để đối chiếu với dữ liệu trên frontend.

Nếu UI trống, xem log API, kết quả migration, RBAC permission và
`SYSTEM AUDIT WRITE FAILED`. Những log trước khi tính năng được triển khai
không được tạo lại tự động.
