# Core

`core` chứa các thành phần kỹ thuật dùng chung cho toàn bộ backend. Thư mục này
không chứa business logic của từng domain và không phụ thuộc ngược vào `agents`,
`tools` hoặc `domains`.

## Cấu trúc hiện tại

```text
core/
├── config/
│   ├── __init__.py
│   └── settings.py
├── database/
│   ├── __init__.py
│   ├── base.py
│   └── session.py
├── exceptions/
│   ├── __init__.py
│   ├── domain.py
│   └── handlers.py
├── utils/
│   ├── __init__.py
│   └── ids.py
├── logging.py
├── __init__.py
└── README.md
```

Chỉ các thành phần đã có implementation mới được liệt kê ở trên. Các folder
`cache`, `middlewares` và `security` chỉ được tạo khi có use case thực tế.

## Trách nhiệm

### `config/`

- `settings.py` khai báo `Settings` bằng Pydantic Settings, đọc và kiểm tra biến
  môi trường của ứng dụng, PostgreSQL, GNS3, kết nối mạng và AI provider.
- `get_settings()` cache một instance cấu hình cho mỗi process.
- `__init__.py` cung cấp public import ổn định:

  ```python
  from app.core.config import Settings, get_settings
  ```

Không đọc trực tiếp `os.environ` ở các module khác. Biến môi trường dùng chung
phải được khai báo và kiểm tra tại đây.

### `database/`

- `base.py` khai báo SQLAlchemy `Base` dùng chung cho ORM model thuộc các domain.
- `session.py` chuẩn hóa PostgreSQL URL sang psycopg 3, tạo Engine, connection
  pool và synchronous session factory.
- `__init__.py` giữ public import ổn định:

  ```python
  from app.core.database import Base, create_session_factory
  ```

ORM model vẫn nằm trong `models/` của domain sở hữu bảng. Query nghiệp vụ vẫn
nằm trong repository; `core/database` chỉ chứa hạ tầng kết nối dùng chung.

### `exceptions/`

- `domain.py` chứa `DomainError` và các lỗi nghiệp vụ dùng chung.
- `handlers.py` ánh xạ exception dùng chung thành HTTP response cho FastAPI.
- `__init__.py` export public exception để API và domain không phụ thuộc vào tên
  file implementation:

  ```python
  from app.core.exceptions import ResourceNotFoundError
  ```

HTTP handler chịu trách nhiệm chuyển exception thành response. Exception không
được chứa chi tiết bí mật hoặc thông tin hạ tầng nhạy cảm.

### `utils/`

Chứa các hàm nhỏ, thuần và không phụ thuộc framework. Hiện `utils/ids.py` cung
cấp `generate_id()` để tạo ID nghiệp vụ theo prefix, ngày UTC và phần ngẫu nhiên:

```python
from app.core.utils import generate_id
```

Quy ước prefix cụ thể thuộc về domain gọi hàm. Không đưa service, repository,
settings hoặc code tích hợp hạ tầng vào `utils`.

### `logging.py`

Cấu hình định dạng và log level dùng chung cho process. Module lấy log level từ
`get_settings()` và không chứa logic nghiệp vụ.

## Quy tắc phụ thuộc

```text
main / agents / tools / domains
               ↓
              core
```

- Các lớp phía trên được phép import public API từ `core`.
- `core` không import từ các lớp phía trên.
- Query nghiệp vụ nằm trong repository của domain, không đặt trong `core`.
- Chỉ tạo abstraction dùng chung khi đã có ít nhất một use case thực tế.
- Không tạo file rỗng hoặc implementation giả chỉ để lấp đầy cấu trúc folder.

## Khi nào mở rộng từng folder?

- `database/`: có thể bổ sung transaction helper hoặc lifecycle khi ứng dụng
  cần quản lý session theo request.
- `security/`: khi có password hashing, token hoặc encryption service dùng chung.
- `middlewares/`: khi ứng dụng có middleware dùng chung như request ID hoặc
  observability.
- `cache/`: khi đã chọn cache backend và có use case cần cache.

Khi bổ sung module mới, export public symbol qua `__init__.py` của package tương
ứng và cập nhật README này.
