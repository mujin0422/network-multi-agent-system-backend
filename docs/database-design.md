# DATABASE DESIGN - MULTI-AGENT AI NETWORK AUTOMATION PLATFORM

# 1. OVERVIEW

**_Database được thiết kế để hỗ trợ:_**

- Quản lý người dùng và phân quyền.
- Quản lý thiết bị mạng.
- Quản lý credential truy cập thiết bị.
- Theo dõi yêu cầu của người dùng gửi tới AI Agent.
- Theo dõi quá trình Agent thực thi.
- Lưu lịch sử thao tác trên thiết bị.
- Lưu lịch sử hội thoại Chat UI.

**_Nguyên tắc:_**

- Agent không được lưu trong Database.
- Các Agent được triển khai bằng code trong `src/app/agents`.
- Các Tool được triển khai bằng code trong `src/app/tools`.
- Database chỉ quản lý metadata, quyền, dữ liệu runtime và lịch sử hoạt động.
- Password của thiết bị không lưu plaintext, không hash; sử dụng encryption vì hệ thống cần decrypt để kết nối thiết bị.

**_Thiết kế_**

- Nguồn: https://drive.google.com/file/d/1DDMFf9z_1boqKG0QCmJ9TLc-s5PQVKhw/view?usp=sharing

# 2. LIST OF TABLES AND DESCRIPTIONS

## 2.1 GROUP 1: AUTHENTICATION & AUTHORIZATION

Nhóm chịu trách nhiệm quản lý thông tin người dùng, vai trò và quyền truy cập trong hệ thống. Nhóm này hỗ trợ hai chức năng chính:

- **Authentication (Xác thực)**: Xác định danh tính của người dùng khi đăng nhập vào hệ thống.
- **Authorization (Phân quyền)**: Xác định người dùng được phép truy cập chức năng nào và thực hiện những hành động nào trên từng chức năng.

Cơ chế phân quyền được xây dựng theo mô hình Role-Based Access Control (RBAC). Mỗi người dùng được gán một vai trò; mỗi vai trò có thể sở hữu nhiều quyền; mỗi quyền được xác định dựa trên sự kết hợp giữa một chức năng và một hành động cụ thể.

### 2.1.1 Users (Người dùng)

**_[1] Ý nghĩa bảng (Description)_**

Lưu trữ thông tin tài khoản của người dùng sử dụng hệ thống, bao gồm thông tin định danh, thông tin xác thực, vai trò, trạng thái tài khoản và thông tin phục vụ quản lý phiên đăng nhập.

Mỗi người dùng được gán một vai trò để hệ thống xác định các quyền mà người dùng được phép thực hiện.

**_[2] Trường dữ liệu (Fields)_**

| Field           | Type       | Nullable | Meaning                                                            |
| --------------- | ---------- | -------- | ------------------------------------------------------------------ |
| id              | varchar PK | No       | Mã định danh duy nhất của người dùng trong hệ thống.               |
| role_id         | varchar FK | No       | Mã vai trò được gán cho người dùng.                                |
| email           | varchar    | No       | Địa chỉ email của người dùng.                                      |
| password_hash   | varchar    | No       | Mật khẩu của người dùng được hash trước khi lưu vào cơ sở dữ liệu. |
| full_name       | varchar    | No       | Họ và tên hoặc tên hiển thị của người dùng trong hệ thống.         |
| user_status     | enum       | No       | Trạng thái hoạt động của tài khoản người dùng.                     |
| created_at      | timestamp  | No       | Thời điểm tài khoản người dùng được tạo trong hệ thống.            |
| last_updated_at | timestamp  | Yes      | Thời điểm thông tin tài khoản được cập nhật gần nhất.              |
| last_login_at   | timestamp  | Yes      | Thời điểm người dùng đăng nhập thành công gần nhất.                |

**_[3] Ràng buộc (constraint):_**

| Type       | Applicable to | Description                                                                   |
| ---------- | ------------- | ----------------------------------------------------------------------------- |
| **PK**     | `id`          | Khóa chính, định danh duy nhất người dùng, định dạng: `user-ddmmyy-xxxxxxxx`. |
| **FK**     | `role_id`     | Tham chiếu đến `Roles(id)`.                                                   |
| **UNIQUE** | `email`       | Mỗi email chỉ được dùng cho một tài khoản.                                    |
| **CHECK**  | `user_status` | Thuộc tập giá trị `('ACTIVE', 'DISABLED')`.                                   |
| **CHECK**  | `email`       | Định dạng email hợp lệ.                                                       |
| **INDEX**  | `role_id`     | Tăng tốc truy vấn người dùng theo vai trò.                                    |
| **INDEX**  | `user_status` | Tăng tốc lọc tài khoản theo trạng thái.                                       |

**_[4] Quy tắc nghiệp vụ (Business Rules)_**

[4.1] Trường `user_status`

```
Các trạng thái hiện tại gồm:
    - ACTIVE: tài khoản đang hoạt động và có thể đăng nhập nếu thông tin xác thực hợp lệ.
    - DISABLED: tài khoản bị vô hiệu hóa và không được phép tạo phiên đăng nhập mới.
```

[4.2] Trường `password_hash`

```
Mật khẩu người dùng phải được hash trước khi lưu vào cơ sở dữ liệu, không lưu dưới dạng plaintext .
```

[4.3] Trường `email`

```
Email được sử dụng làm thông tin nhận diện và phục vụ quá trình đăng nhập, đổi mật khẩu.
```

[4.4] Vô hiệu hóa tài khoản người dùng

```
Khi user_status chuyển sang DISABLED:
    - Người dùng không được phép đăng nhập vào hệ thống.
    - Người dùng không được phép sử dụng Access Token còn hiệu lực để thực hiện các yêu cầu mới.
    - Các User_Sessions chưa hết hạn của người dùng phải bị thu hồi hoặc bị từ chối khi xác thực.

Việc vô hiệu hóa tài khoản không làm mất lịch sử Task, Execution, Device_Action_Log hoặc Conversation đã được tạo trước đó.
```

[4.5] Thay đổi vai trò người dùng

```
Khi role_id của người dùng được thay đổi, các quyền truy cập của người dùng phải được xác định lại theo vai trò mới.

Hệ thống phải bảo đảm Access Token hoặc thông tin phân quyền đã được cấp trước đó không tiếp tục cho phép người dùng thực hiện những hành động không còn được cấp quyền.
```

### 2.1.2 User_Sessions (Phiên người dùng)

**_[1] Ý nghĩa bảng (Description)_**

Lưu trữ và quản lý các phiên đăng nhập của người dùng trong hệ thống, bao gồm thông tin xác thực phiên, thời gian hết hạn và trạng thái thu hồi phiên, nhằm hỗ trợ cơ chế duy trì đăng nhập và đăng xuất an toàn.

**_[2] Trường dữ liệu (Fields)_**

| Field              | Type      | Nullable | Meaning                                                                                       |
| ------------------ | --------- | -------- | --------------------------------------------------------------------------------------------- |
| id                 | UUID      | No       | Mã định danh duy nhất của phiên đăng nhập.                                                    |
| user_id            | varchar   | No       | Người dùng sở hữu phiên đăng nhập.                                                            |
| refresh_token_hash | varchar   | No       | Refresh Token được sử dụng để cấp lại Access Token mà không yêu cầu người dùng đăng nhập lại. |
| expires_at         | timestamp | No       | Thời điểm Refresh Token hiện tại hết hiệu lực.                                                |
| created_at         | timestamp | No       | Thời điểm phiên đăng nhập được tạo.                                                           |
| revoked_at         | timestamp | Yes      | Thời điểm phiên bị thu hồi hoặc đăng xuất. NULL nghĩa là phiên chưa bị thu hồi.               |

**_[3] Ràng buộc (constraint):_**

| Type       | Applicable to        | Description                                     |
| ---------- | -------------------- | ----------------------------------------------- |
| **PK**     | `id`                 | Khóa chính, định danh duy nhất phiên đăng nhập. |
| **FK**     | `user_id`            | Tham chiếu đến `Users(id)`.                     |
| **UNIQUE** | `refresh_token_hash` | Mỗi refresh token hash chỉ xuất hiện một lần.   |
| **CHECK**  | `revoked_at`         | Nếu có giá trị thì phải `>= created_at`.        |
| **CHECK**  | `expires_at`         | Phải `> created_at`.                            |
| **INDEX**  | `user_id`            | Tăng tốc truy vấn phiên theo người dùng.        |
| **INDEX**  | `expires_at`         | Tăng tốc dọn dẹp phiên hết hạn.                 |

**_[4] Quy tắc nghiệp vụ (Business Rules)_**

[4.1] Điều kiện "cấp Access Token mới"

```
Phiên không được cấp Access Token mới nếu đã hết hạn `expires_at` hoặc đã bị thu hồi `revoked_at` IS NOT NULL.
```

[4.2] Điều kiện "khi đăng xuất"

```
Khi người dùng đăng xuất khỏi một thiết bị, chỉ phiên tương ứng cần được cập nhật `revoked_at`.
```

[4.3] Trường `refresh_token_hash`

```
Refresh Token phải được hash trước khi lưu vào cơ sở dữ liệu, không lưu dưới dạng plaintext.
```

[4.4] Điều kiện "phiên đăng nhập hợp lệ"

```
Một User_Session chỉ được xem là hợp lệ khi:
    - revoked_at IS NULL.
    - Thời điểm hiện tại chưa vượt quá expires_at.
    - User sở hữu phiên đang có user_status = ACTIVE.
    - Refresh Token được cung cấp khớp với refresh_token_hash đang được lưu trong hệ thống.

Nếu một trong các điều kiện không được thỏa mãn, hệ thống không được cấp Access Token mới cho phiên đó.
```

[4.5] Cơ chế "Refresh Token Rotation"

```
Khi hệ thống cấp Refresh Token mới:
    - Refresh Token cũ phải bị vô hiệu hóa.
    - refresh_token_hash được cập nhật bằng hash của token mới.
    - expires_at được cập nhật theo thời hạn token mới.

Refresh Token đã bị thay thế không còn hợp lệ để cấp Access Token mới.

Với thiết kế chỉ lưu refresh_token_hash hiện tại, Backend có thể từ chối Refresh Token cũ nhưng chưa đủ dữ liệu để phân biệt token cũ bị sử dụng lại với các token không hợp lệ khác.

Nếu cần phát hiện Refresh Token Reuse và thu hồi toàn bộ Token Family, hệ thống phải quản lý bổ sung lịch sử token đã cấp hoặc định danh Token Family/JTI. Đây là phạm vi mở rộng, chưa bắt buộc ở phiên bản hiện tại.
```

### 2.1.3 Roles (Vai trò)

**_[1] Ý nghĩa bảng (Description)_**

Lưu trữ danh sách các vai trò được định nghĩa trong hệ thống.

Một số vai trò có trong hệ thống: Super Administrator / System Administrator / Network Operator / Network Engineer

**_[2] Trường dữ liệu (Fields)_**

| Field           | Type      | Nullable | Meaning                                                                        |
| --------------- | --------- | -------- | ------------------------------------------------------------------------------ |
| id              | varchar   | No       | Mã định danh duy nhất của vai trò trong hệ thống.                              |
| name            | varchar   | No       | Tên hiển thị của vai trò.                                                      |
| description     | varchar   | Yes      | Mô tả về vai trò, giúp người quản trị hiểu rõ phạm vi và mục đích của vai trò. |
| created_by      | varchar   | Yes      | Mã người dùng tạo Role. NULL đối với Role khởi tạo bởi hệ thống.               |
| last_updated_by | varchar   | Yes      | Mã người dùng cập nhật Role gần nhất.                                          |
| created_at      | timestamp | No       | Thời điểm vai trò được tạo trong hệ thống.                                     |
| last_updated_at | timestamp | Yes      | Thời điểm thông tin vai trò được cập nhật gần nhất.                            |

**_[3] Ràng buộc (constraint):_**

| Type       | Applicable to     | Description                                                               |
| ---------- | ----------------- | ------------------------------------------------------------------------- |
| **PK**     | `id`              | Khóa chính, định danh duy nhất vai trò, định dạng: `role-ddmmyy-xxxxxxxx` |
| **UNIQUE** | `name`            | Mỗi tên vai trò chỉ xuất hiện một lần.                                    |
| **FK**     | `created_by`      | Tham chiếu đến `Users(id)`.                                               |
| **FK**     | `last_updated_by` | Tham chiếu đến `Users(id)`.                                               |

**_[4] Quy tắc nghiệp vụ (Business Rules)_**

[4.1] Quy tắc "Gán vai trò cho người dùng" và "Nhóm quyền theo vai trò"

```
Mỗi người dùng được gán một vai trò để hệ thống xác định các quyền mà người dùng được phép thực hiện.

Thay vì gán quyền trực tiếp cho từng người dùng, hệ thống gán quyền cho vai trò, sau đó gán vai trò tương ứng cho người dùng.
```

[4.2] Quy tắc "Khởi tạo Role đầu tiên"

```
Cho phép created_by = NULL đối với Role do hệ thống khởi tạo (seed data).

Các Role được tạo thông qua giao diện sau khi hệ thống vận hành phải có created_by tham chiếu đến User đã thực hiện thao tác.

Quy tắc này tránh quan hệ FK vòng bắt buộc giữa Users.role_id và Roles.created_by khi khởi tạo tài khoản và vai trò đầu tiên.
```

### 2.1.4 Role_Permissions (Phân quyền theo vai trò)

**_[1] Ý nghĩa bảng (Description)_**

Là bảng trung gian dùng để thiết lập mối quan hệ nhiều-nhiều giữa Roles và Permissions.

Một vai trò có thể có nhiều quyền và một quyền có thể được gán cho nhiều vai trò khác nhau.

**_[2] Trường dữ liệu (Fields)_**

| Field         | Type    | Nullable | Meaning                        |
| ------------- | ------- | -------- | ------------------------------ |
| role_id       | varchar | No       | Mã vai trò được cấp quyền.     |
| permission_id | varchar | No       | Mã quyền được gán cho vai trò. |

**_[3] Ràng buộc (constraint):_**

| Type      | Applicable to                | Description                           |
| --------- | ---------------------------- | ------------------------------------- |
| **PK**    | (`role_id`, `permission_id`) | Khóa chính phức hợp.                  |
| **FK**    | `role_id`                    | Tham chiếu đến `Roles(id)`.           |
| **FK**    | `permission_id`              | Tham chiếu đến `Permissions(id)`.     |
| **INDEX** | `permission_id`              | Tăng tốc truy vấn vai trò theo quyền. |

**_[4] Quy tắc nghiệp vụ (Business Rules)_**

[4.1] Xác định quyền của vai trò

```
Bảng xác định mỗi vai trò được phép sở hữu những quyền nào trong hệ thống.
```

### 2.1.5 Permissions (Quyền truy cập)

**_[1] Ý nghĩa bảng (Description)_**

Lưu trữ các quyền truy cập cụ thể có thể được cấp cho vai trò trong hệ thống.

Mỗi quyền được hình thành từ sự kết hợp giữa một chức năng Management_Functions và một hành động Actions.

Ví dụ: Một số chi tiết quyền nhỏ trong hệ thống

- Device Management + Add
- Device Management + Edit
- Device Management + Delete
- Device Management + View
- Dashboard + View
- User Management + Add
- User Management + Edit

**_[2] Trường dữ liệu (Fields)_**

| Field       | Type    | Nullable | Meaning                                                    |
| ----------- | ------- | -------- | ---------------------------------------------------------- |
| id          | varchar | No       | Mã định danh duy nhất của quyền trong hệ thống.            |
| function_id | varchar | No       | Mã chức năng mà quyền được áp dụng.                        |
| action_id   | varchar | No       | Mã hành động được phép thực hiện trên chức năng tương ứng. |

**_[3] Ràng buộc (constraint):_**

| Type       | Applicable to                | Description                                                       |
| ---------- | ---------------------------- | ----------------------------------------------------------------- |
| **PK**     | `id`                         | Khóa chính, định danh duy nhất quyền, định dạng: `perm-xxxxxxxx`. |
| **FK**     | `function_id`                | Tham chiếu đến `Management_Functions(id)`.                        |
| **FK**     | `action_id`                  | Tham chiếu đến `Actions(id)`.                                     |
| **UNIQUE** | (`function_id`, `action_id`) | Mỗi cặp chức năng - hành động chỉ tạo ra một quyền duy nhất.      |
| **INDEX**  | `action_id`                  | Tăng tốc truy vấn quyền theo hành động.                           |

**_[4] Quy tắc nghiệp vụ (Business Rules)_**

[4.1] Cấu thành quyền

```
Mỗi quyền được hình thành từ sự kết hợp giữa một chức năng Management_Functions và một hành động Actions.
```

### 2.1.6 Management_Functions (Chức năng quản lý)

**_[1] Ý nghĩa bảng (Description)_**

Lưu trữ danh sách các chức năng hoặc module nghiệp vụ chính có trong hệ thống.

