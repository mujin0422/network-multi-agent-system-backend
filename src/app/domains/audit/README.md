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

API không cho phép client tạo, sửa hoặc xóa audit log. Trong luồng CRUD chính,
Service sử dụng `DatabaseUnitOfWork.begin()`, gọi phương thức repository
`save_in_session(session, ...)` và `record_audit_in_session(session, ...)`
trước khi kết thúc transaction. Helper này gọi
`AuditLogService.record_in_session(session, ...)` nhưng **không commit**.
**Cả nghiệp vụ và audit cùng COMMIT hoặc cùng ROLLBACK**.

Các repository/Service cũ chưa chuyển sang Unit of Work explicit vẫn dùng
`audit_mutation` và `append_audit_in_session` để tương thích. Đây là đường
chuyển tiếp, không phải kiến trúc khuyến nghị cho tính năng mới.
Xem [Unit of Work](../../../../docs/architecture/database-unit-of-work.md).

## Quy tắc bảo mật

- Actor USER phải lấy từ identity đã xác thực.
- Không ghi password, token, secret, credential hoặc Authorization header.
- `event_data` chỉ chứa metadata tối thiểu cần cho truy vết.
- Bản ghi chỉ được append; retention/archive là quy trình quản trị riêng.

## Tự động ghi audit cho API nghiệp vụ

Hai cơ chế có chủ đích khác nhau:

1. **Thành công của CRUD và approval:** Service khai báo event; repository ghi
   business row và audit row vào **cùng SQLAlchemy Session/transaction**.
   Ghi audit thất bại làm rollback cả business mutation. Không chấp nhận
   ghi thành công trên middleware (tránh log trùng).
2. **Đăng nhập, refresh, logout, Conversation và HTTP lỗi/từ chối:**
   `AuditCaptureMiddleware` ghi một audit event **độc lập** sau khi xử lý,
   vì login thất bại hoặc permission denied không có transaction nghiệp vụ
   thành công. Các luồng này chưa dùng chung transaction với audit.

Danh mục route được khai báo tường minh trong
`app/domains/audit/http_capture.py::AUDITED_ROUTES`, còn
`TRANSACTIONAL_ACTIONS` đánh dấu các route ghi audit nguyên tử.

Các nhóm đã kết nối:

- Authentication: login, refresh, logout (bao gồm kết quả thất bại/từ chối).
- Identity: tạo/sửa User, Role, và cập nhật ma trận Permission.
- Inventory: tạo/sửa Device, Credential, Brand.
- Conversation/Task: tạo Conversation/Message, đổi title, tạo Task/Operation.
- Benchmarks: tạo/sửa Scenario, bắt đầu/cleanup Run.
- Approval: phê duyệt, từ chối (không lưu command snapshot).
- Worker timeout: event `APPROVAL_TIMEOUT` ghi cùng transaction kết thúc Task.

Audit nguyên tử có `action`, `resource_type`, `resource_id`,
`event_status`, actor được xác thực và thời điểm UTC; không lưu HTTP body.
Audit độc lập do middleware ghi cho các trường hợp trên có thêm HTTP status,
route chuẩn hóa, IP và UUID hợp lệ từ `X-Request-ID`.
Không ghi request/response body, query params, Authorization header,
password, token, credential hoặc command. Client không thể tự POST audit.

Lưu ý:
- System Audit Log khác `task_activity_events` và `device_action_logs`.
- Những endpoint inventory **đã tồn tại trước đây và chưa có auth dependency**
  vẫn có thể được gọi không đăng nhập. Event của request không xác thực
  hiển thị `SYSTEM / Unauthenticated request`, không giả mạo người dùng.
  Khi có Bearer token hợp lệ, middleware kiểm tra token/session để gán User.
  Việc bắt buộc RBAC cho các endpoint cũ cần được triển khai riêng để tránh
  làm thay đổi HTTP contract ở đợt tích hợp audit này.
- Các thao tác CRUD/approval đã dùng audit nguyên tử: User, Role, Role
  Permissions, Device, Brand, Credential, Benchmark Scenario, khởi tạo/cleanup
  Benchmark Run, Task Create, Operation Create, và Approval Approve/Reject.
  Các luồng còn lại (đăng nhập, Conversation/Message, rename Conversation,
  và lỗi/denied) được ghi best-effort. Cần triển khai chung transaction cho
  các nghiệp vụ còn lại nếu yêu cầu tuân thủ tuyệt đối.
- Benchmark có thao tác **thiết bị mạng bên ngoài PostgreSQL**; DB rollback
  không tự đảo ngược cấu hình thiết bị. Cleanup vẫn phải được vận hành riêng.
- Với login failure / HTTP denied, middleware ghi transaction riêng; nếu DB
  ghi audit thất bại, sẽ có `SYSTEM AUDIT WRITE FAILED` trong server log.
  Cần theo dõi và cảnh báo lỗi này trên production.

## Kiểm thử

```bash
pytest tests/domains/test_audit.py tests/domains/test_audit_capture.py tests/domains/test_transactional_audit.py -q
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

Test `test_transactional_audit.py` cố ý gây trùng khóa audit và khẳng định
thao tác cập nhật Role cũng rollback. Trên PostgreSQL thật, xác minh cùng
trạng thái trước và sau khi audit insert thất bại trong môi trường test.
Nếu UI trống, xem log API, kết quả migration, RBAC permission và
`SYSTEM AUDIT WRITE FAILED`. Những log trước khi tính năng được triển khai
không được tạo lại tự động.
