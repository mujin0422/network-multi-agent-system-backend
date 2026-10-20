# Domain Architecture

Thư mục `domains` chứa nghiệp vụ cốt lõi của hệ thống. Mỗi domain quản lý một
nhóm nghiệp vụ độc lập, bao gồm dữ liệu, quy tắc xử lý và API của chính nó.

| Domain         | Trách nhiệm                                         |
| -------------- | --------------------------------------------------- |
| `identity`     | Người dùng, vai trò, quyền và phiên đăng nhập       |
| `inventory`    | Thiết bị mạng, hãng, loại thiết bị và credential    |
| `conversation` | Cuộc hội thoại và tin nhắn                          |
| `execution`    | Task, operation và quá trình thực thi trên thiết bị |
| `evaluation`   | Đánh giá kết quả task, RCA, remediation và safety   |

## Cấu trúc một domain

```text
domain_name/
├── __init__.py
├── models/
│   ├── __init__.py
│   └── <resource>.py
├── schemas/
│   ├── __init__.py
│   └── <resource>.py
├── repositories/
│   ├── __init__.py
│   └── <resource>.py
├── services/
│   ├── __init__.py
│   └── <resource>.py
├── routers/
│   ├── __init__.py
│   ├── dependencies.py
│   └── <resource>.py
├── utils/
│   ├── __init__.py
│   └── <capability>.py
└── providers/                 # Chỉ tạo khi tích hợp hệ thống bên ngoài
    ├── __init__.py
    └── <provider>.py
```

Không bắt buộc domain phải có đủ mọi thư mục. Chỉ tạo một lớp khi có nhu cầu
thực tế, không tạo file rỗng để giữ chỗ.

## Trách nhiệm của từng lớp

### `models/`

**Chức năng:** Định nghĩa cấu trúc các bảng (tables) trong cơ sở dữ liệu
(Database) bằng SQLAlchemy ORM.

Model mô tả tên bảng, cột, kiểu dữ liệu, khóa chính, khóa ngoại, constraint và
cách Python object được ánh xạ thành database record. Model không kiểm tra
request, không chứa HTTP logic và không xử lý nghiệp vụ. Chỉ repository được sử
dụng model để đọc hoặc ghi database.

```python
class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
```

### `schemas/`

**Chức năng:** Định nghĩa cấu trúc dữ liệu để FastAPI kiểm tra (validate), chuyển
đổi dữ liệu đầu vào từ Client gửi lên (Request) và định dạng dữ liệu đầu ra gửi
về cho Client (Response).

Schema được viết bằng Pydantic và thường gồm:

- `<Resource>Create`: dữ liệu được phép gửi khi tạo mới.
- `<Resource>Update`: dữ liệu được phép gửi khi cập nhật.
- `<Resource>`: dữ liệu công khai trả về Client.
- `<Resource>Record`: dữ liệu nội bộ đầy đủ khi cần trường nhạy cảm.
- Enum của resource: ví dụ `UserStatus` nằm trong `user.py`, `TaskStatus` nằm
  trong `task.py`.

Schema không truy cập database, không gọi repository/service và không xử lý
nghiệp vụ. Password hash, refresh-token hash, secret hoặc ciphertext phải được
loại khỏi response công khai.

### `repositories/`

**Chức năng:** Là lớp duy nhất trong domain chịu trách nhiệm truy cập và lưu trữ
dữ liệu.

Repository nhận/trả schema hoặc domain contract, dùng SQLAlchemy model để truy
vấn database, và cung cấp các thao tác như `get`, `list`, `save`, `delete`.
Repository nên có `Protocol` để service phụ thuộc vào contract, không phụ thuộc
trực tiếp implementation PostgreSQL.

```python
class UserRepository(Protocol):
    def get(self, user_id: str) -> UserRecord | None: ...
    def save(self, user: UserRecord) -> None: ...
```

Repository không chứa business rule, không tạo HTTP response, không gọi router,
service hoặc provider.

Repository được tách theo bảng/resource. Ví dụ:

