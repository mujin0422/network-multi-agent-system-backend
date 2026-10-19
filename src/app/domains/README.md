# Domains

`domains` chứa nghiệp vụ cốt lõi của hệ thống. Mỗi domain là một bounded context
có contract, use case, transport adapter và persistence riêng. Business layer
không tự đọc biến môi trường và không phụ thuộc trực tiếp vào implementation của
domain khác.

## Cấu trúc chuẩn

```text
domain_name/
├── __init__.py          # public API ổn định của domain
├── schemas/             # Pydantic request, response, enum và domain contract
│   ├── __init__.py
│   └── <feature>.py
├── repositories/        # persistence port và adapter
│   ├── __init__.py
│   └── <aggregate>.py
├── services/            # use case và business rule
│   ├── __init__.py
│   └── <feature>.py
├── routers/             # FastAPI transport của domain, chỉ tạo khi cần
│   ├── __init__.py
│   └── <feature>.py
└── providers/           # tích hợp hệ thống ngoài, chỉ tạo khi cần
    ├── __init__.py
    └── <provider>.py
```

Không phải domain nào cũng cần đủ mọi folder:

- `schemas/` và `services/` được tạo khi domain đã có use case tương ứng.
- `repositories/` chỉ cần khi domain đọc hoặc ghi persistence.
- `providers/` chỉ dành cho kết nối dịch vụ hoặc thiết bị bên ngoài.
- `routers/` expose public service qua HTTP và không chứa business rule.
- `models/` chứa SQLAlchemy ORM mapping của các bảng do domain sở hữu; Pydantic
  trong `schemas/` tiếp tục là contract request/response và không phải ORM model.
- `app/main.py` tổng hợp router của các domain. Route chat/agent discovery nằm
  trong `app/agents/routers` vì thuộc application layer của agent.

Các package con export public symbol qua `__init__.py`. Code bên ngoài ưu tiên
import từ public API của domain:

```python
from app.domains.inventory import DeviceService
from app.domains.inventory.schemas import DeviceCreate
```

Không import xuyên vào file implementation nếu symbol đã được export.

## Quy tắc tách file con

Folder chỉ dùng để phân lớp; bên trong tiếp tục tách file theo resource hoặc
aggregate, không gom tất cả class vào một `schemas.py` lớn:

```text
conversation/schemas/
├── conversation.py
└── message.py

execution/schemas/
├── device_action_log.py
├── task.py
├── operation.py
├── operation_dependency.py
├── operation_device.py
├── task_execution.py
└── status.py

inventory/schemas/
├── brand.py
├── category.py
├── credential.py
├── device.py
└── device_connection.py
```

Một file có thể chứa các contract rất gần nhau như `Device`, `DeviceCreate` và
`DeviceUpdate`. Chỉ tách tiếp khi chúng thuộc resource khác hoặc file bắt đầu có
nhiều trách nhiệm.

## Năm domain của hệ thống

Tên domain ánh xạ trực tiếp với năm nhóm trong tài liệu database:

| Nhóm tài liệu                      | Domain source  |
| ---------------------------------- | -------------- |
| 3.1 Authentication & Authorization | `identity`     |
| 3.2 Network Inventory              | `inventory`    |
| 3.3 Conversation Management        | `conversation` |
| 3.4 AI Execution Management        | `execution`    |
| 3.5 AI Evaluation & Benchmarking   | `evaluation`   |

### `identity`

Sở hữu user, session, role, permission và authentication/authorization. Database
record schemas đã được định nghĩa theo đúng bảy bảng trong tài liệu. Domain có
PostgreSQL repository, login/refresh/logout, current-user endpoint và dependency
RBAC theo function/action.

### `inventory`

Sở hữu toàn bộ nhóm Network Inventory trong tài liệu: device, brand, category,
credential và khả năng kết nối GNS3/Netmiko. Domain cung cấp Device API,
uniqueness rule, PostgreSQL repository và provider kết nối thiết bị. Test dùng
stub repository cục bộ, không đưa memory adapter vào production code.

Public Device contract không trả password/secret. Credential chỉ được giải mã
trong repository dành cho luồng kết nối và không được ghi log.

### `conversation`

Sở hữu conversation, message và thứ tự lịch sử hội thoại. Domain chỉ quản lý dữ
liệu hội thoại; việc chọn hoặc điều phối AI agent nằm ở application layer.