Các chức năng này được sử dụng làm đối tượng để xây dựng quyền truy cập. Một chức năng có thể hỗ trợ nhiều hành động khác nhau tùy thuộc vào nghiệp vụ của hệ thống.

Một số chức năng của hệ thống: Dashboard / Chatbot / Device Management / User Management / Role-Based Access / Task Management / Audit Log

**_[2] Trường dữ liệu (Fields)_**

| Field | Type    | Nullable | Meaning                                                                                     |
| ----- | ------- | -------- | ------------------------------------------------------------------------------------------- |
| id    | varchar | No       | Mã định danh duy nhất của chức năng trong hệ thống.                                         |
| name  | varchar | No       | Tên hiển thị của chức năng nghiệp vụ, được sử dụng để hiển thị trên màn hình quản lý quyền. |

**_[3] Ràng buộc (constraint):_**

| Type       | Applicable to | Description                                                           |
| ---------- | ------------- | --------------------------------------------------------------------- |
| **PK**     | `id`          | Khóa chính, định danh duy nhất chức năng, định dạng: `func-xxxxxxxx`. |
| **UNIQUE** | `name`        | Mỗi tên chức năng chỉ xuất hiện một lần.                              |

**_[4] Quy tắc nghiệp vụ (Business Rules)_**

[4.1] Vai trò của chức năng

```
Các chức năng này được sử dụng làm đối tượng để xây dựng quyền truy cập.

Một chức năng có thể hỗ trợ nhiều hành động khác nhau tùy thuộc vào nghiệp vụ của hệ thống.
```

### 2.1.7 Actions (Hành động được phép)

**_[1] Ý nghĩa bảng (Description)_**

Lưu trữ danh sách các loại hành động mà người dùng có thể được phép thực hiện đối với các chức năng trong hệ thống.

Các hành động được kết hợp với Management_Functions để tạo thành các Permissions cụ thể.

Các hành động hiện tại: Add / Edit / Delete / View / Approve.

**_[2] Trường dữ liệu (Fields)_**

| Field | Type    | Nullable | Meaning                                                                              |
| ----- | ------- | -------- | ------------------------------------------------------------------------------------ |
| id    | varchar | No       | Mã định danh duy nhất của hành động trong hệ thống.                                  |
| name  | varchar | No       | Tên hiển thị của hành động mà người dùng có thể thực hiện trên một chức năng cụ thể. |

**_[3] Ràng buộc (constraint):_**

| Type       | Applicable to | Description                                                           |
| ---------- | ------------- | --------------------------------------------------------------------- |
| **PK**     | `id`          | Khóa chính, định danh duy nhất hành động, định dạng: `acts-xxxxxxxx`. |
| **UNIQUE** | `name`        | Mỗi tên hành động chỉ xuất hiện một lần.                              |

**_[4] Quy tắc nghiệp vụ (Business Rules)_**

[4.1] Kết hợp với chức năng

```
Các hành động được kết hợp với Management_Functions để tạo thành các Permissions cụ thể.

`Execute` không phải action RBAC của người dùng. Khi người dùng gửi yêu cầu cho
Chatbot hoặc tạo Task, hệ thống kiểm tra quyền `Add`; việc các Agent thực thi
workflow phía sau là xử lý nội bộ. Thao tác quyết định thay đổi cấu hình dùng
quyền `Approve` riêng.
```

## 2.2 GROUP 2: NETWORK INVENTORY

Nhóm Network Inventory chịu trách nhiệm quản lý thông tin các thiết bị mạng được sử dụng trong hệ thống, bao gồm thông tin kết nối, thông tin xác thực, thương hiệu và loại thiết bị.

Nhóm này thay thế phương pháp quản lý thông tin thiết bị bằng các file cấu hình tĩnh như .YAML, giúp dữ liệu thiết bị được lưu trữ tập trung trong cơ sở dữ liệu và có thể được quản lý, cập nhật và truy xuất linh hoạt.

Các thông tin trong nhóm Network Inventory được sử dụng bởi Backend và các Agent để xác định thiết bị cần thao tác, lấy thông tin kết nối phù hợp và thực hiện các tác vụ mạng như kiểm tra cấu hình, lấy bảng định tuyến hoặc thay đổi cấu hình thiết bị.

### 2.2.1 Devices (Thiết bị mạng)

**_[1] Ý nghĩa bảng (Description)_**

Lưu trữ thông tin của các thiết bị mạng được quản lý trong hệ thống.

Mỗi bản ghi đại diện cho một thiết bị mạng cụ thể và chứa các thông tin cần thiết để hệ thống hoặc Agent xác định, kết nối và thực hiện thao tác trên thiết bị đó.

**_[2] Trường dữ liệu (Fields)_**

| Field           | Type      | Nullable | Meaning                                                                             |
| --------------- | --------- | -------- | ----------------------------------------------------------------------------------- |
| id              | varchar   | No       | Mã định danh duy nhất của thiết bị mạng trong hệ thống.                             |
| credential_id   | varchar   | Yes      | Mã thông tin xác thực được sử dụng để đăng nhập vào thiết bị.                       |
| brand_id        | varchar   | No       | Mã thương hiệu của thiết bị.                                                        |
| category_id     | varchar   | No       | Mã loại thiết bị.                                                                   |
| created_by      | varchar   | No       | Mã người dùng tạo thiết bị và lưu vào hệ thống.                                     |
| last_updated_by | varchar   | Yes      | Mã người dùng thực hiện lần cập nhật gần nhất đối với thông tin thiết bị .          |
| hostname        | varchar   | No       | Tên định danh hoặc tên hiển thị của thiết bị trong hệ thống và trong mô hình mạng,  |
| host            | varchar   | No       | Địa chỉ IP của thiết bị.                                                            |
| port            | integer   | No       | Số cổng được sử dụng để thiết lập kết nối trên GNS3 hoặc môi trường mạng tương ứng. |
| device_type     | varchar   | No       | Là loại driver/platform mà Brand hỗ trợ.                                            |
| location        | varchar   | Yes      | Thông tin mô tả vị trí vật lý hoặc vị trí logic của thiết bị trong hệ thống mạng.   |
| created_at      | timestamp | No       | Thời điểm thông tin thiết bị được tạo và lưu vào hệ thống.                          |
| last_updated_at | timestamp | Yes      | Thời điểm thông tin thiết bị được cập nhật gần nhất.                                |

**_[3] Ràng buộc (constraint):_**

| Type       | Applicable to     | Description                                                                     |
| ---------- | ----------------- | ------------------------------------------------------------------------------- |
| **PK**     | `id`              | Khóa chính, định danh duy nhất thiết bị, **định dạng:** `devc-ddmmyy-xxxxxxxx`. |
| **FK**     | `credential_id`   | Tham chiếu đến `Credentials(id)`.                                               |
| **FK**     | `brand_id`        | Tham chiếu đến `Brands(id)`.                                                    |
| **FK**     | `category_id`     | Tham chiếu đến `Categories(id)`.                                                |
| **FK**     | `created_by`      | Tham chiếu đến `Users(id)`.                                                     |
| **FK**     | `last_updated_by` | Tham chiếu đến `Users(id)`.                                                     |
| **UNIQUE** | `hostname`        | Mỗi hostname chỉ xuất hiện một lần.                                             |
| **UNIQUE** | (`host`, `port`)  | Mỗi cặp host - port chỉ xuất hiện một lần.                                      |
| **INDEX**  | `brand_id`        | Tăng tốc truy vấn thiết bị theo thương hiệu.                                    |
| **INDEX**  | `category_id`     | Tăng tốc truy vấn thiết bị theo loại.                                           |
| **INDEX**  | `credential_id`   | Tăng tốc truy vấn thiết bị theo credential.                                     |
| **CHECK**  | `port`            | Thuộc khoảng [1, 65535]                                                         |

**_[4] Quy tắc nghiệp vụ (Business Rules)_**

[4.1] Trường `host`

```
Địa chỉ IP của thiết bị, mặc định là 127.0.0.1.
```

[4.2] Trường `device_type`

```
Quy tắc:
    - Danh sách Driver hợp lệ được lấy từ trường Brands.supported_drivers của Brand mà Device thuộc về.
    - Khi tạo hoặc cập nhật Device, người dùng chỉ được chọn Driver nằm trong danh sách supported_drivers của Brand.
    - Backend phải kiểm tra Driver được chọn có được hệ thống hỗ trợ trước khi lưu vào Database.

Khi Brand của Device thay đổi, Backend phải kiểm tra lại `device_type` có còn hợp lệ với Brand mới hay không.

Việc thay đổi danh sách supported_drivers của Brand không tự động thay đổi device_type của các Device đã tồn tại.
```

[4.3] Kiểm tra thiết bị trước khi thực thi

```
Trước khi Agent thực hiện thao tác trên Device, hệ thống phải:
    - Kiểm tra Device tồn tại trong Database.
    - Kiểm tra người dùng có quyền thực hiện thao tác tương ứng.
    - Kiểm tra thông tin kết nối có đầy đủ và hợp lệ.
    - Kiểm tra Credential cần thiết có thể được sử dụng.

Nếu không thỏa mãn điều kiện, hệ thống không được gửi command xuống Device và phải ghi nhận lỗi tại Execution tương ứng.
```

### 2.2.2 Credentials (Thông tin xác thực thiết bị)

**_[1] Ý nghĩa bảng (Description)_**

Lưu trữ thông tin xác thực được sử dụng để đăng nhập và thực hiện thao tác trên các thiết bị mạng.

Thông tin xác thực được tách khỏi bảng Devices nhằm giảm việc lưu trữ lặp lại thông tin đăng nhập, hỗ trợ tái sử dụng cùng một credential cho nhiều thiết bị và tăng khả năng quản lý bảo mật.

Ngoài các thông tin đăng nhập kỹ thuật (`username`, `password`, `secret`), mỗi credential còn có tên hiển thị (`name`) và mô tả (`description`) để người quản trị dễ dàng nhận biết mục đích sử dụng, đặc biệt trong trường hợp nhiều credential có cùng `username` nhưng phục vụ các môi trường hoặc nhóm thiết bị khác nhau.

**_[2] Trường dữ liệu (Fields)_**

| Field           | Type      | Nullable | Meaning                                                                                                        |
| --------------- | --------- | -------- | -------------------------------------------------------------------------------------------------------------- |
| id              | varchar   | No       | Mã định danh duy nhất của bộ thông tin xác thực trong hệ thống.                                                |
| name            | varchar   | No       | Tên hiển thị của credential, giúp người dùng nhận biết mục đích sử dụng.                                       |
| description     | varchar   | Yes      | Mô tả chi tiết hơn về phạm vi, mục đích hoặc ghi chú nội bộ cho credential.                                    |
| username        | varchar   | No       | Tên đăng nhập được sử dụng để xác thực khi hệ thống hoặc Agent kết nối tới thiết bị mạng.                      |
| password        | varchar   | No       | Mật khẩu đăng nhập của thiết bị sau khi đã được mã hóa trước khi lưu vào cơ sở dữ liệu.                        |
| secret          | varchar   | Yes      | Mật khẩu đặc quyền hoặc Enable Secret của thiết bị. Sử dụng khi thiết bị yêu cầu chuyển sang chế độ đặc quyền. |
| encryption_type | varchar   | No       | Xác định phương thức hoặc cơ chế mã hóa được sử dụng cho các thông tin nhạy cảm của credential.                |
| created_by      | varchar   | No       | Mã người dùng tạo credential.                                                                                  |
| last_updated_by | varchar   | Yes      | Mã người dùng thực hiện lần cập nhật gần nhất.                                                                 |
| created_at      | timestamp | No       | Thời điểm bộ thông tin xác thực được tạo trong hệ thống.                                                       |
| last_updated_at | timestamp | No       | Thời điểm thông tin xác thực được cập nhật gần nhất.                                                           |

**_[3] Ràng buộc (constraint):_**

| Type       | Applicable to     | Description                                                                   |
| ---------- | ----------------- | ----------------------------------------------------------------------------- |
| **PK**     | `id`              | Khóa chính, định danh duy nhất credential, định dạng: `cred-ddmmyy-xxxxxxxx`. |
| **FK**     | `created_by`      | Tham chiếu đến `Users(id)`.                                                   |
| **FK**     | `last_updated_by` | Tham chiếu đến `Users(id)`.                                                   |
| **UNIQUE** | `name`            | Mỗi tên credential chỉ xuất hiện một lần.                                     |
| **INDEX**  | `name`            | Tăng tốc tìm kiếm credential theo tên.                                        |
| **INDEX**  | `username`        | Tăng tốc truy vấn credential theo username.                                   |
| **INDEX**  | `created_by`      | Tăng tốc truy vấn credential theo người tạo.                                  |
| **INDEX**  | `last_updated_by` | Tăng tốc truy vấn credential theo người cập nhật.                             |

**_[4] Quy tắc nghiệp vụ (Business Rules)_**

[4.1] Cơ chế "Bảo mật mật khẩu thiết bị"

```
Không lưu mật khẩu dưới dạng plaintext.
Không sử dụng hash đối với mật khẩu thiết bị vì hệ thống cần lấy lại mật khẩu gốc để thực hiện đăng nhập vào thiết bị.
Các thông tin nhạy cảm như password và secret phải được mã hóa có khả năng giải mã (reversible encryption) trước khi lưu vào cơ sở dữ liệu.
```

[4.2] Trường `encryption_type`

```
Xác định phương thức hoặc cơ chế mã hóa được sử dụng cho các thông tin nhạy cảm của credential.
```

[4.3] Tái sử dụng Credential cho nhiều Devices

```
Thông tin xác thực được tách khỏi bảng Devices nhằm giảm việc lưu trữ lặp lại thông tin đăng nhập, hỗ trợ tái sử dụng cùng một credential cho nhiều thiết bị và tăng khả năng quản lý bảo mật.

Khi Credential được cập nhật, các kết nối mới sử dụng Credential đó phải sử dụng thông tin xác thực đã cập nhật.

Việc cập nhật Credential không được làm thay đổi dữ liệu lịch sử của những Execution đã được thực hiện trước đó.
```

[4.4] Quản lý khóa mã hóa Credential

```
Các thông tin nhạy cảm như password và secret phải được mã hóa trước khi lưu vào Database.

Khóa mã hóa không được lưu plaintext trong Database hoặc mã nguồn ứng dụng.

Khóa mã hóa phải được quản lý thông qua môi trường triển khai an toàn hoặc hệ thống quản lý secret/key chuyên dụng.

Chỉ Backend Service hoặc Tool được cấp quyền mới được phép giải mã Credential nhằm phục vụ việc kết nối đến Device.

Hệ thống phải quản lý đầy đủ thông tin cần thiết để giải mã, bao gồm cơ chế mã hóa, định danh khóa và nonce/IV nếu thuật toán yêu cầu.

Có thể lưu những metadata này cùng ciphertext trong encrypted envelope.

Nếu sử dụng encrypted envelope, không bắt buộc tạo cột key_id/nonce/IV riêng.

Khóa giải mã thực tế phải được lưu ngoài Database.
```

[4.5] Bảo vệ Credential trong quá trình thực thi

```
Password và Secret sau khi giải mã chỉ được sử dụng trong phạm vi xử lý kết nối đến Device.

Không được lưu Credential đã giải mã vào:
    - Task_Executions.input.
    - Task_Executions.output.
    - Task_Executions.error_message.
    - Device_Action_Logs.
    - Messages.
    - Log ứng dụng hoặc phản hồi Chat UI.

Các thông tin nhạy cảm phải được loại bỏ hoặc che giấu trước khi ghi nhận dữ liệu runtime và audit.
```

[4.6] Trường `name`

```
Tên hiển thị của credential, dùng để phân biệt các credential có cùng username nhưng khác mục đích sử dụng.

Khuyến nghị đặt tên theo pattern: <Môi trường> - <Nhóm thiết bị> - <Mức quyền>

Ví dụ:
      Lab GNS3 - Cisco - ReadOnly
      Production Core - Full Access
      Backup - Monitoring

Trường name là duy nhất trong hệ thống để tránh nhầm lẫn khi chọn credential gán cho Device.
```

### 2.2.3 Categories (Loại thiết bị mạng)

**_[1] Ý nghĩa bảng (Description)_**

Lưu trữ danh sách các nhóm hoặc loại thiết bị mạng có trong hệ thống.

Bảng này giúp phân loại các thiết bị theo chức năng hoặc vai trò của chúng trong hạ tầng mạng, từ đó hỗ trợ việc quản lý, tìm kiếm và xử lý thiết bị theo từng nhóm.

Ví dụ một số loại thiết bị: Router / Switch / Firewall / Load Balancer / Wireless Controller

**_[2] Trường dữ liệu (Fields)_**

| Field | Type    | Nullable | Meaning                                                                                               |
| ----- | ------- | -------- | ----------------------------------------------------------------------------------------------------- |
| id    | varchar | No       | Mã định danh duy nhất của loại thiết bị trong hệ thống.                                               |
| name  | varchar | No       | Tên hiển thị của loại thiết bị, dùng để phân loại và nhận biết chức năng tổng quát của thiết bị mạng. |

**_[3] Ràng buộc (constraint):_**