```text
conversation/repositories/
├── conversation.py          # conversations
└── message.py               # messages

execution/repositories/
├── task.py                  # tasks
├── operation.py             # task_operations
├── operation_dependency.py  # operation_dependencies
├── operation_device.py      # task_operation_devices
└── unit_of_work.py          # facade transaction của execution plan
```

Facade nhiều bảng chỉ được dùng khi một use case bắt buộc phải commit nguyên tử.
Nó điều phối các repository theo bảng trong cùng transaction, không chứa business
rule. Không tạo repository cho bảng chưa có use case đọc/ghi thực tế.

### `services/`

**Chức năng:** Chứa use case và toàn bộ quy tắc nghiệp vụ của domain.

Service chịu trách nhiệm:

- Kiểm tra resource liên quan có tồn tại.
- Kiểm tra dữ liệu trùng lặp và trạng thái hợp lệ.
- Sinh ID, timestamp, hash hoặc dữ liệu nghiệp vụ cần thiết.
- Phối hợp repository và provider qua contract.
- Phát sinh domain exception như `ResourceNotFoundError` hoặc
  `ResourceConflictError`.

Service không biết FastAPI, không nhận `Request`, không trả `Response`, không tạo
`HTTPException` và không thao tác trực tiếp với ORM model/session.

```python
class UserService:
    def create_user(self, payload: UserCreate) -> User:
        self._ensure_unique_email(payload.email)
        self._repository.save(user)
        return public_user
```

### `routers/`

**Chức năng:** Khai báo HTTP API của domain bằng FastAPI.

Router khai báo URL, HTTP method, status code, request/response schema và kiểm
tra quyền qua dependency. Mỗi handler chỉ nhận input, gọi public use case của
service và trả kết quả.

```python
@router.post("/", response_model=User, status_code=201)
async def create_user(
    payload: UserCreate,
    service: Annotated[UserService, Depends(get_user_service)],
) -> User:
    return service.create_user(payload)
```

Router phải mỏng: không chứa business rule, không viết SQL, không dùng model ORM
và không gọi repository trực tiếp. Route nên có `summary`, `response_model` và
chú thích `CREATE`, `READ`, `UPDATE`, `DELETE` để OpenAPI dễ hiểu.

`routers/dependencies.py` khởi tạo repository, provider và service rồi cung cấp
chúng qua FastAPI dependency injection. File này chỉ composition dependency,
không chứa nghiệp vụ.

### `providers/`

**Chức năng:** Tích hợp với hệ thống nằm ngoài database của ứng dụng, ví dụ
Netmiko, GNS3, API bên thứ ba hoặc secret vault.

Repository quản lý dữ liệu của ứng dụng; provider giao tiếp với hệ thống ngoài.
Provider không gọi router và không tự ghi dữ liệu nghiệp vụ vào database.

### `utils/`

**Chức năng:** Chứa các hàm hỗ trợ nhỏ, không trạng thái và chỉ có ý nghĩa bên
trong một domain. Ví dụ: hash/verify password của Identity hoặc tạo biểu thức mã
hóa credential của Inventory.

Không chuyển code vào `utils` chỉ vì chưa biết đặt ở đâu. Những thành phần sau
vẫn phải ở đúng lớp của chúng:

- Quy tắc/use case nghiệp vụ thuộc `services`.
- Truy vấn và ánh xạ dữ liệu thuộc `repositories`.
- Kết nối hệ thống bên ngoài thuộc `providers`.
- Validation request/response thuộc `schemas`.
- Helper dùng chung từ hai domain trở lên thuộc `core/utils`.

`utils` không được gọi service, repository, router hoặc thực hiện I/O. Riêng
helper gắn với persistence framework chỉ được repository cùng domain sử dụng.

### `__init__.py`

**Chức năng:** Công bố public API ổn định của package/domain.

Code bên ngoài nên import từ public package nếu symbol đã được export:

```python
from app.domains.inventory.schemas import DeviceCreate
from app.domains.inventory.services import DeviceService
```

Không import xuyên sâu vào file implementation nếu không cần thiết.

## Luồng xử lý chuẩn

```text
Client
  ↓ HTTP request
Router
  ↓ gọi use case
Service
  ↓ gọi persistence contract
Repository
  ↓ sử dụng ORM mapping
Model
  ↓
Database
```