### `execution`

Sở hữu Task, Operation, dependency, trạng thái thực thi và device action audit.
Schema đã bao phủ toàn bộ sáu bảng; hiện service, repository và router mới triển
khai use case Task/Operation.

### `evaluation`

Sở hữu AI evaluation và benchmarking: goal result, RCA, remediation, safety và
evidence. Schema `TaskEvaluation` đã ánh xạ bảng `task_evaluations`; repository,
service và router sẽ được tạo khi có workflow đánh giá thực tế.

## Phạm vi schema database

Hai mươi bảng trong tài liệu đã có record schema tương ứng. Tên trường trong các
record schema giữ nguyên theo database; các request/response schema bổ sung như
`DeviceCreate` hoặc `TaskDetail` không được tính là bảng mới.

| Domain         | Bảng và record schema                                                                                                                                                                                                                |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `identity`     | `roles` → `Role`, `management_functions` → `ManagementFunction`, `actions` → `Action`, `permissions` → `Permission`, `role_permissions` → `RolePermission`, `users` → `UserRecord`, `user_sessions` → `UserSessionRecord`            |
| `inventory`    | `brands` → `Brand`, `categories` → `Category`, `credentials` → `CredentialRecord`, `devices` → `Device`                                                                                                                              |
| `conversation` | `conversations` → `Conversation`, `messages` → `Message`                                                                                                                                                                             |
| `execution`    | `tasks` → `Task`, `task_operations` → `Operation`, `operation_dependencies` → `OperationDependency`, `task_operation_devices` → `TaskOperationDevice`, `task_executions` → `TaskExecution`, `device_action_logs` → `DeviceActionLog` |
| `evaluation`   | `task_evaluations` → `TaskEvaluation`                                                                                                                                                                                                |

`User`, `Credential` là public response schema đã loại dữ liệu nhạy cảm.
`UserRecord`, `UserSessionRecord` và `CredentialRecord` vẫn nhận đủ trường nội bộ
nhưng password, refresh-token hash và ciphertext được đánh dấu `exclude=True` để
không bị serialize ngoài ý muốn.

## Đánh giá ranh giới domain

Năm domain trên phù hợp với phạm vi hiện tại và chưa cần thêm hoặc loại bỏ:

| Domain         | Trách nhiệm                               | Trạng thái                                               |
| -------------- | ----------------------------------------- | -------------------------------------------------------- |
| `identity`     | User, session và RBAC                     | Authentication, session và route permissions implemented |
| `inventory`    | Inventory, credential và kết nối thiết bị | Implemented                                              |
| `conversation` | Hội thoại và message                      | Implemented                                              |
| `execution`    | Task, operation và device action audit    | All schemas; Task/Operation use cases                    |
| `evaluation`   | Evaluation và benchmarking                | Schema implemented; workflow planned                     |
| Domain         | Trách nhiệm                               | Trạng thái                                               |
| -------------- | ----------------------------------------- | -------------------------------------                    |
| `identity`     | User, session và RBAC                     | Schema implemented; use cases planned                    |
| `inventory`    | Inventory, credential và kết nối thiết bị | Implemented                                              |
| `conversation` | Hội thoại và message                      | Implemented                                              |
| `execution`    | Task, operation và device action audit    | All schemas; Task/Operation use cases                    |
| `evaluation`   | Evaluation và benchmarking                | Schema implemented; workflow planned                     |

Chỉ cân nhắc tách thêm trong tương lai khi xuất hiện ranh giới nghiệp vụ độc lập:

- Tách `credential` khỏi `inventory` khi secret lifecycle, rotation và vault trở
  thành một bounded context độc lập.
- Không biến `agents` hoặc `tools` thành domain; chúng là lớp orchestration và
  adapter sử dụng các domain service.

## Quy tắc phụ thuộc

```text
api / agents / tools
         ↓
   domain service
      ↙      ↘
repository  provider
      ↘      ↙
      schemas + core
```

- Service phối hợp business rule và chỉ phụ thuộc persistence/provider qua
  contract.
- Repository không gọi provider bên ngoài.
- Provider không ghi trực tiếp dữ liệu nghiệp vụ.
- API, agent và tool gọi public service; không đi tắt vào repository.
- Khi hai domain cần phối hợp, application/orchestrator gọi hai public service;
  không để domain này import implementation nội bộ của domain kia.