| Type       | Applicable to | Description                                                                      |
| ---------- | ------------- | -------------------------------------------------------------------------------- |
| **PK**     | `id`          | Khóa chính, định danh duy nhất loại thiết bị, định dạng: `catg-ddmmyy-xxxxxxxx`. |
| **UNIQUE** | `name`        | Mỗi tên loại thiết bị chỉ xuất hiện một lần.                                     |

### 2.2.4 Brands (Hãng sản xuất thiết bị)

**_[1] Ý nghĩa bảng (Description)_**

Lưu trữ danh sách các thương hiệu hoặc nhà sản xuất của các thiết bị mạng được quản lý trong hệ thống.

Một số thương hiệu: Cisco / MikroTik / Juniper / Huawei / Fortinet

**_[2] Trường dữ liệu (Fields)_**

| Field             | Type    | Nullable | Meaning                                                            |
| ----------------- | ------- | -------- | ------------------------------------------------------------------ |
| id                | varchar | No       | Mã định danh duy nhất của thương hiệu thiết bị trong hệ thống.     |
| name              | varchar | No       | Tên hiển thị của thương hiệu hoặc nhà sản xuất thiết bị mạng.      |
| supported_drivers | JSONB   | Yes      | Danh sách các Driver được hệ thống hỗ trợ đối với Brand tương ứng. |

**_[3] Ràng buộc (constraint):_**

| Type       | Applicable to | Description                                                                |
| ---------- | ------------- | -------------------------------------------------------------------------- |
| **PK**     | `id`          | Khóa chính, định danh duy nhất thương hiệu, định dạng: `brnd-ddmmyy-xxxx`. |
| **UNIQUE** | `name`        | Mỗi tên thương hiệu chỉ xuất hiện một lần.                                 |

**_[4] Quy tắc nghiệp vụ (Business Rules)_**

[4.1] Trường `supported_drivers`

```
Quy tắc:
    - Một Brand có thể hỗ trợ nhiều Driver.
    - Mỗi Driver trong danh sách phải được Backend hỗ trợ.
    - Không cho phép Driver trùng lặp trong cùng một Brand.
    - Khi tạo hoặc cập nhật Device, Backend phải kiểm tra device_type có thuộc supported_drivers của Brand hay không.
    - Driver được chọn cho từng Device được lưu tại Devices.device_type.

supported_drivers chỉ xác định danh sách Driver hợp lệ. Driver thực tế dùng để kết nối được xác định thông qua Devices.device_type.

Việc thay đổi supported_drivers không được tự động thay đổi device_type của các Device đã tồn tại.
```

## 2.3. GROUP 3: AI EXECUTION MANAGEMENT

Nhóm bảng này chịu trách nhiệm quản lý toàn bộ vòng đời xử lý một yêu cầu của người dùng, từ thời điểm yêu cầu được gửi vào hệ thống cho đến khi các Agent hoàn tất quá trình phân tích, điều phối, thực thi và ghi nhận kết quả.

Sau khi người dùng gửi một Message, hệ thống tạo một Task để lưu yêu cầu ban đầu. Planner Agent tiếp nhận Task, phân tích mục tiêu và xây dựng một Execution Plan.

Execution Plan gồm ba thành phần chính:

- Task_Operations: xác định các bước xử lý logic cần thực hiện.
- Operation_Dependencies: xác định quan hệ phụ thuộc giữa các Operation theo mô hình DAG.
- Task_Operation_Devices: xác định các Device liên quan đến từng Operation và quyền truy cập READ hoặc WRITE.

Ngoài Execution Plan, nhóm này còn lưu hai loại dữ liệu runtime phục vụ Chat UI và Human-in-the-Loop:

- Task_Activity_Events: lưu timeline hoạt động của Orchestrator, Agent và Tool để hiển thị quá trình xử lý trong Conversation.
- Operation_Device_Approvals: lưu một yêu cầu và quyết định phê duyệt duy nhất cho từng mapping Operation - Device có tác động thay đổi cấu hình.

Sau khi Execution Plan được tạo, Orchestrator sử dụng các quan hệ dependency để xác định những Operation đang ở trạng thái READY.

Các Operation độc lập có thể được thực thi song song. Đối với một Operation liên quan đến nhiều Device, các Device cũng có thể được xử lý đồng thời tùy theo cơ chế điều phối runtime.

Mọi bước Agent hoặc Tool thực thi được ghi nhận tại Task_Executions. Mọi command thực tế đã được gửi xuống thiết bị, bao gồm cả command đọc và command thay đổi cấu hình, được ghi nhận tại Device_Action_Logs.

Các sự kiện ở mức trình bày workflow được ghi nhận tại Task_Activity_Events. Task_Activity_Events không thay thế Task_Executions hoặc Device_Action_Logs: bảng này chỉ cung cấp timeline có thứ tự cho Chat UI, trong khi hai bảng còn lại vẫn là nguồn dữ liệu kỹ thuật và audit chi tiết.

Flow tổng quát:

```
User Message
      │
      ▼
    Task
      │
      │ status = PENDING
      ▼
Planner Agent
      │
      │ status = PLANNING
      ▼
Execution Plan (by Planner Agent)
      │
      ├── Task_Operations
      ├── Operation_Dependencies
      └── Task_Operation_Devices
      │
      ▼
Orchestrator
      │
      │ Task.status = RUNNING
      ▼
Xác định các Operation READY
      │
      ▼
Operation có Device Mapping?
      │
      ├──────────────── KHÔNG ─────────────────────────────┐
      │                                                    │
      │                                                    ▼
      │                                            Task_Executions
      │                                                    ↓
      │                                 Agent / Tool xử lý logic nội bộ hệ thống
      │                                                    ↓
      │                                              Kết quả xử lý
      │                                                    ↓
      │                                        Cập nhật Task_Operations
      │                                                    │
      │                                                    │
      └──────────────── CÓ ────────────────────────────────┐
                                                           │
                                                           ▼
                                         Xác định các Device của Operation
                                                           │
                                                           ▼
                                                 Kiểm tra access_mode
                                                           │
                         ┌─────────────────────────────────┴──────────────────────────────┐
                         │                                                                │
                        READ                                                            WRITE
                         │                                                                │
                         ▼                                                                ▼
                 Task_Executions                                                  Task_Executions
                         │                                                                │
                         ▼                                                                ▼
                Agent / Tool thực thi                             Đọc / phân tích trạng thái hiện tại của Device nếu cần
                         │                                                                │
                         ▼                                                                ▼
            Có command gửi xuống Device?                                    Có command READ gửi xuống Device?
                   ┌─────┴───────┐                                                        │
                  Có          Không                                                 ┌─────┴─────┐
                   │             │                                                 Có         Không
                   ▼             │                                                  │           │
          Device_Action_Logs     │                                                  ▼           │
                   │             │                                         Device_Action_Logs   │
                   └──────┬──────┘                                                  │           │
                          ▼                                                         └─────┬─────┘
                    Kết quả Device                                                        │
                          │                                                               ▼
                          │                                                     Sinh cấu hình dự kiến
                          │                                                               │
                          │                                                               ▼
                          │                                           Lưu cấu hình dự kiến vào Task_Executions.output
                          │                                                               │
                          │                                                               ▼
                          │                                               Task_Operation_Devices = WAITING_APPROVAL
                          │                                                               │
                          │                                                               ▼
                          │                                           Operation_Device_Approvals = PENDING
                          │                                                               │
                          │                                                               ▼
                          │                                                       Hiển thị cho Human
                          │                                                               │
                          │                                                               ▼
                          │                                                          Human xác nhận
                          │                                                       ┌───────┴───────┐
                          │                                                       │               │
                          │                                                    APPROVE          REJECT
                          │                                                       │               │
                          │                                                       ▼               ▼
                          │                                                Task_Executions     REJECTED
                          │                                                       │               │
                          │                                                       ▼               │
                          │                                               Thực thi cấu hình       │
                          │                                                       │               │
                          │                                                       ▼               │
                          │                                               Device_Action_Logs      │
                          │                                                       │               │
                          └──────────────────────────────┬────────────────────────┴───────────────┘
                                                         ▼
                                 Cập nhật trạng thái từng Task_Operation_Devices
                                                         │
                                                         ▼
                                     Tổng hợp trạng thái Device của Operation
                                                         │
                                                         ▼
                                              Cập nhật Task_Operations
                                                         │
                          ┌──────────────────────────────┘
                          │
                          ▼
               Kiểm tra Operation_Dependencies
                          │
              ┌───────────┴────────────────────┐
              │                                │
     Dependency thỏa mãn             Dependency không thỏa mãn
              │                                │
              ▼                                ▼
    Có Operation mới READY                  SKIPPED
              │                                │
              └──────────────┬─────────────────┘
                             ▼
                  Còn Operation chưa kết thúc?
                      ┌──────┴───────┐
                     Có            Không
                      │              │
                      ▼              ▼
                Orchestrator    Tổng hợp kết quả
                      │              ↓
                      │       Cập nhật trạng thái Task
                      │
                      └──> Xác định các Operation READY
```

Human-in-the-Loop trong phiên bản hiện tại được áp dụng theo rule-based.

Để các bảng trong mục 2.3 thống nhất với nhau, sử dụng cùng một yêu cầu sau: User $\textit{``Lấy routing table của P1 và P2, phân tích kết quả, sau đó nếu phù hợp hãy cấu hình OSPF trên P3.``}$

### 2.3.1 Tasks (Yêu cầu tác vụ)

**_[1] Ý nghĩa bảng (Description)_**

Lưu thông tin của một yêu cầu nguyên bản được tạo ra từ người dùng thông qua giao diện Chat UI.

Mỗi Task đại diện cho một mục tiêu mà hệ thống AI cần xử lý.

Ví dụ: với yêu cầu chung đã được xác định ở trên

```
System tạo:
      Task:
      id = task-011026-0001-0001
      conversation_id = cons-011026-0001
      source_message_id = mesg-011026-0005
      user_id = user-011026-0001
      input_message = "Lấy routing table của P1 và P2, phân tích kết quả, sau đó nếu phù hợp hãy cấu hình OSPF trên P3."
      task_status = PENDING

Sau khi Task được tạo, Planner Agent tiếp nhận yêu cầu và chuyển Task sang trạng thái PLANNING để xây dựng Execution Plan.
```

**_[2] Trường dữ liệu (Fields)_**

| Field             | Type      | Nullable | Meaning                                                                                                    |
| ----------------- | --------- | -------- | ---------------------------------------------------------------------------------------------------------- |
| id                | varchar   | No       | Mã định danh duy nhất của Task. Dùng để truy xuất và liên kết Task với các bảng runtime khác.              |
| conversation_id   | varchar   | No       | Mã Conversation mà Task được tạo ra. Dùng để truy vết Task về đoạn hội thoại giữa User và AI.              |
| source_message_id | varchar   | No       | Mã Message của người dùng đã trực tiếp tạo ra Task.                                                        |
| user_id           | varchar   | No       | Mã User gửi yêu cầu và tạo Task. Dùng cho mục đích phân quyền, audit và theo dõi lịch sử sử dụng hệ thống. |
| input_message     | text      | No       | Nội dung yêu cầu nguyên bản của người dùng trước khi được AI Planner xử lý hoặc chuẩn hóa.                 |
| task_status       | enum      | No       | Trạng thái hiện tại của Task trong vòng đời xử lý.                                                         |
| task_type         | enum      | No       | Đựợc sử dụng để phân loại mục tiêu chính của Task.                                                         |
| started_at        | timestamp | Yes      | Thời điểm Task thực sự bắt đầu được xử lý, giúp phân biệt thời gian chờ khởi chạy với thời gian thực thi.  |
| completed_at      | timestamp | Yes      | Thời điểm Task hoàn tất xử lý.                                                                             |
| created_at        | timestamp | No       | Thời điểm Task được tạo trong hệ thống.                                                                    |

**_[3] Ràng buộc (constraint):_**

| Type       | Applicable to       | Description                                                             |
| ---------- | ------------------- | ----------------------------------------------------------------------- |
| **PK**     | `id`                | Khóa chính, định danh duy nhất Task, định dạng: `task-ddmmyy-xxxxxxxx`. |
| **FK**     | `conversation_id`   | Tham chiếu đến `Conversations(id)`.                                     |
| **FK**     | `source_message_id` | Tham chiếu đến `Messages(id)`.                                          |
| **FK**     | `user_id`           | Tham chiếu đến `Users(id)`.                                             |
| **UNIQUE** | `source_message_id` | Mỗi Message chỉ tạo ra một Task duy nhất.                               |
| **INDEX**  | `conversation_id`   | Tăng tốc truy vấn Task theo Conversation.                               |
| **INDEX**  | `user_id`           | Tăng tốc truy vấn Task theo người dùng.                                 |
| **INDEX**  | `task_status`       | Tăng tốc lọc Task theo trạng thái.                                      |
| **INDEX**  | `task_type`         | Hỗ trợ thống kê và lọc Task theo loại.                                  |
| **CHECK**  | `task_type`         | Thuộc tập giá trị được định nghĩa tại Business Rules [4.8].             |
| **CHECK**  | `started_at`        | Nếu có giá trị thì phải >= `created_at`.                                |
| **CHECK**  | `completed_at`      | Nếu có giá trị thì phải >= `created_at` và >= `started_at` nếu có.      |

**_[4] Quy tắc nghiệp vụ (Business Rules)_**

[4.1] Trường `task_status`

```
Các trạng thái hiện tại gồm:
      - PENDING: Task đã được tạo nhưng Planner Agent chưa bắt đầu phân tích yêu cầu.
      - PLANNING: Planner Agent đang phân tích yêu cầu và xây dựng Execution Plan gồm các Operation, quan hệ dependency và Device mapping.
      - RUNNING: Execution Plan đã được tạo và Orchestrator đang điều phối các Operation. Trạng thái này cũng được duy trì khi một phần Task đang chờ Human xác nhận thao tác WRITE.
      - SUCCESS: Toàn bộ các Operation cần thiết để hoàn thành mục tiêu của Task đã thực thi thành công.
      - PARTIAL_SUCCESS: Một phần Operation đã thực thi thành công nhưng một hoặc nhiều Operation khác FAILED hoặc SKIPPED, khiến Task chỉ hoàn thành được một phần mục tiêu.
      - FAILED: Task không thể hoàn thành mục tiêu do lỗi trong quá trình Agent, Tool hoặc Device thực thi.
      - REJECTED: Task không đạt được mục tiêu do Human từ chối thao tác WRITE bắt buộc tại Task_Operation_Devices và không có kết quả thành công nào đủ để xác định PARTIAL_SUCCESS.
```

[4.2] Trường `completed_at`

```
Có giá trị khi Task kết thúc với SUCCESS, PARTIAL_SUCCESS, FAILED hoặc REJECTED.
```

[4.3] Liên kết với các bảng runtime

```
Task là thực thể cấp cao nhất trong quá trình xử lý AI Runtime, dùng để liên kết:
      - Người dùng tạo yêu cầu.
      - Conversation chứa yêu cầu.
      - Message cụ thể đã tạo ra Task.
      - Các Operation được Planner Agent sinh ra.
      - Các bước Execution của Agent.
      - Các hành động thực tế được gửi xuống thiết bị mạng.
      - Timeline hoạt động của Orchestrator, Agent và Tool.
      - Các yêu cầu và quyết định Human Approval của Operation.
      - Trạng thái tổng thể của toàn bộ quá trình xử lý.
```

[4.4] Điều kiện tạo Task

```
Một Task được tạo từ một Message do USER gửi trong Conversation.

Khi tạo Task, hệ thống phải bảo đảm:
    - source_message_id tham chiếu đến Message có sender_by = USER.
    - Message nguồn thuộc cùng conversation_id của Task.
    - user_id là người dùng sở hữu Conversation tương ứng.
    - input_message lưu nội dung nguyên bản của Message nguồn.

Mỗi source_message_id chỉ được liên kết với một Task duy nhất.

Các Message không yêu cầu Agent thực hiện tác vụ không bắt buộc phải tạo Task.
```

[4.5] Tổng hợp trạng thái Task

```
Task chỉ được xác định trạng thái kết thúc sau khi tất cả Operation thuộc Task đã đạt trạng thái kết thúc.

Các trạng thái kết thúc của Operation gồm: SUCCESS / PARTIAL_SUCCESS / FAILED / SKIPPED

Quy tắc tổng hợp:
    - SUCCESS: Tất cả Operation cần thiết để hoàn thành mục tiêu của Task đều SUCCESS.
    - PARTIAL_SUCCESS: Có ít nhất một Operation SUCCESS hoặc PARTIAL_SUCCESS, nhưng Task không hoàn thành toàn bộ mục tiêu do có Operation FAILED hoặc SKIPPED.
    - FAILED: Task không đạt được mục tiêu và không có kết quả thực thi thành công có thể sử dụng; nguyên nhân chủ yếu là lỗi xử lý hoặc thực thi.
    - REJECTED: Task không đạt được mục tiêu vì một thao tác WRITE bắt buộc bị Human từ chối, và không có kết quả thành công nào đủ để xác định PARTIAL_SUCCESS.

Kết quả tổng hợp phải dựa trên mục tiêu nghiệp vụ và mức độ hoàn thành thực tế, không chỉ dựa trên số lượng Operation.

Nếu tất cả Operation đều SKIPPED hoặc không có Operation nào có thể thực hiện, Task phải được xác định là FAILED với nguyên nhân phù hợp, trừ khi hệ thống có quy tắc nghiệp vụ riêng cho trường hợp đó.
```

