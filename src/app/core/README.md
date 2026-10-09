# Core

`core` chứa cấu hình/hạ tầng dùng chung và không chứa nghiệp vụ.

## Thành phần

- `config.py`: đọc và validate biến môi trường bằng Pydantic Settings.

Chỉ tạo `database.py`, `logging.py` hoặc module hạ tầng khác khi ứng dụng thật sự
sử dụng chúng; không tạo package placeholder.

## Quy tắc phụ thuộc

- Domain và API được phép import từ `core`.
- `core` không được import từ `api` hoặc bất kỳ domain nào.
- Không đọc trực tiếp `os.environ` bên ngoài `config.py`.
- Nếu bổ sung database, query nghiệp vụ phải nằm trong repository của domain.

## Khi nào sửa module này?

- Thêm biến môi trường dùng chung.
- Đổi cách quản lý database connection/session.
- Thêm logging, tracing hoặc metrics dùng cho toàn hệ thống.