Kết quả đi theo chiều ngược lại:

```text
Database → Model → Repository → Schema → Service → Router → Client
```

Khi cần gọi thiết bị hoặc dịch vụ ngoài:

```text
Router → Service → Provider → External system
```

## Quy tắc phụ thuộc bắt buộc

| Lớp                       | Được phép phụ thuộc                                              | Không được phép gọi                   |
| ------------------------- | ---------------------------------------------------------------- | ------------------------------------- |
| `models`                  | `core.database`, kiểu dữ liệu/enum cần thiết                     | repository, service, router, provider |
| `schemas`                 | Pydantic, thư viện chuẩn                                         | model, repository, service, router    |
| `repositories`            | models, schemas, `core.database`                                 | service, router, provider             |
| `providers`               | schema/config cần thiết, SDK bên ngoài                           | router, repository implementation     |
| `services`                | schemas, repository/provider contract, core utilities/exceptions | router, FastAPI, ORM model/session    |
| `routers`                 | schemas, services, router dependencies                           | model, repository trực tiếp, SQL      |
| `routers/dependencies.py` | repository/provider implementation, service, config              | business rule                         |
| `utils`                   | thư viện chuẩn hoặc SDK cần cho helper thuần                      | router, service, repository, I/O      |

Quy tắc bắt buộc:

1. Router chỉ gọi service, không gọi thẳng repository.
2. Service chỉ gọi repository/provider qua contract; không viết SQL và không sử
   dụng SQLAlchemy model/session.
3. Repository là lớp duy nhất sử dụng ORM model và database session.
4. Model không import service, repository hoặc router.
5. Schema không thực hiện I/O hoặc truy cập database.
6. Domain này không import implementation nội bộ của domain khác.
7. Khi cần phối hợp nhiều domain, application/orchestrator gọi public service
   của từng domain.
8. `app/main.py` chỉ đăng ký router dưới prefix `/api/v1`, không chứa nghiệp vụ.

## Những cách gọi bị cấm

```text
Router     ─X→ Repository
Router     ─X→ Model
Service    ─X→ SQLAlchemy Session/Model
Service    ─X→ Router
Repository ─X→ Service/Provider
Schema     ─X→ Database
Domain A   ─X→ implementation nội bộ của Domain B
```

Sai:

```python
@router.post("/")
async def create_user(payload: UserCreate):
    session.add(UserModel(...))  # Router đi thẳng vào ORM/database.
```

Đúng:

```python
@router.post("/")
async def create_user(payload: UserCreate, service: UserService):
    return service.create_user(payload)
```

## Quy tắc tổ chức file

- Tách file theo resource hoặc aggregate, không gom cả domain vào một file lớn.
- Schema và enum của resource đặt cùng file. Ví dụ `user.py` chứa `User`,
  `UserCreate`, `UserUpdate`, `UserRecord`, `UserStatus`.
- Model của các bảng gần nhau có thể chung file khi vẫn dễ đọc; tách theo
  resource khi file lớn.
- Tên file dùng danh từ số ít: `user.py`, `role.py`, `device.py`.
- Tên router, service và repository tương ứng với resource để dễ tìm kiếm.
- Chỉ export thành phần thực sự là public API qua `__init__.py`.
- Utility đặt tên theo capability (`security.py`, `credential_crypto.py`), không
  tạo file chung chung như `helpers.py` hoặc `common.py`.
- Không đặt password thô, token, secret hoặc ciphertext trong response và log.

## Ranh giới giữa các domain

Mỗi domain sở hữu model, schema và nghiệp vụ của bảng thuộc domain đó. Domain
không truy cập trực tiếp repository hoặc model của domain khác.

Workflow cần nhiều domain phải được phối hợp tại application/orchestration layer:

```text
Application service
   ├── gọi ConversationService
   └── gọi ExecutionService
```

Không được gọi theo cách:

```text
ConversationService ─X→ ExecutionRepository
```

Quy tắc này giữ các domain độc lập, dễ kiểm thử và tránh phụ thuộc vòng tròn khi
hệ thống phát triển lớn hơn.