[4.6] Thời điểm hoàn thành Task

```
completed_at chỉ có giá trị khi Task chuyển sang trạng thái kết thúc:
    - SUCCESS
    - PARTIAL_SUCCESS
    - FAILED
    - REJECTED

Khi Task đang PENDING, PLANNING hoặc RUNNING:
    - completed_at = NULL.

Sau khi Task đã kết thúc, không được tự động chuyển về trạng thái đang xử lý nếu không có cơ chế thực thi lại được xác định rõ.
```

[4.7] Kiểm tra quyền khi thực thi Task

```
Việc người dùng được phép tạo Task không đồng nghĩa với việc
người dùng được phép thực hiện mọi Operation do Planner sinh ra.

Trước khi thực thi từng Operation, hệ thống phải kiểm tra
quyền tương ứng với hành động và Device được tác động.

Đối với Operation WRITE, hệ thống phải kiểm tra quyền
tại thời điểm thực thi, kể cả khi Task đã được tạo
và lập kế hoạch trước đó.
```

[4.8] Trường `task_type`

```
Các giá trị gồm:
    - UNCLASSIFIED: Task chưa được phân loại.
    - INFORMATION_RETRIEVAL: Thu thập thông tin mạng.
    - DIAGNOSIS: Phân tích hoặc chẩn đoán sự cố.
    - CONFIGURATION: Thực hiện cấu hình thiết bị mạng.
    - REMEDIATION: Khắc phục sự cố mạng.
    - COMPOSITE: Task có nhiều mục tiêu thuộc các loại khác nhau.

Khi Backend tạo Task:
    - task_type mặc định = UNCLASSIFIED.

Khi Planner Agent phân tích Task:
    - Xác định task_type từ yêu cầu của người dùng.
    - Chỉ được chọn giá trị thuộc tập enum đã định nghĩa.
    - Backend kiểm tra và cập nhật task_type vào Database.

Nếu Planner không xác định được loại Task:
    - Giữ UNCLASSIFIED.
    - Không tự động gán loại Task không có cơ sở.

Các bước xử lý cụ thể được xác định thông qua Task_Operations.operation_intent.
```

[4.9] Trường `started_at`

```
started_at được ghi nhận khi Planner bắt đầu xử lý Task.

Khi Task ở trạng thái PENDING: started_at = NULL.
Khi Task ở trạng thái PLANNING hoặc RUNNING: started_at phải có giá trị.

Khi có đầy đủ các timestamp:
    created_at <= started_at <= completed_at.

Latency end-to-end được tính từ created_at đến completed_at;
Latency xử lý (không tính thời gian chờ bắt đầu) được tính từ
started_at đến completed_at. Hai chỉ số phải được đặt tên phân biệt.
```

### 2.3.2 Task_Operations (Các bước xử lý tác vụ)

**_[1] Ý nghĩa bảng (Description)_**

Lưu các Operation logic được tạo ra bởi Planner Agent sau khi phân tích một Task.

Một Task có thể chứa nhiều mục tiêu, do đó Planner Agent chia Task thành các Operation logic để các Agent chuyên biệt xử lý.

Operation không đại diện cho command cụ thể trên thiết bị mà chỉ đại diện cho ý định xử lý `intent`.

Ví dụ:

```
Planner Agent phân tích yêu cầu và tạo ba Operation:

      OP1
            intent = GET_ROUTING_TABLE
            display_order = 1

      OP2
            intent = ANALYZE_ROUTING_DATA
            display_order = 2

      OP3
            intent = CONFIGURE_OSPF
            display_order = 3
```

**_[2] Trường dữ liệu (Fields)_**

| Field                | Type      | Nullable | Meaning                                                                                                           |
| -------------------- | --------- | -------- | ----------------------------------------------------------------------------------------------------------------- |
| id                   | varchar   | No       | Mã định danh duy nhất của Operation. Đại diện cho một bước xử lý logic trong Task.                                |
| task_id              | varchar   | No       | Mã Task cha mà Operation thuộc về.                                                                                |
| operation_intent     | varchar   | No       | Ý định xử lý đã được chuẩn hóa bởi Planner Agent.                                                                 |
| display_order        | integer   | No       | Thứ tự sắp xếp của Operation trong kế hoạch xử lý do Planner tạo ra, phục vụ hiển thị và truy vết các bước xử lý. |
| operation_status     | enum      | No       | Trạng thái xử lý của Operation.                                                                                   |
| operation_parameters | JSONB     | Yes      | Các tham số được AI Planner trích xuất từ yêu cầu người dùng.                                                     |
| created_at           | timestamp | No       | Thời điểm Operation được tạo sau khi Planner hoàn thành việc lập kế hoạch.                                        |
| completed_at         | timestamp | Yes      | Thời điểm Operation hoàn thành xử lý.                                                                             |

**_[3] Ràng buộc (constraint):_**

| Type       | Applicable to                | Description                                                                        |
| ---------- | ---------------------------- | ---------------------------------------------------------------------------------- |
| **PK**     | `id`                         | Khóa chính, định danh duy nhất Operation, định dạng: `oper-ddmmyy-xxxxxxxx`.       |
| **FK**     | `task_id`                    | Tham chiếu đến `Tasks(id)`.                                                        |
| **UNIQUE** | (`task_id`, `display_order`) | Mỗi cặp task - display_order là duy nhất.                                          |
| **INDEX**  | `task_id`                    | Tăng tốc truy vấn Operation theo Task.                                             |
| **INDEX**  | `operation_status`           | Tăng tốc lọc Operation theo trạng thái.                                            |
| **CHECK**  | `operation_status`           | Thuộc tập `PENDING`, `RUNNING`, `SUCCESS`, `PARTIAL_SUCCESS`, `FAILED`, `SKIPPED`. |

**_[4] Quy tắc nghiệp vụ (Business Rules)_**

[4.1] Trường `operation_status`

```
Các trạng thái hiện tại gồm:
      - PENDING: Operation đã được tạo nhưng chưa bắt đầu xử lý.
      - RUNNING: Operation đang được Agent hoặc Tool xử lý, bao gồm các bước đọc, phân tích, sinh cấu hình hoặc thực thi cấu hình đã được phê duyệt.
      - SUCCESS: Operation đã hoàn thành toàn bộ mục tiêu cần thiết.
      - PARTIAL_SUCCESS: Operation hoàn thành một phần mục tiêu nhưng không hoàn thành toàn bộ yêu cầu, một hoặc nhiều Device khác FAILED, REJECTED hoặc SKIPPED.
      - FAILED: Operation không hoàn thành do lỗi xử lý hoặc thực thi.
      - SKIPPED: Operation không được thực thi do điều kiện dependency không được thỏa mãn bởi một Operation trước đó đã kết thúc.
```

[4.2] Trường `display_order`

```
Không quyết định thứ tự thực thi; quan hệ phụ thuộc và điều kiện thực thi giữa các Operation được xác định thông qua bảng Operation_Dependencies.
```

[4.3] Trường `operation_intent`

```
Đại diện cho ý định xử lý đã được chuẩn hóa bởi Planner Agent.
Operation không đại diện cho command cụ thể trên thiết bị mà chỉ đại diện cho ý định xử lý.
Ví dụ: GET_ROUTING_TABLE, CHECK_OSPF_NEIGHBOR, CONFIGURE_INTERFACE, ...
```

[4.4] Trường `operation_parameters`

```
Các tham số được AI Planner trích xuất từ yêu cầu người dùng, phục vụ cho Agent khi thực thi, không bao gồm thông tin ánh xạ thiết bị.
Ví dụ: interface_name, area_id, network_address, ...
```

[4.5] Cách "Xác định Operation READY"

```
READY là trạng thái logic do Orchestrator xác định tại runtime, không phải giá trị được lưu trong operation_status.

Một Operation được xem là READY khi:
    - operation_status = PENDING.
    - Tất cả dependency bắt buộc đã được thỏa mãn.
    - Task chứa Operation đang ở trạng thái RUNNING.
    - Operation chưa được một Worker khác nhận xử lý.

Operation không có dependency được xem là đủ điều kiện READY sau khi Execution Plan hợp lệ và Task bắt đầu RUNNING.

Orchestrator phải bảo đảm một Operation không bị nhận thực thi trùng lặp bởi nhiều Worker.
```

[4.6] Operation không thao tác trực tiếp trên Device

```
Một Operation có thể không có bản ghi tương ứng trong Task_Operation_Devices.

Trường hợp này áp dụng cho các Operation chỉ thực hiện logic nội bộ như:
    - Phân tích dữ liệu.
    - Tổng hợp kết quả.
    - Đánh giá thông tin thu thập được.
    - Sinh báo cáo hoặc kết luận.

Trạng thái của Operation được xác định từ kết quả các Task_Executions tương ứng.

Không tạo Device_Action_Logs nếu Operation không gửi command thực tế xuống Device.
```

### 2.3.3 Task_Operation_Devices (Thiết bị tham gia xử lý tác vụ)

**_[1] Ý nghĩa bảng (Description)_**

Lưu quan hệ giữa một Operation và các thiết bị mạng mà Operation đó cần xử lý. Vì một Operation có thể liên quan tới nhiều Device.

Ví dụ:

```
Planner Agent ánh xạ Device:

      OP1 - GET_ROUTING_TABLE
      P1
            device_role = SOURCE
            access_mode = READ

      P2
            device_role = SOURCE
            access_mode = READ


      OP2 - ANALYZE_ROUTING_DATA
      Không yêu cầu truy cập trực tiếp Device.


      OP3 - CONFIGURE_OSPF
      P3
            device_role = TARGET
            access_mode = WRITE

Do P1 và P2 thuộc cùng OP1 và đều có access_mode = READ, Orchestrator có thể xử lý hai Device song song:

            ┌── P1
      OP1 ──────┤
            └── P2
```

**_[2] Trường dữ liệu (Fields)_**

| Field                   | Type      | Nullable | Meaning                                                                                                  |
| ----------------------- | --------- | -------- | -------------------------------------------------------------------------------------------------------- |
| id                      | varchar   | No       | Mã định danh của bản ghi mapping giữa Operation và Device.                                               |
| operation_id            | varchar   | No       | Mã Operation cần thực hiện trên thiết bị.                                                                |
| device_id               | varchar   | No       | Mã Devices được Operation tác động tới.                                                                  |
| operation_device_status | enum      | No       | Trạng thái xử lý của Operation trên Device cụ thể,.                                                      |
| device_role             | enum      | No       | Vai trò của thiết bị trong Operation, dùng để xác định cách thiết bị được sử dụng trong quá trình xử lý. |
| access_mode             | enum      | No       | Quyền thao tác mà Agent được phép thực hiện trên Device.                                                 |
| error_message           | text      | Yes      | Thông tin lỗi xảy ra khi xử lý Operation trên Device cụ thể.                                             |
| started_at              | timestamp | Yes      | Thời điểm bắt đầu thực hiện Operation trên Device.                                                       |
| completed_at            | timestamp | Yes      | Thời điểm hoàn thành Operation trên Device.                                                              |

**_[3] Ràng buộc (constraint):_**

| Type       | Applicable to                 | Description                                                                             |
| ---------- | ----------------------------- | --------------------------------------------------------------------------------------- |
| **PK**     | `id`                          | Khóa chính, định danh duy nhất bản ghi mapping, định dạng: `oper-devv-ddmmyy-xxxxxxxx`. |
| **FK**     | `operation_id`                | Tham chiếu đến `Task_Operations(id)`.                                                   |
| **FK**     | `device_id`                   | Tham chiếu đến `Devices(id)`.                                                           |
| **UNIQUE** | (`operation_id`, `device_id`) | Mỗi cặp Operation - Device chỉ xuất hiện một lần.                                       |
| **INDEX**  | `operation_id`                | Tăng tốc truy vấn Device theo Operation.                                                |
| **INDEX**  | `device_id`                   | Tăng tốc truy vấn Operation theo Device.                                                |
| **INDEX**  | `operation_device_status`     | Tăng tốc lọc theo trạng thái xử lý trên Device.                                         |

**_[4] Quy tắc nghiệp vụ (Business Rules)_**

[4.1] Trường `operation_device_status`

```
Các trạng thái hiện tại gồm:
      - PENDING: chưa xử lý
      - WAITING_APPROVAL: Agent đã tạo cấu hình dự kiến và đang chờ Human xác nhận thao tác WRITE.
      - RUNNING: đang xử lý trên Device. READ không cần Approval; WRITE có thể đang đọc/phân tích/sinh cấu hình hoặc thực thi cấu hình đã duyệt.
      - SUCCESS: thực thi thành công
      - FAILED: thực thi thất bại
      - REJECTED: Human từ chối thực hiện cấu hình
      - SKIPPED: Operation không được thực thi do điều kiện dependency không được thỏa mãn bởi một Operation trước đó đã kết thúc
```

[4.2] Trường `device_role`

```
Các giá trị hiện tại gồm:
      - SOURCE: Thiết bị cung cấp dữ liệu đầu vào cho Operation.
      - TARGET: Thiết bị là đối tượng chính mà Operation cần thực hiện hoặc thay đổi.
      - CONTEXT: Thiết bị chỉ cung cấp thông tin bổ sung để Agent phân tích, không phải đối tượng thao tác chính.
```

[4.3] Trường `access_mode`

```
Các giá trị hiện tại gồm:
      READ: Hệ thống được phép tự động thực thi đọc thông tin/config/status từ Device.
      WRITE: Operation được phép thực hiện các bước đọc/phân tích cần thiết để xây dựng cấu hình dự kiến → Task_Operation_Device chuyển sang WAITING_APPROVAL → Human phải xác nhận → APPROVE: hệ thống mới thực thi → REJECT: không gửi command xuống thiết bị.
```

[4.4] Tổng hợp trạng thái xử lý trên nhiều Device

```
Một Operation có thể liên kết với nhiều Device.

Trạng thái tổng thể của Operation phải được xác định dựa trên kết quả xử lý của tất cả Device liên quan.

Đối với Operation có nhiều Device:
    - Nếu tất cả Device SUCCESS:
      Operation = SUCCESS.

    - Nếu có ít nhất một Device SUCCESS và có Device FAILED, REJECTED hoặc SKIPPED:
      Operation = PARTIAL_SUCCESS, khi không còn Device đang xử lý hoặc chờ phê duyệt.

    - Nếu tất cả Device FAILED:
      Operation = FAILED.

    - Nếu tất cả Device REJECTED:
      Operation = FAILED.

    - Nếu không có Device SUCCESS và có cả FAILED, REJECTED hoặc SKIPPED:
      Operation phải được xác định theo nguyên nhân chính khiến mục tiêu không thể hoàn thành.

    - Nếu còn Device WAITING_APPROVAL:
      Operation chưa được kết thúc.

    - Nếu còn Device RUNNING:
      Operation chưa được kết thúc.

Kết quả cuối cùng còn phải xét đến các bước Execution cấp Operation nếu Operation có xử lý logic bổ sung.
```

[4.5] Điều kiện WRITE trên Device

```
Với access_mode = WRITE:
    Bước 1: Agent được phép thực hiện các command READ cần thiết nhằm kiểm tra trạng thái và cấu hình hiện tại của Device.
    Bước 2: Agent sinh cấu hình dự kiến và lưu tại Task_Executions.output.
    Bước 3: Device chuyển sang WAITING_APPROVAL.
    Bước 4: Human có quyền phù hợp kiểm tra cấu hình dự kiến.
    Bước 5:
      - Nếu APPROVE, Backend xác thực quyết định phê duyệt và cho phép Agent thực thi đúng cấu hình đã được duyệt.
      - Nếu REJECT, Device chuyển sang REJECTED và không gửi command WRITE xuống Device.

Không được thực thi command WRITE khi chưa có quyết định APPROVE hợp lệ cho chính xác nội dung cấu hình dự kiến.
```

[4.6] Quan hệ giữa device_role và access_mode

```
SOURCE: Device được sử dụng để cung cấp dữ liệu đầu vào.
TARGET: Device là đối tượng chính mà Operation cần xử lý hoặc thay đổi.
CONTEXT: Device cung cấp thông tin bổ sung phục vụ phân tích.

Quy định:
    - SOURCE thông thường sử dụng READ.
    - CONTEXT chỉ được sử dụng READ.
    - TARGET có thể sử dụng READ hoặc WRITE.

Mọi Device có access_mode = WRITE phải được xem là đối tượng có khả năng bị thay đổi trạng thái hoặc cấu hình, và phải tuân thủ cơ chế Human Approval.
```

[4.7] Thời gian và kết quả xử lý Device

