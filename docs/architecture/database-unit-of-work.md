# Database connection lifecycle và Unit of Work

## Mục tiêu

Không tạo `Engine`/pool mới trong mỗi repository, không chia sẻ SQLAlchemy
`Session` giữa các request, và giữ business mutation + audit trong cùng
transaction. Kiến trúc này dành cho SQLAlchemy sync + psycopg 3.

## Cấu trúc

- `app/core/database/session.py`: registry thread-safe, một Engine và
  `sessionmaker` cho mỗi canonical database URL trong từng process.
  PostgreSQL URL được chuẩn hóa về `postgresql+psycopg://`.
- `app/core/database/unit_of_work.py`: `DatabaseUnitOfWork` mở
  `sessionmaker.begin()`, tự commit khi thành công và rollback khi lỗi.
- Repository: hàm đọc ngắn có thể tự mở Session; hàm ghi được Service sở hữu
  transaction dùng `save_in_session(session, data)` và **không commit**.
- Service: validation và quy tắc nghiệp vụ trước transaction; trong
  `uow.begin()` thực hiện các repository writes và
  `record_audit_in_session(session, ...)`.
- FastAPI dependency: inject UoW cùng factory theo URL; có thể cache Service
  và Session Factory, nhưng không bao giờ cache `Session` riêng lẻ.
- `main.lifespan`: ra tín hiệu dừng approval worker, đợi DB sweep xong rồi
  `engine.dispose()` các pool. Giữ registry khi lifespan khởi động lại trong
  cùng process để các Service cache không giữ factory thuộc pool khác.

## Ví dụ

```python
# Service là chủ sở hữu transaction, repository nhận cùng Session.
with self._uow.begin() as session:
    self._repository.save_in_session(session, device)
    record_audit_in_session(
        session,
        action="DEVICE_CREATE",
        resource_type="DEVICE",
        resource_id=device.id,
    )
# Cả Device và AuditLog được COMMIT; lỗi ở một bước => ROLLBACK cả hai.
```

`AuditLogService.record_in_session()` chỉ gọi `session.add(...)`; không tự
mở session và không commit. Các test minh họa rollback khi audit insert lỗi.

## Những luồng đang sử dụng

- Inventory: Device, Brand, Credential create/update.
- Identity: User, Role create/update; Role Permissions replace.
- Benchmark: Scenario create/update, Run start/cleanup, và cặp
  Evaluation + Run khi hoàn tất.
- Execution: Task create; Operation create + chuyển Task sang PLANNING;
  execution plan đã được ghi trong cùng UoW.
- Approval: quyết định phê duyệt và worker timeout vốn dùng transaction
  PostgreSQL chung cho nhiều record; một số đoạn còn sử dụng helper audit
  tương thích cũ.

Repository còn dùng `self._sessions.begin()` trực tiếp cho các write đơn bảng
chưa chuyển vẫn tạo **Session mới** từ factory chung, nên không tạo thêm pool.
Chuyển dần các luồng còn lại sang explicit UoW khi có nghiệp vụ cần cập nhật
nhiều bảng hoặc yêu cầu audit bắt buộc.

## Những điều KHÔNG nên làm

- Không giữ UoW trong lúc LLM sinh câu trả lời, gọi Netmiko/GNS3, gọi HTTP
  bên ngoài hoặc chờ approval (mặc định 15 phút).
- Không truyền chung một SQLAlchemy Session cho hai request, thread hoặc
  asyncio task đang chạy đồng thời.
- Không tự `commit()` hoặc `rollback()` trong repository nhận Session từ UoW.
- Không tưởng rằng rollback PostgreSQL có thể hoàn tác cấu hình mạng thật.
  Network cleanup/compensation cần cơ chế riêng.
- Đăng nhập thất bại và HTTP DENIED vẫn được ghi audit độc lập để giữ
  bằng chứng bảo mật kể cả khi business transaction không thành công.

## Kiểm thử

```bash
pytest tests/core/test_session_factory_lifecycle.py \
       tests/core/test_approval_timeout_worker_shutdown.py \
       tests/domains/test_transactional_audit.py \
       tests/domains/test_identity_repository.py \
       tests/domains/test_audit_capture.py -q
pytest -q
```

Khi chạy nhiều worker ASGI: **mỗi process** có một engine/pool riêng, không có
một pool chia sẻ xuyên process. Cần đặt giới hạn pool theo số worker và
`max_connections` của PostgreSQL. Thay đổi này không cần migration schema.
