# Identity Domain

Domain `identity` sở hữu toàn bộ nghiệp vụ xác thực (authentication), phân quyền
(authorization), tài khoản người dùng, vai trò, quyền và phiên đăng nhập của hệ
thống.

Domain này cung cấp:

- Đăng nhập bằng email và password.
- Phát hành access token và refresh token.
- Làm mới và thu hồi phiên đăng nhập.
- Xác định người dùng hiện tại từ bearer token.
- Kiểm tra quyền theo cặp `Management Function` và `Action`.
- Thêm, cập nhật user.
- Thêm, cập nhật role.
- Lấy danh sách và chi tiết user/role theo ID.

## Các bảng được sở hữu

Identity sở hữu đúng bảy bảng thuộc nhóm Authentication & Authorization:

| Bảng                   | ORM model                 | Schema chính         | Ý nghĩa                               |
| ---------------------- | ------------------------- | -------------------- | ------------------------------------- |
| `roles`                | `RoleModel`               | `Role`               | Vai trò được gán cho user             |
| `management_functions` | `ManagementFunctionModel` | `ManagementFunction` | Chức năng cần được bảo vệ             |
| `actions`              | `ActionModel`             | `Action`             | Hành động như Add, Edit, View         |
| `permissions`          | `PermissionModel`         | `Permission`         | Cặp function-action được phép         |
| `role_permissions`     | `RolePermissionModel`     | `RolePermission`     | Quyền được gán cho từng role          |
| `users`                | `UserModel`               | `UserRecord`         | Tài khoản đăng nhập                   |
| `user_sessions`        | `UserSessionModel`        | `UserSessionRecord`  | Refresh session và trạng thái thu hồi |

`User` là response schema công khai, không chứa `password_hash`. `UserRecord` là
schema nội bộ có đầy đủ dữ liệu cần cho authentication nhưng đánh dấu
`password_hash` không được serialize ra response.

## Cấu trúc thư mục

```text
identity/
├── README.md
├── __init__.py
├── models/
│   └── identity.py
├── schemas/
│   ├── action.py
│   ├── auth.py
│   ├── management_function.py
│   ├── permission.py
│   ├── role.py
│   ├── user.py
│   └── user_session.py
├── repositories/
│   └── identity.py
├── services/
│   ├── identity.py
│   ├── role.py
│   └── user.py
└── routers/
    ├── auth.py
    ├── dependencies.py
    ├── role.py
    └── user.py
```

## Trách nhiệm của từng lớp

### `models/`

Định nghĩa SQLAlchemy ORM mapping cho bảy bảng Identity. Model chỉ mô tả cách
dữ liệu được lưu trong PostgreSQL; không chứa authentication, authorization hoặc
HTTP logic.

### `schemas/`

Định nghĩa request, response, internal record và enum của Identity:

- `auth.py`: `LoginRequest`, `RefreshRequest`, `TokenResponse` và JWT payload.
- `user.py`: `UserCreate`, `UserUpdate`, `User`, `UserRecord`, `UserStatus`.
- `role.py`: `RoleCreate`, `RoleUpdate`, `Role`.
- Các file còn lại ánh xạ management function, action, permission,
  role-permission và user session.

Status của user được đặt trong `user.py` vì nó thuộc user, không quản lý trong
một file `status.py` riêng.

### `repositories/`

`IdentityRepository` định nghĩa persistence contract mà các service sử dụng.
`PostgresIdentityRepository` triển khai contract đó bằng SQLAlchemy ORM.

Repository chịu trách nhiệm:

- Tìm user theo ID hoặc email.
- Tìm role theo ID hoặc tên.
- Lưu user và role.
- Lấy tập quyền của role.
- Tạo, đọc, rotate và revoke user session.
- Cập nhật thời điểm đăng nhập gần nhất.

Chỉ repository được dùng ORM model và database session.

### `services/`

- `IdentityService`: login, refresh, logout, xác thực access token và kiểm tra
  quyền.
- `UserService`: tạo/cập nhật user, kiểm tra role, email trùng và hash password.
- `RoleService`: tạo/cập nhật role, kiểm tra tên trùng và ghi audit user.

Service chứa business rule nhưng không phụ thuộc FastAPI và không thao tác trực
tiếp với ORM model.

### `routers/`

- `auth.py`: API đăng nhập, refresh, logout và lấy user hiện tại.
- `user.py`: API thêm và sửa user.
- `role.py`: API thêm và sửa role.
- `dependencies.py`: khởi tạo repository/service, đọc bearer token và cung cấp
  dependency kiểm tra quyền.

Router chỉ nhận request, gọi service và trả response; không gọi repository hoặc
model trực tiếp.

## API hiện tại