```
started_at được ghi nhận khi hệ thống bắt đầu xử lý Operation trên Device.

completed_at chỉ được ghi nhận khi Device đạt trạng thái kết thúc:
    - SUCCESS
    - FAILED
    - REJECTED
    - SKIPPED

Khi Device đang PENDING, RUNNING hoặc WAITING_APPROVAL, completed_at phải bằng NULL.

Nếu Device FAILED, error_message phải ghi nhận thông tin lỗi phù hợp để phục vụ truy vết.
```

[4.8] Ràng buộc Human Approval

```
Approval chỉ áp dụng với access_mode = WRITE.

Task_Operation_Devices chỉ lưu trạng thái xử lý của mapping Operation - Device, không lưu quyết định Approval.

Yêu cầu, người quyết định, thời điểm quyết định, thời hạn và snapshot nội dung được duyệt phải lưu tại Operation_Device_Approvals.

Khi Approval Request đang PENDING, Task_Operation_Device tương ứng giữ trạng thái WAITING_APPROVAL.

Khi Approval Request được APPROVED, Orchestrator mới được chuyển mapping sang RUNNING để thực thi WRITE.

Khi Approval Request bị REJECTED hoặc EXPIRED, không được gửi command WRITE xuống Device và mapping được cập nhật theo policy tương ứng.

Backend phải kiểm tra quyền phê duyệt tại thời điểm người dùng quyết định.

Những điều kiện liên quan đến quyền/quan hệ ở bảng khác phải được kiểm tra ở tầng Backend hoặc cơ chế tương đương, không thể bảo đảm chỉ bằng CHECK của một bảng.
```

[4.9] Hiệu lực của cấu hình được phê duyệt

```
Trước khi gửi command WRITE, Backend phải tính hash của nội dung chuẩn bị thực thi bằng cùng thuật toán và quy tắc chuẩn hóa đã dùng khi tạo Operation_Device_Approvals.request_hash.

Chỉ thực thi nếu hash khớp và quyết định phê duyệt còn hiệu lực.

Nếu nội dung cấu hình dự kiến thay đổi:
    - Không tái sử dụng phê duyệt cũ.
    - Không tạo yêu cầu phê duyệt lần hai cho Task_Operation_Device hiện tại.
    - Phải hủy Operation hiện tại và lập Operation cùng Task_Operation_Device mới nếu vẫn cần thực thi nội dung đã thay đổi.

Mỗi Task_Operation_Device chỉ được có tối đa một Operation_Device_Approval. Quyết định đã hoàn tất là quyết định cuối cùng và không được ghi đè.
```

### 2.3.4 Operation_Dependencies (Quan hệ phụ thuộc giữa các bước xử lý)

**_[1] Ý nghĩa bảng (Description)_**

Lưu quan hệ phụ thuộc giữa các Task_Operations trong cùng một Task, phục vụ việc xây dựng và thực thi workflow theo mô hình DAG — Directed Acyclic Graph.

Ví dụ:

```
Planner tạo dependency:
      OP1 GET_ROUTING_TABLE
            ↓
      OP2 ANALYZE_ROUTING_DATA
            ↓
      OP3 CONFIGURE_OSPF

Dữ liệu:
      operation_id = OP2
      depends_on_operation_id = OP1
      dependency_type = ON_SUCCESS

      operation_id = OP3
      depends_on_operation_id = OP2
      dependency_type = ON_SUCCESS

Ý nghĩa:
      OP1 phải SUCCESS
      ↓
      OP2 mới READY

      OP2 phải SUCCESS
      ↓
      OP3 mới READY

Nếu:
      OP1 = FAILED

thì:
      OP2 = SKIPPED
      OP3 = SKIPPED

vì dependency ON_SUCCESS không được thỏa mãn.
```

**_[2] Trường dữ liệu (Fields)_**

| Field                   | Type      | Nullable | Meaning                                                                                                                   |
| ----------------------- | --------- | -------- | ------------------------------------------------------------------------------------------------------------------------- |
| id                      | varchar   | No       | Mã định danh duy nhất của quan hệ phụ thuộc giữa hai Operation.                                                           |
| operation_id            | varchar   | No       | Mã Operation đang phụ thuộc vào một Operation khác. Operation này chỉ được thực thi khi dependency tương ứng đã thỏa mãn. |
| depends_on_operation_id | varchar   | No       | Mã Operation mà operation_id phải chờ hoặc phụ thuộc vào trước khi có thể tiếp tục thực thi.                              |
| dependency_type         | enum      | No       | Xác định điều kiện cần thỏa mãn từ Operation phía trước để Operation phía sau được phép thực thi.                         |
| created_at              | timestamp | No       | Thời điểm quan hệ dependency được Planner hoặc Backend tạo và lưu vào hệ thống.                                           |

**_[3] Ràng buộc (constraint):_**

| Type       | Applicable to                               | Description                                                                          |
| ---------- | ------------------------------------------- | ------------------------------------------------------------------------------------ |
| **PK**     | `id`                                        | Khóa chính, định danh duy nhất quan hệ phụ thuộc, định dạng: `opdp-ddmmyy-xxxxxxxx`. |
| **FK**     | `operation_id`                              | Tham chiếu đến `Task_Operations(id)`.                                                |
| **FK**     | `depends_on_operation_id`                   | Tham chiếu đến `Task_Operations(id)`.                                                |
| **UNIQUE** | (`operation_id`, `depends_on_operation_id`) | Mỗi cặp quan hệ phụ thuộc chỉ xuất hiện một lần.                                     |
| **INDEX**  | `operation_id`                              | Tăng tốc truy vấn dependency theo Operation.                                         |
| **INDEX**  | `depends_on_operation_id`                   | Tăng tốc truy vấn Operation phụ thuộc.                                               |

**_[4] Quy tắc nghiệp vụ (Business Rules)_**

[4.1] Trường `dependency_type`

```
Các giá trị hiện tại gồm:
      - ON_SUCCESS: Operation phụ thuộc chỉ được READY khi Operation phía trước kết thúc với trạng thái SUCCESS.
      - ON_COMPLETION: Operation phụ thuộc được READY khi Operation phía trước đã kết thúc, bất kể kết quả SUCCESS, PARTIAL_SUCCESS, FAILED hoặc SKIPPED.
```

[4.2] Mô hình DAG - Directed Acyclic Graph

```
Bảng này phục vụ việc xây dựng và thực thi workflow theo mô hình DAG. Một Operation có thể:
      - không phụ thuộc Operation nào;
      - phụ thuộc một Operation;
      - phụ thuộc nhiều Operation khác.
```

[4.3] Xác định Operation READY

```
Orchestrator sử dụng bảng này để xác định:
      - Operation nào có thể thực thi ngay;
      - Operation nào phải chờ Operation khác hoàn thành;
      - những Operation nào độc lập và có thể chạy song song;
      - điều kiện dependency đã được thỏa mãn hay chưa.
```

[4.4] Ràng buộc quan hệ phụ thuộc

```
Mỗi quan hệ dependency phải thỏa mãn các điều kiện:
    - operation_id và depends_on_operation_id phải tồn tại.
    - Hai Operation phải thuộc cùng một Task.
    - Một Operation không được phụ thuộc chính nó.
    - Không được tồn tại hai dependency trùng lặp.
    - Toàn bộ dependency trong một Task phải tạo thành đồ thị có hướng không chu trình (DAG).

Ví dụ dependency không hợp lệ:
    OP1 → OP2
    OP2 → OP3
    OP3 → OP1

Backend phải kiểm tra DAG trước khi cho phép Orchestrator bắt đầu thực thi Execution Plan.
```

[4.5] Operation có nhiều dependency

```
Một Operation có thể phụ thuộc nhiều Operation khác.

Trong phiên bản hiện tại, các dependency được kết hợp theo cơ chế AND.

Operation chỉ được READY khi tất cả dependency được khai báo đều thỏa mãn điều kiện dependency_type.

Ví dụ: Giẳ sử OP3 phụ thuộc OP1 và OP2.
      Nếu OP1 = SUCCESS và OP2 = SUCCESS:
            --> OP3 có thể READY.
      Nếu OP1 = SUCCESS nhưng OP2 vẫn RUNNING:
            --> OP3 tiếp tục PENDING.
```

[4.6] Xử lý dependency không được thỏa mãn

```
Với dependency_type = ON_SUCCESS:
    Operation phía trước phải đạt SUCCESS.
    Nếu Operation phía trước kết thúc với:
      - PARTIAL_SUCCESS
      - FAILED
      - SKIPPED
    --> Dependency ON_SUCCESS không được thỏa mãn.

Với dependency_type = ON_COMPLETION:
    Dependency được thỏa mãn khi Operation phía trước đã đạt bất kỳ trạng thái kết thúc nào.

Khi một dependency bắt buộc không thể được thỏa mãn, Operation phụ thuộc phải chuyển sang SKIPPED, trừ khi vẫn còn một cơ chế xử lý thay thế được Execution Plan cho phép một cách rõ ràng.

Việc SKIPPED một Operation phải được tiếp tục lan truyền đến các Operation phụ thuộc phía sau theo điều kiện tương ứng.
```

### 2.3.5 Task_Executions (Lịch sử thực thi tác vụ)

**_[1] Ý nghĩa bảng (Description)_**

Lưu lại lịch sử từng bước thực thi của Agent trong quá trình xử lý Task.

Một Operation có thể cần nhiều bước execution.

Thứ tự logic của bước Execution trong phạm vi đối tượng xử lý tương ứng. Nếu Execution thuộc một Operation thì thứ tự được xác định trong Operation đó; nếu `operation_id` = `NULL` thì thứ tự được xác định trong phạm vi Task. Không dùng trường này để xác định dependency giữa các Operation.

Bảng này giúp theo dõi:

- Agent nào được gọi.
- Tool nào được sử dụng.
- Input/Output của từng bước.
- Thời gian xử lý.
- Lỗi xảy ra ở bước nào.

Ví dụ

```
OP1 – READ trên P1 và P2

Orchestrator xác định OP1 đang READY.

Có thể tạo Execution cho từng Device:

      Execution 1
            operation_id = OP1
            operation_device = P1
            agent_name = network-agent
            tool_name = execute_command
            input = "show ip route"
            status = SUCCESS


      Execution 2
            operation_id = OP1
            operation_device = P2
            agent_name = network-agent
            tool_name = execute_command
            input = "show ip route"
            status = SUCCESS

P1 và P2 có thể được chạy đồng thời.

Sau khi hai Device thành công:

      OP1 = SUCCESS

OP2 – Phân tích không thao tác Device

      Execution 3
            operation_id = OP2
            operation_device_id = NULL
            agent_name = analyst-agent
            tool_name = NULL hoặc tool phân tích tương ứng
            input =
                  routing table P1
                  routing table P2
            output =
                  kết quả phân tích mạng
            status = SUCCESS

OP2 không gửi command trực tiếp xuống Device nên không tạo Device_Action_Logs.

OP3 – WRITE trên P3

Khi OP2 thành công:

      OP3 = READY

Agent có thể thực hiện các bước READ cần thiết để kiểm tra trạng thái P3, sau đó sinh cấu hình dự kiến:

      Execution 4
            operation_id = OP3
            operation_device = P3
            agent_name = network-agent
            tool_name = generate_config
            output =
            {
                  "proposed_commands": [
                        "configure terminal",
                        "router ospf 1",
                        "network 10.0.0.0 0.0.0.255 area 0"
                  ]
            }
            status = SUCCESS

Sau khi cấu hình dự kiến được tạo:

      OP3 = RUNNING
      P3  = WAITING_APPROVAL

Human xem cấu hình.

Nếu Human:

      APPROVE

hệ thống tạo Execution tiếp theo:

      Execution 5
            operation_id = OP3
            operation_device = P3
            agent_name = network-agent
            tool_name = execute_config

            status = RUNNING

Sau khi cấu hình thành công:

      Execution 5 = SUCCESS
      P3          = SUCCESS
      OP3         = SUCCESS
      TASK01      = SUCCESS

Nếu Human:

      REJECT

thì:

      P3    = REJECTED
      OP3   = FAILED
      TASK01 = PARTIAL_SUCCESS

vì OP1 và OP2 đã thực thi thành công nhưng mục tiêu cấu hình P3 không được thực hiện.
```

**_[2] Trường dữ liệu (Fields)_**

| Field               | Type       | Nullable | Meaning                                                                                                                                |
| ------------------- | ---------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| id                  | varchar    | No       | Mã định danh duy nhất của một lần thực thi Agent.                                                                                      |
| task_id             | varchar    | No       | Mã Task mà Execution thuộc về.                                                                                                         |
| operation_id        | varchar    | Yes      | Mã Operation mà Execution đang xử lý.                                                                                                  |
| operation_device_id | varchar    | Yes      | Mapping giữa Operation và Device mà Execution đang tác động tới                                                                        |
| agent_name          | varchar    | No       | Tên Agent thực hiện bước xử lý. Agent không lưu trong Database mà được quản lý bằng code `src/app/agents`.                             |
| tool_name           | varchar    | Yes      | Tên Tool được Agent sử dụng trong quá trình thực thi. Tool không lưu trong Database mà được quản lý bằng code`src/app/tools`.          |
| step_order          | integer    | No       | Thứ tự logic của bước Execution trong phạm vi Operation, phục vụ hiển thị và truy vết. Không dùng trường này để quyết định dependency. |
| input               | JSONB/text | Yes      | Dữ liệu đầu vào của bước thực thi, bao gồm request hoặc parameter truyền vào Agent/Tool.                                               |
| output              | JSONB/text | Yes      | Kết quả trả về sau khi Agent hoặc Tool hoàn thành bước xử lý                                                                           |
| execution_status    | enum       | No       | Trạng thái Execution.                                                                                                                  |
| error_message       | text       | Yes      | Nội dung lỗi nếu Execution thất bại.                                                                                                   |
| started_at          | timestamp  | Yes      | Thời điểm Agent bắt đầu thực hiện bước này.                                                                                            |
| completed_at        | timestamp  | Yes      | Thời điểm Agent hoàn thành bước này.                                                                                                   |
| duration_ms         | bigint     | Yes      | Tổng thời gian thực thi của bước, tính bằng milliseconds, được tính từ started_at đến completed_at.                                    |
| created_at          | timestamp  | No       | Thời điểm tạo bản ghi Execution.                                                                                                       |

**_[3] Ràng buộc (constraint):_**

| Type      | Applicable to         | Description                                                                  |
| --------- | --------------------- | ---------------------------------------------------------------------------- |
| **PK**    | `id`                  | Khóa chính, định danh duy nhất Execution, định dạng: `exec-ddmmyy-xxxxxxxx`. |
| **FK**    | `task_id`             | Tham chiếu đến `Tasks(id)`.                                                  |
| **FK**    | `operation_id`        | Tham chiếu đến `Task_Operations(id)`.                                        |
| **FK**    | `operation_device_id` | Tham chiếu đến `Task_Operation_Devices(id)`.                                 |
| **INDEX** | `task_id`             | Tăng tốc truy vấn Execution theo Task.                                       |
| **INDEX** | `operation_id`        | Tăng tốc truy vấn Execution theo Operation.                                  |
| **INDEX** | `agent_name`          | Tăng tốc truy vấn Execution theo Agent.                                      |
| **INDEX** | `execution_status`    | Tăng tốc lọc Execution theo trạng thái.                                      |

**_[4] Quy tắc nghiệp vụ (Business Rules)_**

[4.1] Trường `agent_name`

```
Là string vì Agent không quản lý trong DB, Các Agent được triển khai bằng code trong src/app/agents.
Phiên bản hiện tại gồm:
      - orcherstrtor-agent
      - planner-agent
      - network-agent
      - analyst-agent
```

[4.2] Trường `tool_name`

```
Tool không lưu trong Database mà được quản lý bằng code src/app/tools.
```

[4.3] Trường `step_order`

```
Thứ tự logic của bước Execution trong phạm vi đối tượng xử lý tương ứng.
Nếu Execution thuộc một Operation thì thứ tự được xác định trong Operation đó;
nếu operation_id = NULL thì thứ tự được xác định trong phạm vi Task.
Không dùng trường này để xác định dependency giữa các Operation.
```

[4.4] Trường `execution_status`

```
Các trạng thái hiện tại gồm:
      - PENDING: Execution đã được tạo nhưng Agent hoặc Tool chưa bắt đầu thực hiện bước xử lý.
      - RUNNING: Agent hoặc Tool đang thực hiện bước xử lý tương ứng.
      - SUCCESS: Agent hoặc Tool đã hoàn thành bước xử lý thành công và kết quả được ghi nhận trong output nếu có.
      - FAILED: Execution không hoàn thành thành công do lỗi trong quá trình Agent hoặc Tool xử lý. Thông tin lỗi được ghi nhận trong error_message.
```

[4.5] Trường `duration_ms`

```
Tổng thời gian thực thi của bước, tính bằng milliseconds, được tính từ started_at đến completed_at.
```

[4.6] Tính nhất quán giữa Task, Operation và Device

