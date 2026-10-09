# API

`api` là lớp HTTP transport của ứng dụng. Module này nhận request, validate input,
gọi service/repository phù hợp và trả response.

## Thành phần

- `route.py`: tập hợp các router và khai báo URL prefix.
- `dependencies.py`: dependency injection và object composition.
- `routes/`: các FastAPI endpoint mỏng, chia theo resource công khai.

## Luồng gọi

```text
HTTP request
  -> routes/<resource>.py
  -> dependency factory
  -> domain service hoặc agent manager
  -> response schema
```

## Quy tắc

- Route chỉ xử lý HTTP, không chứa routing agent hoặc logic kết nối thiết bị.
- Việc khởi tạo provider/service đặt trong `dependencies.py`.
- API không gọi Netmiko, GNS3 hoặc provider trực tiếp.
- Business rule mới được viết trong domain service; orchestration agent được viết
  trong `agents/manager.py` rồi mới expose qua route.

## Endpoint hiện tại

- `POST /api/chat/`: xử lý một lượt chat.
- `GET /api/agents/`: liệt kê agent đã đăng ký.
- `GET /api/network/`: trạng thái network domain.
- `POST/GET /api/conversations/`: tạo và đọc phiên hội thoại.
- `POST /api/conversations/{id}/messages`: thêm message vào conversation.
- `POST/GET/PATCH /api/devices`: quản lý inventory thiết bị trong PostgreSQL.
- `POST/GET /api/tasks`: tạo và truy vấn Task.
- `POST /api/tasks/{id}/operations`: thêm Operation do Planner tạo.
- `POST /api/operations/{id}/change-sets`: lập kế hoạch apply và rollback.
- `POST /api/change-sets/{id}/approve`: phê duyệt ChangeSet trước khi WRITE.

Unit test có thể dùng repository in-memory; Docker API dùng PostgreSQL để dữ liệu
thiết bị không mất khi tiến trình API khởi động lại.