Tất cả endpoint được đăng ký dưới `/api/v1`:

| Method  | Endpoint                  | Chức năng             | Quyền                    |
| ------- | ------------------------- | --------------------- | ------------------------ |
| `POST`  | `/api/v1/auth/login`      | Đăng nhập             | Public                   |
| `POST`  | `/api/v1/auth/refresh`    | Làm mới token         | Refresh token hợp lệ     |
| `POST`  | `/api/v1/auth/logout`     | Thu hồi session       | Đã đăng nhập             |
| `GET`   | `/api/v1/auth/me`         | Lấy user hiện tại     | Đã đăng nhập             |
| `POST`  | `/api/v1/users/`          | Thêm user             | User Management / Add    |
| `GET`   | `/api/v1/users/`          | Lấy danh sách user    | User Management / View   |
| `GET`   | `/api/v1/users/{user_id}` | Lấy user theo ID      | User Management / View   |
| `PATCH` | `/api/v1/users/{user_id}` | Sửa user              | User Management / Edit   |
| `POST`  | `/api/v1/roles/`          | Thêm role             | Role-Based Access / Add  |
| `GET`   | `/api/v1/roles/`          | Lấy danh sách role    | Role-Based Access / View |
| `GET`   | `/api/v1/roles/{role_id}` | Lấy role theo ID      | Role-Based Access / View |
| `PATCH` | `/api/v1/roles/{role_id}` | Sửa role              | Role-Based Access / Edit |

## Luồng authentication

```text
Client
  ↓ email + password
Auth Router
  ↓
IdentityService
  ├── IdentityRepository → đọc user/password hash
  ├── kiểm tra trạng thái UserStatus.ACTIVE
  ├── kiểm tra password
  ├── tạo access token + refresh token
  └── IdentityRepository → lưu UserSessionRecord
```

Access token chứa:

- `sub`: ID của user.
- `sid`: ID của session.
- `iat`: thời điểm phát hành.
- `exp`: thời điểm hết hạn.
- `jti`: ID duy nhất của token.

Khi xác thực request, chữ ký JWT hợp lệ là chưa đủ. `IdentityService` còn kiểm
tra session chưa bị revoke, chưa hết hạn và user vẫn ở trạng thái `ACTIVE`.

## Luồng authorization (RBAC)

Quyền được biểu diễn bằng cặp:

```text
(Management Function, Action)
```

Ví dụ:

```text
(User Management, Add)
(User Management, Edit)
(Role-Based Access, Add)
(Device Management, View)
```

Route khai báo quyền cần thiết bằng dependency:

```python
current_user: Annotated[
    User,
    Depends(require_permission("User Management", "Edit")),
]
```

Luồng kiểm tra:

```text
Bearer token
  ↓
get_current_identity
  ↓ xác thực token, session và user
require_permission
  ↓ đọc permissions theo role_id
Cho phép request hoặc trả lỗi authorization
```

## Quy tắc phụ thuộc

Luồng hợp lệ trong Identity:

```text
Router → Service → IdentityRepository contract
                         ↓
             PostgresIdentityRepository → ORM Model → Database
```

Các cách gọi bị cấm:

```text
Router     ─X→ Repository/ORM Model
Service    ─X→ ORM Model/SQLAlchemy Session
Repository ─X→ Service/Router
Schema     ─X→ Database
```

Domain khác cần kiểm tra người dùng hoặc quyền phải sử dụng public service hoặc
FastAPI dependency của Identity, không truy cập trực tiếp `UserModel`,
`RoleModel` hoặc `PostgresIdentityRepository`.

## Quy tắc bảo mật

- Không lưu password thô; password phải được bcrypt hash trước khi lưu.
- Không trả `password_hash` qua API.
- Không lưu refresh token thô; chỉ lưu hash của refresh token.
- Không ghi password, token hoặc hash vào log.
- Email đăng nhập được chuẩn hóa thành chữ thường.
- Mỗi refresh token chỉ thuộc một session và session có thể bị revoke.
- Mọi route quản trị user/role phải khai báo quyền tương ứng.
- `created_by` và `last_updated_by` của role lấy từ user đang đăng nhập, không
  nhận tùy ý từ request.

## Mở rộng domain

Khi thêm một chức năng Identity mới, thực hiện theo thứ tự:

1. Thêm hoặc cập nhật schema của resource.
2. Chỉ thêm ORM model/migration nếu database thực sự thay đổi.
3. Mở rộng repository contract và implementation khi cần persistence.
4. Viết business rule trong service.
5. Thêm route mỏng và dependency phân quyền.
6. Export public symbol qua `__init__.py` khi cần dùng bên ngoài package.
7. Viết test cho service, permission và API contract.