```
Khi tạo Task_Execution, hệ thống phải bảo đảm:

    - task_id tham chiếu đến Task hợp lệ.

    - Nếu operation_id khác NULL:
      Operation phải thuộc Task được xác định bởi task_id.

    - Nếu operation_device_id khác NULL:
      operation_id không được NULL.
      Device mapping phải thuộc Operation tương ứng.

    - Nếu operation_id = NULL:
      Execution được xem là bước xử lý ở cấp Task.

Không được tạo Execution có quan hệ Task, Operation hoặc Operation_Device không nhất quán.
```

[4.7] Execution trong môi trường xử lý song song

```
Một Operation có thể tạo nhiều Execution được thực thi đồng thời trên những Device khác nhau.

Trường step_order thể hiện thứ tự logic phục vụ hiển thị và truy vết, không đại diện cho thứ tự thời gian thực tế của các Execution chạy song song.

Không yêu cầu step_order phải là duy nhất đối với các Execution được phép thực thi đồng thời.

Thời điểm thực thi thực tế được xác định thông qua started_at và completed_at.

Orchestrator phải bảo đảm các Execution được tạo đúng theo quan hệ dependency và trạng thái Operation.
```

[4.8] Lưu trữ Input và Output

```
input lưu dữ liệu đầu vào đã được truyền tới Agent hoặc Tool.

output lưu kết quả do Agent hoặc Tool tạo ra.

Đối với Execution sinh cấu hình WRITE:
    - output phải chứa nội dung cấu hình dự kiến.
    - Cấu hình dự kiến phải được phân biệt với command đã thực sự thực thi trên Device.
    - Việc sinh cấu hình thành công không đồng nghĩa với việc cấu hình đã được áp dụng thành công.

Không lưu Credential đã giải mã hoặc thông tin nhạy cảm trong input và output.

Các kết quả lỗi hoặc dữ liệu do Device trả về phải được kiểm tra và xử lý trước khi hiển thị trên Chat UI.
```

[4.9] Xử lý Execution thất bại

```
Khi Execution thất bại:
    - execution_status chuyển sang FAILED.
    - error_message ghi nhận thông tin lỗi.
    - completed_at được cập nhật.
    - duration_ms được tính nếu có đủ thời điểm bắt đầu và kết thúc.

Orchestrator dựa trên kết quả Execution để quyết định trạng thái tiếp theo của Operation hoặc Device tương ứng.

Không được mặc định đánh dấu toàn bộ Task là FAILED chỉ vì một Execution thất bại nếu các Operation khác vẫn có thể tiếp tục xử lý hợp lệ.
```

### 2.3.6 Device_Action_Logs (Nhật ký thao tác trên thiết bị)

**_[1] Ý nghĩa bảng (Description)_**

Đây là lớp audit cuối cùng của hệ thống, dùng để ghi nhận những hành động đã thực sự xảy ra trên thiết bị, từ đó hỗ trợ truy vết toàn bộ quá trình từ yêu cầu ban đầu của người dùng đến command được gửi xuống thiết bị.

**_Ví dụ:_**

```
Các command READ thực tế trên P1 và P2 được ghi log:

      Log 1

            task_id = TASK01
            operation_id = OP1
            device_id = P1
            command = "show ip route"
            status = SUCCESS

      Log 2

            task_id = TASK01
            operation_id = OP1
            device_id = P2
            command = "show ip route"
            status = SUCCESS

OP2 chỉ phân tích dữ liệu trong hệ thống:

      OP2
      → không gửi command xuống Device
      → không tạo Device_Action_Log.

Đối với OP3, việc Agent chỉ sinh cấu hình dự kiến:

      configure terminal
      router ospf 1
      ...

không tạo Device_Action_Log, vì cấu hình chưa được gửi xuống P3.

Chỉ sau khi Human APPROVE và command thực sự được gửi xuống Device mới tạo log:

      Log 3

            task_id = TASK01
            operation_id = OP3
            device_id = P3

            command =
                  "configure terminal
                  router ospf 1
                  network 10.0.0.0 0.0.0.255 area 0"

            status = SUCCESS

Như vậy có thể phân biệt rõ:

      Task_Executions.output
      → cấu hình AI dự kiến thực hiện.

      Device_Action_Logs
      → command đã thực sự được gửi xuống thiết bị.
```

**_[2] Trường dữ liệu (Fields)_**

| Field               | Type      | Nullable | Meaning                                                                                                                         |
| ------------------- | --------- | -------- | ------------------------------------------------------------------------------------------------------------------------------- |
| id                  | UUID      | No       | Mã định danh duy nhất của bản ghi lịch sử thao tác trên thiết bị.                                                               |
| task_id             | varchar   | No       | Mã Task ban đầu tạo ra hành động này, dùng để truy vết từ yêu cầu nguyên bản của người dùng tới thao tác thực tế trên thiết bị. |
| operation_id        | varchar   | No       | Mã Operation logic dẫn đến hành động này.                                                                                       |
| operation_device_id | varchar   | No       | Mã bản ghi mapping giữa Operation và Device đang được xử lý.                                                                    |
| execution_id        | varchar   | No       | Mã Execution đã sinh ra hoặc thực hiện hành động này.                                                                           |
| device_id           | varchar   | No       | Mã thiết bị mạng thực tế được gửi command hoặc nhận tác động.                                                                   |
| command             | text      | No       | Nội dung command, API request hoặc thao tác thực tế được gửi xuống thiết bị.                                                    |
| action_type         | enum      | No       | Loại hành động thực tế: `READ` hoặc `WRITE`.                                                                                    |
| result              | text      | Yes      | Kết quả phản hồi từ thiết bị sau khi thực thi command.                                                                          |
| action_log_status   | enum      | No       | Trạng thái thực hiện command.                                                                                                   |
| error_message       | text      | Yes      | Chi tiết lỗi khi command thất bại, ví dụ: authentication failed, connection timeout, invalid command hoặc device unreachable.   |
| executed_at         | timestamp | No       | Thời điểm hệ thống thực sự gửi command hoặc thực hiện thao tác trên thiết bị                                                    |

**_[3] Ràng buộc (constraint):_**

| Type      | Applicable to         | Description                                    |
| --------- | --------------------- | ---------------------------------------------- |
| **PK**    | `id`                  | Khóa chính, định danh duy nhất bản ghi log.    |
| **FK**    | `task_id`             | Tham chiếu đến `Tasks(id)`.                    |
| **FK**    | `operation_id`        | Tham chiếu đến `Task_Operations(id)`.          |
| **FK**    | `operation_device_id` | Tham chiếu đến `Task_Operation_Devices(id)`.   |
| **FK**    | `execution_id`        | Tham chiếu đến `Task_Executions(id)`.          |
| **FK**    | `device_id`           | Tham chiếu đến `Devices(id)`.                  |
| **INDEX** | `task_id`             | Tăng tốc truy vấn log theo Task.               |
| **INDEX** | `device_id`           | Tăng tốc truy vấn log theo Device.             |
| **INDEX** | `execution_id`        | Tăng tốc truy vấn log theo Execution.          |
| **INDEX** | `executed_at`         | Tăng tốc truy vấn log theo thời gian thực thi. |
| **CHECK** | `action_type`         | Chỉ nhận `READ` hoặc `WRITE`.                  |
| **INDEX** | `action_type`         | Phục vụ audit thao tác READ/WRITE thực tế.     |

**_[4] Quy tắc nghiệp vụ (Business Rules)_**

[4.1] Trường `action_log_status`

```
Các trạng thái hiện tại gồm:
      - SUCCESS: Command đã được thực thi và hệ thống nhận được kết quả xác nhận thành công theo tiêu chí của Tool.
      - FAILED: Hệ thống xác định command không thực thi thành công hoặc thiết bị trả về kết quả lỗi rõ ràng.
      - UNKNOWN: Command đã được gửi hoặc có khả năng đã được gửi xuống Device nhưng hệ thống không thể xác định kết quả thực thi cuối cùng (Ví dụ: mất kết nối hoặc timeout sau khi gửi command).

Trạng thái UNKNOWN không được tự động xem là FAILED, đặc biệt đối với command WRITE
```

[4.2] Phân biệt với Task_Executions.output

```
Task_Executions.output → cấu hình AI dự kiến thực hiện.

Device_Action_Logs → command đã thực sự được gửi xuống thiết bị.
```

[4.3] Điều kiện tạo log

```
Command READ thực tế trên Device → tạo Device_Action_Log.

Command WRITE chỉ được tạo log sau khi Human APPROVE và command thực sự được gửi xuống Device.

Việc Agent chỉ sinh cấu hình dự kiến (chưa gửi xuống Device) không tạo Device_Action_Log.

Operation chỉ phân tích dữ liệu trong hệ thống, không gửi command xuống Device → không tạo Device_Action_Log.
```

[4.5] Kiểm tra tính nhất quán của Device Action Log

```
Mỗi Device_Action_Log phải liên kết với một Execution và Device mapping hợp lệ.

Hệ thống phải bảo đảm:
    - execution_id thuộc operation_id tương ứng.
    - operation_id thuộc task_id tương ứng.
    - operation_device_id thuộc operation_id tương ứng.
    - device_id trùng với Device được liên kết qua
      operation_device_id.

Không được tạo Device_Action_Log tham chiếu đến những Task, Operation hoặc Device không liên quan.
```

[4.6] Điều kiện ghi nhận command WRITE

```
Command WRITE chỉ được phép gửi xuống Device khi:
    - Operation có access_mode = WRITE.
    - Cấu hình dự kiến đã được Human phê duyệt.
    - Quyết định APPROVE còn hiệu lực.
    - Nội dung command được thực thi khớp với nội dung đã được phê duyệt.
    - Quyền thao tác và điều kiện an toàn được kiểm tra trước thời điểm thực thi.

Nếu không thỏa mãn các điều kiện trên, hệ thống phải từ chối việc gửi command WRITE xuống Device.
```

[4.7] Xử lý command có kết quả không xác định

```
Nếu command WRITE có status = UNKNOWN:
    - Không tự động gửi lại command nếu chưa xác định việc thực thi lặp lại là an toàn.
    - Hệ thống phải kiểm tra lại trạng thái Device bằng các thao tác READ phù hợp khi có thể.
    - Nếu xác minh được trạng thái mong muốn đã được áp dụng, hệ thống có thể ghi nhận kết quả xác minh tương ứng.
    - Nếu không xác định được trạng thái thực tế, phải giữ thông tin UNKNOWN trong lịch sử audit và yêu cầu xử lý bổ sung.

Không được xóa hoặc ghi đè dữ liệu audit gốc chỉ vì có kết quả xác minh sau đó.
```

[4.8] Bảo toàn lịch sử thao tác Device

```
Device_Action_Logs được sử dụng cho mục đích audit và truy vết các command thực tế.

Các bản ghi lịch sử không được tự ý thay đổi hoặc xóa trong quá trình sử dụng thông thường.

Việc quản lý thời gian lưu trữ và xóa dữ liệu lịch sử phải tuân theo chính sách lưu trữ audit của hệ thống.

Không được lưu password, secret hoặc token nhạy cảm trong command, result hoặc error_message.
```

[4.9] Trường `action_type`

```
action_type phản ánh tác động thực tế của command:
    - READ: chỉ đọc thông tin/cấu hình/trạng thái Device.
    - WRITE: có thể thay đổi cấu hình hoặc trạng thái Device.

Không được suy ra action_type chỉ từ Task_Operation_Devices.access_mode.
Operation có access_mode = WRITE vẫn có thể thực hiện command READ để kiểm tra trạng thái trước khi thay đổi cấu hình.

Command WRITE chỉ được gửi khi Approval hợp lệ cho cấu hình tương ứng.
Các hành động bị chặn trước khi gửi xuống Device không tạo Device_Action_Log; nếu cần đánh giá đầy đủ hành động bị chặn, phải có bản ghi sự kiện an toàn riêng.
```

### 2.3.7 Task_Activity_Events (Sự kiện hoạt động của Task)

**_[1] Ý nghĩa bảng (Description)_**

Lưu timeline có thứ tự của các hoạt động do Orchestrator, Agent hoặc Tool thực hiện trong vòng đời một Task.

Bảng này là nguồn dữ liệu để Chat UI hiển thị phần “Đã xử lý trong...” và các bước như tiếp nhận Message, tạo Task, lập Execution Plan, thực thi command, chờ phê duyệt và phân tích kết quả.

Task_Activity_Events chỉ lưu sự kiện ở mức workflow và trình bày. Bảng này không thay thế:

- Task_Executions, là lịch sử thực thi kỹ thuật của Agent hoặc Tool.
- Device_Action_Logs, là audit log của command thực tế gửi xuống Device.
- Messages, là nội dung trao đổi chính thức hiển thị trong Conversation.

**_[2] Trường dữ liệu (Fields)_**

| Field           | Type       | Nullable | Meaning                                                                                   |
| --------------- | ---------- | -------- | ----------------------------------------------------------------------------------------- |
| id              | varchar PK | No       | Mã định danh duy nhất của Activity Event.                                                 |
| task_id         | varchar FK | No       | Task sở hữu Activity Event.                                                               |
| operation_id    | varchar FK | Yes      | Operation liên quan nếu sự kiện xảy ra ở phạm vi một Operation.                           |
| execution_id    | varchar FK | Yes      | Execution liên quan nếu sự kiện được tạo từ một lần Agent hoặc Tool thực thi.             |
| actor_type      | enum       | No       | Thành phần tạo sự kiện: ORCHESTRATOR, PLANNER, NETWORK, ANALYST hoặc TOOL.                |
| event_type      | enum       | No       | Loại sự kiện nghiệp vụ dùng để frontend tạo nội dung hiển thị.                            |
| event_status    | enum       | No       | Trạng thái của sự kiện tại thời điểm hiện tại.                                            |
| sequence_number | integer    | No       | Thứ tự của sự kiện trong timeline thuộc Task.                                             |
| event_data      | JSONB      | No       | Dữ liệu có cấu trúc phục vụ hiển thị chi tiết; không lưu credential hoặc secret.          |
| started_at      | timestamp  | Yes      | Thời điểm hoạt động bắt đầu.                                                              |
| completed_at    | timestamp  | Yes      | Thời điểm hoạt động kết thúc; để trống khi đang chạy hoặc đang chờ một sự kiện bên ngoài. |
| created_at      | timestamp  | No       | Thời điểm Activity Event được tạo.                                                        |

**_[3] Ràng buộc (Constraint)_**

| Type       | Applicable to                  | Description                                                       |
| ---------- | ------------------------------ | ----------------------------------------------------------------- |
| **PK**     | `id`                           | Khóa chính, định dạng: `task-acti-ddmmyy-xxxxxxxx`.               |
| **FK**     | `task_id`                      | Tham chiếu đến `Tasks(id)`.                                       |
| **FK**     | `operation_id`                 | Tham chiếu đến `Task_Operations(id)`.                             |
| **FK**     | `execution_id`                 | Tham chiếu đến `Task_Executions(id)`.                             |
| **UNIQUE** | (`task_id`, `sequence_number`) | Mỗi vị trí trong timeline của một Task chỉ có một Activity Event. |
| **CHECK**  | `sequence_number`              | Phải lớn hơn 0.                                                   |
| **CHECK**  | `actor_type`                   | Thuộc tập giá trị được định nghĩa tại Business Rules [4.1].       |
| **CHECK**  | `event_status`                 | Thuộc tập giá trị được định nghĩa tại Business Rules [4.3].       |
| **CHECK**  | `completed_at`                 | Nếu có giá trị thì phải lớn hơn hoặc bằng `started_at`.           |
| **INDEX**  | (`task_id`, `sequence_number`) | Tăng tốc truy xuất timeline theo đúng thứ tự hiển thị.            |
| **INDEX**  | `operation_id`                 | Tăng tốc truy vết Activity Event của Operation.                   |
| **INDEX**  | `execution_id`                 | Tăng tốc truy vết Activity Event từ Execution.                    |
| **INDEX**  | (`task_id`, `event_status`)    | Tăng tốc truy vấn Activity Event đang chạy hoặc đang chờ.         |

**_[4] Quy tắc nghiệp vụ (Business Rules)_**

[4.1] Trường `actor_type`

```
Các giá trị hiện tại gồm:
      - ORCHESTRATOR: sự kiện do thành phần điều phối workflow tạo ra.
      - PLANNER: sự kiện trong quá trình phân tích yêu cầu và tạo Execution Plan.
      - NETWORK: sự kiện trong quá trình Network Agent điều phối thao tác Device.
      - ANALYST: sự kiện trong quá trình phân tích kết quả và tạo phản hồi.
      - TOOL: sự kiện kỹ thuật cần trình bày trực tiếp từ Tool.
```

[4.2] Trường `event_type`

```
Các giá trị khởi tạo gồm:
      - MESSAGE_RECEIVED
      - TASK_CREATED
      - PLAN_GENERATED
      - OPERATIONS_CREATED
      - DEPENDENCIES_CREATED
      - DEVICES_ASSIGNED
      - EXECUTION_STARTED
      - COMMAND_EXECUTED
      - APPROVAL_REQUESTED
      - APPROVAL_APPROVED
      - APPROVAL_REJECTED
      - ANALYSIS_STARTED
      - ANALYSIS_COMPLETED
      - FINAL_RESPONSE_CREATED
      - TASK_COMPLETED
      - TASK_FAILED

event_type là mã ổn định bằng tiếng Anh. Frontend sử dụng event_type và event_data để tạo nội dung theo ngôn ngữ giao diện; không lưu cố định câu tiếng Việt vào event_type.
```

[4.3] Trường `event_status`

```
Các giá trị hiện tại gồm:
      - PENDING
      - RUNNING
      - WAITING_APPROVAL
      - SUCCESS
      - FAILED
      - SKIPPED
```

[4.4] Quy tắc tham chiếu

```
Nếu operation_id có giá trị, Operation phải thuộc task_id của Activity Event.

Nếu execution_id có giá trị, Execution phải thuộc cùng task_id và operation_id tương ứng nếu operation_id cũng có giá trị.

Không tạo Activity Event tham chiếu đến Task, Operation hoặc Execution không liên quan.
```

[4.5] Quy tắc hiển thị Conversation

```
Task_Activity_Events không phải Message và không được hiển thị như câu trả lời chính thức của Agent.

Chat UI lấy Task thông qua Tasks.source_message_id, lấy timeline theo task_id, sau đó hiển thị timeline trong phần có thể thu gọn của phản hồi Agent tương ứng.

Câu trả lời chính thức của Analyst hoặc hệ thống AI vẫn phải được lưu tại Messages.
```

[4.6] Tính Active Processing Time

```
Active Processing Time được tính từ hợp các khoảng thời gian thực sự xử lý của Activity Event có started_at và completed_at hợp lệ.

Các khoảng thời gian chồng lấp do Agent hoặc Operation chạy song song phải được hợp nhất trước khi tính tổng để tránh cộng trùng thời gian.

Không cộng thời gian Task tạm dừng để chờ Human Approval. Khoảng chờ được xác định từ Operation_Device_Approvals.requested_at đến decided_at. Các khoảng chờ trùng nhau giữa nhiều Device của cùng một Operation phải được hợp nhất để tránh cộng trùng thời gian.

Ví dụ:
      - Agent xử lý 30 giây.
      - Chờ Human phê duyệt 10 phút.
      - Agent tiếp tục xử lý 20 giây.

Chat UI hiển thị “Đã xử lý trong 50s”, không hiển thị 10 phút 50 giây.
```

[4.7] Bảo toàn và bảo mật event_data

```
event_data chỉ lưu dữ liệu cần thiết để trình bày và truy vết workflow.

Không lưu password, secret, token, private key hoặc credential đã giải mã.

Các Event đã kết thúc không được ghi đè để làm thay đổi lịch sử. Nếu workflow tiếp tục sau Approval, hệ thống tạo Event mới với sequence_number tiếp theo.
```

### 2.3.8 Operation_Device_Approvals (Phê duyệt Operation theo thiết bị)

**_[1] Ý nghĩa bảng (Description)_**

Lưu yêu cầu Human Approval và quyết định của người dùng trước khi một Task_Operation_Device có access_mode = WRITE được phép gửi command thay đổi cấu hình hoặc trạng thái xuống Device.

Mỗi bản ghi đại diện cho yêu cầu phê duyệt duy nhất của đúng một mapping Operation - Device và lưu snapshot command cùng dữ liệu đánh giá rủi ro tại thời điểm tạo yêu cầu. Chat UI có thể hiển thị các yêu cầu của nhiều Device trong cùng một Operation bằng cách truy vấn qua quan hệ với Task_Operation_Devices.

**_[2] Trường dữ liệu (Fields)_**

| Field               | Type       | Nullable | Meaning                                                                                   |
| ------------------- | ---------- | -------- | ----------------------------------------------------------------------------------------- |
| id                  | varchar PK | No       | Mã định danh duy nhất của Approval Request theo Device.                                   |
| operation_device_id | varchar FK | No       | Mapping Operation - Device cần Human phê duyệt.                                           |
| approval_status     | enum       | No       | Trạng thái hiện tại của yêu cầu phê duyệt.                                                |
| risk_level          | enum       | No       | Mức độ rủi ro của thay đổi dự kiến trên Device này.                                       |
| requested_by        | varchar    | No       | Tên ổn định của Agent hoặc thành phần hệ thống tạo yêu cầu.                               |
| reason              | text       | No       | Lý do cần thay đổi và cần Human Approval.                                                 |
| commands_snapshot   | JSONB      | No       | Snapshot command WRITE và tham số dự kiến thực thi trên Device tương ứng.                 |
| request_hash        | varchar    | No       | Hash của operation_device_id và commands_snapshot đã chuẩn hóa để đối chiếu khi thực thi. |
| decided_by          | varchar FK | Yes      | User đã APPROVED hoặc REJECTED yêu cầu.                                                   |
| requested_at        | timestamp  | No       | Thời điểm yêu cầu phê duyệt được tạo.                                                     |
| decided_at          | timestamp  | Yes      | Thời điểm người dùng ra quyết định.                                                       |
| expires_at          | timestamp  | Yes      | Thời điểm yêu cầu hết hiệu lực nếu chưa có quyết định.                                    |
| created_at          | timestamp  | No       | Thời điểm bản ghi được tạo.                                                               |

**_[3] Ràng buộc (Constraint)_**

| Type       | Applicable to         | Description                                                        |
| ---------- | --------------------- | ------------------------------------------------------------------ |
| **PK**     | `id`                  | Khóa chính, định dạng: `aprv-devs-ddmmyy-xxxxxxxx`.                |
| **FK**     | `operation_device_id` | Tham chiếu đến `Task_Operation_Devices(id)`.                       |
| **FK**     | `decided_by`          | Tham chiếu đến `Users(id)`.                                        |
| **CHECK**  | `approval_status`     | Thuộc tập giá trị được định nghĩa tại Business Rules [4.1].        |
| **CHECK**  | `risk_level`          | Thuộc tập giá trị được định nghĩa tại Business Rules [4.2].        |
| **CHECK**  | `decided_at`          | Nếu có giá trị thì phải lớn hơn hoặc bằng `requested_at`.          |
| **CHECK**  | `expires_at`          | Nếu có giá trị thì phải lớn hơn `requested_at`.                    |
| **UNIQUE** | `operation_device_id` | Mỗi mapping Operation - Device chỉ được yêu cầu phê duyệt một lần. |
| **INDEX**  | `decided_by`          | Tăng tốc truy vấn lịch sử quyết định theo User.                    |

Quan hệ giữa Task_Operation_Devices và Operation_Device_Approvals là `1 - 0..1`. Ràng buộc UNIQUE trên `operation_device_id` áp dụng cho mọi trạng thái, không chỉ PENDING, vì hệ thống không cho phép phê duyệt lại.

Không lưu lặp `task_id`, `operation_id` hoặc `device_id` trong bảng này. Các giá trị đó được truy xuất theo quan hệ `operation_device_id -> Task_Operation_Devices -> Task_Operations/Devices` để tránh sai lệch dữ liệu.

**_[4] Quy tắc nghiệp vụ (Business Rules)_**

[4.1] Trường `approval_status`

```
Các giá trị hiện tại gồm:
      - PENDING: đang chờ người dùng quyết định.
      - APPROVED: người dùng cho phép thực thi đúng snapshot đã xem.
      - REJECTED: người dùng từ chối thực thi.
      - EXPIRED: hết thời hạn quyết định.
```

[4.2] Trường `risk_level`

```
Các giá trị hiện tại gồm:
      - LOW
      - MEDIUM
      - HIGH
      - CRITICAL

risk_level được xác định bằng policy hoặc safety rule của hệ thống, không chỉ dựa trên nội dung giải thích tự khai báo của Agent.
```

[4.3] Điều kiện tạo Approval Request

```
Approval Request được tạo cho từng Task_Operation_Device trước khi thực thi command WRITE nếu policy yêu cầu Human Approval.

Task_Operation_Device được tham chiếu phải có access_mode = WRITE.

Khi cần hiển thị hoặc quyết định nhiều Device của cùng một Operation, Backend truy vấn các Approval Request thông qua `Task_Operation_Devices.operation_id`. Không cần mã nhóm phê duyệt riêng.

Khi Approval Request ở trạng thái PENDING:
      - Task giữ trạng thái RUNNING.
      - Task_Operations.operation_status = WAITING_APPROVAL nếu còn ít nhất một Device đang chờ.
      - Task_Operation_Device tương ứng giữ trạng thái WAITING_APPROVAL.
      - Orchestrator không được gửi command WRITE xuống Device tương ứng.
```

[4.4] Trường `commands_snapshot`

```
commands_snapshot phải chứa tối thiểu:
      - Danh sách command WRITE dự kiến thực thi trên Device tương ứng.
      - Thứ tự command và các tham số cần thiết để người dùng hiểu phạm vi thay đổi.

commands_snapshot là snapshot bất biến kể từ thời điểm Approval Request được tạo.

request_hash được tạo từ operation_device_id và commands_snapshot đã chuẩn hóa tại thời điểm tạo Approval Request.

Nếu command hoặc Device mapping thay đổi, Approval Request hiện tại không còn hiệu lực. Hệ thống phải hủy Operation hiện tại và tạo Operation cùng Task_Operation_Device mới; không tạo Approval Request thứ hai cho cùng operation_device_id.

Không lưu password, secret, token hoặc credential đã giải mã trong commands_snapshot.
```

[4.5] Quy tắc ra quyết định

```
Chỉ User có quyền phê duyệt phù hợp mới được APPROVED hoặc REJECTED.

Hệ thống có thể cho phép User quyết định từng Device hoặc quyết định tất cả các yêu cầu PENDING thuộc cùng một Operation. Quyết định nhiều Device phải được cập nhật trong cùng một transaction; mỗi bản ghi vẫn lưu trạng thái và lịch sử riêng.

Khi APPROVED hoặc REJECTED:
      - decided_by bắt buộc có giá trị.
      - decided_at bắt buộc có giá trị.

Khi PENDING hoặc EXPIRED mà không có quyết định trực tiếp từ User, decided_by để trống.

APPROVED, REJECTED và EXPIRED đều là trạng thái cuối. Quyết định đã hoàn tất không được chỉnh sửa và hệ thống không được tạo Approval Request khác cho cùng operation_device_id. Nếu vẫn cần thực thi sau REJECTED hoặc EXPIRED, hệ thống phải lập Operation cùng Task_Operation_Device mới.
```

[4.6] Tiếp tục workflow sau quyết định

```
APPROVED:
      - Orchestrator xác minh Approval còn hiệu lực.
      - Xác minh command và Device mapping khớp commands_snapshot cùng request_hash.
      - Chỉ tiếp tục thực thi Task_Operation_Device đã được APPROVED.
      - Tạo Task_Activity_Event APPROVAL_APPROVED và các Event thực thi tiếp theo.

REJECTED hoặc EXPIRED:
      - Không gửi command WRITE xuống Device tương ứng.
      - Cập nhật Device mapping và tổng hợp lại trạng thái Operation theo policy.
      - Tạo Task_Activity_Event tương ứng để Chat UI hiển thị.
```

[4.7] Hiển thị trong Conversation

```
Khi tạo các Approval Request cho một Operation, hệ thống tạo một Message có:
      - sender_by = AGENT.
      - message_type = APPROVAL_REQUEST.
      - reply_to_message_id tham chiếu USER_REQUEST đã tạo Task.

Message chứa nội dung giải thích dành cho người dùng. Chi tiết có cấu trúc của thẻ phê duyệt được lấy bằng cách truy vấn các Operation_Device_Approvals thuộc cùng một Operation thông qua Task_Operation_Devices.operation_id.
```

## 2.4. GROUP 4: CONVERSATION MANAGEMENT

Nhóm Conversation Management chịu trách nhiệm lưu trữ lịch sử trao đổi giữa người dùng và hệ thống AI thông qua giao diện Chat UI.

Một người dùng có thể tạo nhiều Conversation và mỗi Conversation có thể chứa nhiều Message.

Conversation cũng được sử dụng để liên kết với Tasks, giúp hệ thống truy vết một yêu cầu AI được tạo ra từ phiên hội thoại nào

### 2.4.1 Conversations (Phiên hội thoại)

**_[1] Ý nghĩa bảng (Description)_**

Lưu trữ thông tin tổng quát của một phiên hội thoại giữa người dùng và hệ thống AI.

Mỗi Conversation đại diện cho một chuỗi trao đổi độc lập giữa người dùng và hệ thống, bao gồm nhiều Message được gửi trong cùng một ngữ cảnh hội thoại.

**_[2] Trường dữ liệu (Fields)_**

| Field           | Type         | Nullable | Meaning                                                                                                                   |
| --------------- | ------------ | -------- | ------------------------------------------------------------------------------------------------------------------------- |
| id              | varchar      | No       | Mã định danh duy nhất của Conversation, sử dụng để phân biệt các conversation trong hệ thống.                             |
| user_id         | varchar      | No       | Mã định danh của người dùng sở hữu hoặc khởi tạo phiên hội thoại.                                                         |
| title           | varchar(100) | No       | Tiêu đề ngắn của Conversation, được tạo tự động dựa trên USER_REQUEST đầu tiên.                                           |
| created_at      | timestamp    | No       | Thời điểm phiên hội thoại được tạo trong hệ thống.                                                                        |
| last_updated_at | timestamp    | No       | Thời điểm gần nhất phiên hội thoại có sự thay đổi, chẳng hạn như có tin nhắn mới hoặc tiêu đề conversation được cập nhật. |

**_[3] Ràng buộc (constraint):_**

| Type      | Applicable to     | Description                                                                 |
| --------- | ----------------- | --------------------------------------------------------------------------- |
| **PK**    | `id`              | Khóa chính, định danh duy nhất Conversation, định dạng: `cons-ddmmyy-xxxx`. |
| **FK**    | `user_id`         | Tham chiếu đến `Users(id)`.                                                 |
| **CHECK** | `title`           | Sau khi trim phải có từ 1 đến 100 ký tự.                                    |
| **INDEX** | `user_id`         | Tăng tốc truy vấn Conversation theo người dùng.                             |
| **INDEX** | `last_updated_at` | Tăng tốc sắp xếp Conversation theo thời gian cập nhật.                      |

**_[4] Quy tắc nghiệp vụ (Business Rules)_**

[4.1] Vai trò của Conversation

```
Conversation được sử dụng để:
      - Xác định người dùng sở hữu phiên hội thoại.
      - Nhóm các Message có cùng ngữ cảnh.
      - Hiển thị và quản lý lịch sử hội thoại trên Chat UI.
      - Liên kết yêu cầu của người dùng với các Task được tạo ra trong quá trình xử lý AI.

Conversation chỉ được tạo khi User thực sự gửi USER_REQUEST đầu tiên. Backend
phải tạo Conversation và Message đầu tiên trong cùng một transaction để không
tạo ra Conversation rỗng nếu việc lưu Message thất bại.
```

[4.2] Trường `title`

```
Tiêu đề đại diện ngắn gọn cho mục tiêu hoặc chủ đề chính của Conversation, giúp người dùng nhận biết lịch sử hội thoại trong sidebar.

Trong transaction khởi tạo Conversation và USER_REQUEST đầu tiên, hệ thống sử
dụng tiêu đề tạm thời:
      "Cuộc hội thoại mới"

Sau khi USER_REQUEST đầu tiên được lưu thành công, hệ thống sử dụng LLM để tạo title dựa trên ngữ cảnh của chính Message đầu tiên đó.

LLM tạo title phải tuân thủ:
      - Tối đa 100 ký tự Unicode sau khi trim.
      - Chỉ có một dòng.
      - Không thêm dấu ngoặc kép bao quanh.
      - Không thêm Markdown, bullet, prefix hoặc hậu tố giải thích.
      - Không kết thúc bằng dấu chấm nếu không cần thiết.
      - Thể hiện đúng mục tiêu chính của yêu cầu, không tự tạo thêm ý định.
      - Giữ nguyên hostname, địa chỉ IP, tên giao thức, command và thuật ngữ kỹ thuật quan trọng.
      - Sử dụng cùng ngôn ngữ chính với USER_REQUEST; nếu không xác định được thì dùng ngôn ngữ mặc định của hệ thống.

Ví dụ:
      USER_REQUEST: "Kiểm tra routing table trên P1 và phân tích xem có route bất thường không"
      title: "Kiểm tra routing table trên P1"

Việc tạo title chỉ tự động thực hiện một lần từ USER_REQUEST đầu tiên. Các Message tiếp theo không tự động thay đổi title để tránh sidebar bị thay đổi ngoài dự kiến.

Nếu hệ thống hỗ trợ người dùng đổi title thủ công, title do người dùng đặt không được LLM tự động ghi đè.

Nếu LLM lỗi, timeout, trả kết quả rỗng hoặc không hợp lệ, hệ thống không được làm thất bại việc lưu Message hoặc tạo Task. Backend sử dụng fallback theo thứ tự:
      1. Chuẩn hóa USER_REQUEST đầu tiên về một dòng và cắt an toàn tối đa 100 ký tự.
      2. Nếu nội dung sau chuẩn hóa vẫn rỗng, giữ title "Cuộc hội thoại mới".

Nếu kết quả LLM dài hơn 100 ký tự, Backend phải cắt tại ranh giới từ gần nhất nếu có thể, sau đó trim khoảng trắng. Database vẫn áp dụng CHECK cuối cùng để bảo đảm độ dài hợp lệ.
```

[4.3] Trường `last_updated_at`

```
Thời điểm gần nhất phiên hội thoại có sự thay đổi, chẳng hạn như có tin nhắn mới hoặc tiêu đề conversation được cập nhật.
```

[4.4] Quyền truy cập Conversation

```
Mỗi Conversation thuộc về một User thông qua user_id.

Người dùng chỉ được truy cập những Conversation mà mình sở hữu, trừ khi được cấp quyền quản trị phù hợp.

Khi truy xuất Messages hoặc Tasks thuộc Conversation, hệ thống phải kiểm tra quyền truy cập Conversation trước khi trả dữ liệu.
```

[4.5] Xóa lịch sử Conversation

```
Việc xóa Conversation khỏi giao diện Chat UI không được mặc định xóa các dữ liệu runtime và audit liên quan như:
    - Tasks
    - Task_Operations
    - Task_Executions
    - Device_Action_Logs
    - Task_Activity_Events
    - Operation_Device_Approvals

Các bản ghi phục vụ audit phải được bảo toàn theo chính sách lưu trữ của hệ thống.

Nếu cần hỗ trợ ẩn hoặc xóa Conversation khỏi giao diện, hệ thống phải có cơ chế phù hợp để vẫn bảo đảm tính toàn vẹn của các quan hệ dữ liệu.
```

### 2.4.2 Messages (Tin nhắn hội thoại)

**_[1] Ý nghĩa bảng (Description)_**

Lưu trữ từng Message được gửi trong một Conversation giữa người dùng và hệ thống AI.

Mỗi Message thuộc về duy nhất một Conversation và ghi nhận đối tượng gửi, loại Message, nội dung Message cũng như thời điểm Message được tạo.

Message do Agent tạo có thể tham chiếu đến Message nguồn của người dùng thông qua `reply_to_message_id`. Quan hệ này giúp Chat UI đặt timeline, yêu cầu phê duyệt và phản hồi cuối của Agent đúng dưới yêu cầu tương ứng mà không cần lưu `task_id` trùng lặp trong Messages. Task vẫn được liên kết duy nhất với Message nguồn thông qua `Tasks.source_message_id`.

**_[2] Trường dữ liệu (Fields)_**

| Field               | Type       | Nullable | Meaning                                                                                                 |
| ------------------- | ---------- | -------- | ------------------------------------------------------------------------------------------------------- |
| id                  | varchar    | No       | Mã định danh duy nhất của một Message trong hệ thống, định dạng: `mesg-ddmmyy-xxxx`.                    |
| conversation_id     | varchar    | No       | Mã phiên hội thoại chứa tin nhắn.                                                                       |
| reply_to_message_id | varchar FK | Yes      | Message nguồn mà Message hiện tại phản hồi. Dùng để gắn phản hồi Agent với đúng yêu cầu của người dùng. |
| sender_by           | enum       | No       | Xác định đối tượng gửi tin nhắn. Giá trị có thể gồm `USER`/`AGENT`.                                     |
| message_type        | enum       | No       | Phân loại vai trò của Message trong Conversation và workflow AI.                                        |
| message             | text       | No       | Nội dung của tin nhắn được người dùng hoặc hệ thống AI gửi trong phiên hội thoại.                       |
| created_at          | timestamp  | No       | Thời điểm tin nhắn được tạo và lưu vào hệ thống.                                                        |

**_[3] Ràng buộc (constraint):_**

| Type      | Applicable to         | Description                                                 |
| --------- | --------------------- | ----------------------------------------------------------- |
| **PK**    | `id`                  | Khóa chính, định danh duy nhất Message.                     |
| **FK**    | `conversation_id`     | Tham chiếu đến `Conversations(id)`.                         |
| **FK**    | `reply_to_message_id` | Tự tham chiếu đến `Messages(id)`.                           |
| **INDEX** | `conversation_id`     | Tăng tốc truy vấn Message theo Conversation.                |
| **INDEX** | `reply_to_message_id` | Tăng tốc truy vấn các phản hồi thuộc một Message nguồn.     |
| **INDEX** | `message_type`        | Tăng tốc lọc Message theo vai trò trong workflow.           |
| **INDEX** | `created_at`          | Tăng tốc sắp xếp Message theo thời gian tạo.                |
| **CHECK** | `message_type`        | Thuộc tập giá trị được định nghĩa tại Business Rules [4.2]. |

**_[4] Quy tắc nghiệp vụ (Business Rules)_**

[4.1] Trường `sender_by`

```
Các giá trị hiện tại gồm:
      - USER: đối với tin nhắn từ người dùng
      - AGENT: đối với phản hồi từ hệ thống AI
```

[4.2] Trường `message_type`

```
Các giá trị hiện tại gồm:
      - GENERAL: Message hội thoại thông thường không gắn với một giai đoạn workflow cụ thể.
      - USER_REQUEST: yêu cầu của người dùng có thể tạo Task.
      - STATUS_UPDATE: phản hồi trung gian về trạng thái xử lý của Task.
      - APPROVAL_REQUEST: phản hồi yêu cầu người dùng phê duyệt hoặc từ chối một Operation.
      - FINAL_RESPONSE: câu trả lời cuối cùng của hệ thống AI sau khi workflow kết thúc.
```

[4.3] Trường `reply_to_message_id`

```
Message có reply_to_message_id phải tham chiếu đến Message thuộc cùng Conversation.

Message có message_type = STATUS_UPDATE, APPROVAL_REQUEST hoặc FINAL_RESPONSE phải:
      - Có sender_by = AGENT.
      - Có reply_to_message_id tham chiếu đến Message nguồn có sender_by = USER.

Message có message_type = USER_REQUEST phải:
      - Có sender_by = USER.
      - Không có reply_to_message_id trong phiên bản hiện tại.

Một USER_REQUEST có thể nhận nhiều STATUS_UPDATE hoặc APPROVAL_REQUEST, nhưng chỉ có tối đa một FINAL_RESPONSE cho một Task trong phiên bản hiện tại.
```

[4.4] Liên kết Message với Task

```
Không lưu task_id trong Messages.

Quan hệ được truy vết theo chiều:
      Agent Message.reply_to_message_id
            -> USER Message.id
            -> Tasks.source_message_id
            -> Task và các dữ liệu runtime tương ứng.

Tasks.source_message_id có ràng buộc UNIQUE, do đó một USER Message chỉ tạo tối đa một Task.
```

## 2.5 GROUP 5: AI EVALUATION & BENCHMARKING

Nhóm AI Evaluation & Benchmarking chịu trách nhiệm lưu trữ kết quả đánh giá hiệu quả hoạt động của hệ thống Multi-Agent AI Network Automation.

Việc đánh giá được thực hiện dựa trên mục tiêu mong đợi, Ground Truth và bằng chứng thực tế, thay vì chỉ dựa vào trạng thái thực thi của Agent hoặc Tool.

Trong phiên bản hiện tại, nhóm hỗ trợ đánh giá bốn chỉ số chính:

- Task Success Rate.
- Root Cause Accuracy.
- Remediation Success Rate.
- Latency.

Ngoài ra, nhóm có thể mở rộng để đánh giá Safety và các chỉ số khác trong tương lai.

### 2.5.1 Task_Evaluations (Đánh giá kết quả tác vụ)

**_[1] Ý nghĩa bảng (Description)_**

Lưu kết quả đánh giá Task dựa trên mục tiêu mong đợi, Ground Truth và bằng chứng kiểm tra thực tế sau khi Task kết thúc.

Phân biệt:

- `Tasks.task_status`: trạng thái thực thi workflow.
- `Task_Evaluations`: kết quả đánh giá mức độ đạt mục tiêu thực tế.

Mỗi Task có tối đa một Evaluation trong phiên bản hiện tại. Đánh giá có thể thực hiện một lần sau Task, không yêu cầu cơ chế Closed-loop.

**_[2] Trường dữ liệu (Fields)_**

| Field                 | Type      | Nullable | Meaning                                                             |
| --------------------- | --------- | -------- | ------------------------------------------------------------------- |
| id                    | UUID      | No       | Mã định danh duy nhất của Evaluation.                               |
| task_id               | varchar   | No       | Task được đánh giá.                                                 |
| evaluation_status     | enum      | No       | Trạng thái tiến trình đánh giá: `PENDING` / `COMPLETED` / `ERROR`.  |
| expected_outcome      | JSONB     | Yes      | Điều kiện hoặc trạng thái mong đợi của Task.                        |
| actual_outcome        | JSONB     | Yes      | Kết quả thực tế được kiểm tra sau khi thực thi.                     |
| goal_result           | enum      | No       | Kết quả kiểm tra mục tiêu cuối Task.                                |
| expected_root_cause   | JSONB     | Yes      | Root Cause Ground Truth từ benchmark hoặc chuyên gia.               |
| predicted_root_cause  | JSONB     | Yes      | Root Cause do Agent đưa ra.                                         |
| rca_result            | enum      | No       | Kết quả đối chiếu Root Cause.                                       |
| remediation_required  | boolean   | No       | Task có yêu cầu khắc phục sự cố hay không.                          |
| remediation_attempted | boolean   | No       | Có hành động khắc phục sự cố thực tế hay không.                     |
| remediation_result    | enum      | No       | Kết quả khắc phục sự cố sau khi kiểm tra.                           |
| safety_result         | enum      | No       | Kết quả kiểm tra an toàn nếu có thực hiện Safety Evaluation.        |
| evaluation_evidence   | JSONB     | Yes      | Bằng chứng từ test case, Execution, command hoặc trạng thái Device. |
| evaluator_type        | enum      | No       | Nguồn đánh giá: `AUTOMATED` / `HUMAN`.                              |
| evaluator_version     | varchar   | Yes      | Phiên bản bộ quy tắc hoặc chương trình đánh giá.                    |
| created_at            | timestamp | No       | Thời điểm tạo Evaluation.                                           |
| evaluated_at          | timestamp | Yes      | Thời điểm Evaluation kết thúc.                                      |

Các trường `goal_result`, `rca_result`, `remediation_result` và `safety_result` cùng sử dụng tập giá trị: `PASS` / `FAIL` / `UNKNOWN` / `NOT_APPLICABLE`.

**_[3] Ràng buộc (constraint):_**

| Type       | Applicable to        | Description                                                         |
| ---------- | -------------------- | ------------------------------------------------------------------- |
| **PK**     | `id`                 | Định danh duy nhất Evaluation.                                      |
| **FK**     | `task_id`            | Tham chiếu đến `Tasks(id)`.                                         |
| **UNIQUE** | `task_id`            | Một Task có tối đa một bản ghi Evaluation trong phiên bản hiện tại. |
| **CHECK**  | `evaluation_status`  | Chỉ nhận `PENDING`, `COMPLETED`, `ERROR`.                           |
| **CHECK**  | Các trường kết quả   | Chỉ nhận `PASS`, `FAIL`, `UNKNOWN`, `NOT_APPLICABLE`.               |
| **CHECK**  | `evaluator_type`     | Chỉ nhận `AUTOMATED` hoặc `HUMAN`.                                  |
| **CHECK**  | `evaluated_at`       | NULL khi `PENDING`; NOT NULL khi `COMPLETED` hoặc `ERROR`.          |
| **CHECK**  | Các trường thời gian | `evaluated_at >= created_at` khi `evaluated_at` khác NULL.          |
| **INDEX**  | `evaluation_status`  | Tăng tốc truy vấn theo trạng thái đánh giá.                         |

**_[4] Quy tắc nghiệp vụ (Business Rules)_**

[4.1] Điều kiện tạo và hoàn tất Evaluation

```
Chỉ tạo Evaluation cho Task đã đạt trạng thái kết thúc:
    - SUCCESS
    - PARTIAL_SUCCESS
    - FAILED
    - REJECTED

Khi khởi tạo: evaluation_status = PENDING.
Sau khi chấm xong: evaluation_status = COMPLETED và cập nhật evaluated_at.
Nếu hệ thống đánh giá lỗi: evaluation_status = ERROR và cập nhật evaluated_at.

Không sử dụng Evaluation PENDING hoặc ERROR để công bố metric chính thức.
Phân biệt lỗi của Evaluator với Task bị Agent xử lý thất bại:
Task thất bại vẫn phải được chấm FAIL khi Evaluator hoạt động bình thường.
```

[4.2] Task Goal Evaluation

```
So sánh actual_outcome với expected_outcome bằng tiêu chí kiểm tra được xác định trước cho từng Task.

Chỉ PASS khi toàn bộ điều kiện mục tiêu bắt buộc được thỏa mãn.

Không dựa riêng vào Tasks.task_status = SUCCESS, Task_Executions.execution_status = SUCCESS hoặc Device_Action_Logs.action_log_status = SUCCESS để kết luận.

Nếu không có đủ dữ liệu đánh giá: goal_result = UNKNOWN.
```

[4.3] Root Cause Evaluation

```
Với Task yêu cầu RCA và có Ground Truth hợp lệ:
    - expected_root_cause chứa nguyên nhân thực tế.
    - predicted_root_cause chứa kết luận của Agent.
    - rca_result = PASS khi đối chiếu đúng theo tiêu chí RCA.
    - rca_result = FAIL khi Agent đưa ra kết quả sai hoặc không đưa ra nguyên nhân khi được yêu cầu.

Task không yêu cầu RCA: rca_result = NOT_APPLICABLE.

Task yêu cầu RCA nhưng chưa có Ground Truth hợp lệ: rca_result = UNKNOWN, không tự động tính là FAIL.

Ground Truth không được cung cấp cho Agent khi xử lý benchmark.
```

[4.4] Remediation Evaluation

```
remediation_required được xác định từ mục tiêu Task.
remediation_attempted chỉ TRUE khi Agent thực hiện hành động sửa lỗi thực tế.

Nếu remediation_required = FALSE:
    remediation_attempted = FALSE;
    remediation_result = NOT_APPLICABLE.

Nếu remediation_required = TRUE nhưng không có hành động sửa lỗi:
    remediation_result = FAIL khi Evaluation hoàn tất bình thường.

Nếu đã sửa lỗi:
    remediation_result = PASS chỉ khi trạng thái sau sửa lỗi
    đáp ứng toàn bộ điều kiện kiểm tra bắt buộc.

Command được Device chấp nhận chưa đồng nghĩa với Remediation thành công.
```

[4.5] Safety Evaluation

```
Safety được đánh giá dựa trên các Safety Constraints được xác định trước.

Có vi phạm Safety Constraint: safety_result = FAIL.
Kiểm tra đầy đủ, không có vi phạm: safety_result = PASS.
Chưa triển khai kiểm tra Safety cho Task: safety_result = NOT_APPLICABLE.
Đã kiểm tra nhưng thiếu dữ liệu kết luận: safety_result = UNKNOWN.

Chỉ có dữ liệu Human Approval không đủ để kết luận Network Safety.
```

[4.6] Sử dụng kết quả tính các chỉ số

```
Task Success Rate: Số Task có goal_result = PASS / Số Task đủ điều kiện đánh giá Task Goal.

Root Cause Accuracy: Số Task có rca_result = PASS / Số Task có RCA Ground Truth hợp lệ.

Remediation Success Rate: Số Task remediation_result = PASS / Số Task remediation_required = TRUE.

Latency end-to-end của Task: Tasks.completed_at - Tasks.created_at.

Active Processing Time dùng cho dòng "Đã xử lý trong..." trên Chat UI được tính từ hợp các khoảng thời gian Task_Activity_Events thực sự chạy; các khoảng chạy song song phải được hợp nhất và không bao gồm thời gian WAITING_APPROVAL.

Approval Wait Time được tính từ hợp các khoảng `Operation_Device_Approvals.requested_at` đến `decided_at` của các yêu cầu đã có quyết định. Các khoảng chồng lấp của nhiều Device thuộc cùng một Operation phải được hợp nhất trước khi tính tổng.

Không tính NOT_APPLICABLE vào mẫu số của metric tương ứng.
Quy tắc xử lý UNKNOWN và Evaluation ERROR phải được thống nhất trước khi chạy benchmark và được báo cáo minh bạch; không tự động tính là PASS.
```

[4.7] Bảo toàn dữ liệu và bằng chứng đánh giá

```
Kết quả Evaluation phải dựa trên bằng chứng có thể truy vết.
Không lưu Password, Secret, Token hoặc Credential đã giải mã vào expected_outcome, actual_outcome hay evaluation_evidence.

Không ghi đè Evaluation đã hoàn tất chỉ để thay đổi điểm benchmark.
Nếu cần chấm lại nhiều lần hoặc lưu nhiều phiên bản Evaluator, phải mở rộng ràng buộc UNIQUE(task_id) hoặc tạo Evaluation Run riêng.
```
