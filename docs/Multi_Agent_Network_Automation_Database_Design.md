# DATABASE DESIGN — MULTI-AGENT NETWORK AUTOMATION PLATFORM

## 1. Phạm vi và nguyên tắc

Đây là thiết kế database phiên bản đầu tiên (v1) của dự án, đã đồng bộ với
schema PostgreSQL tại
`docker/postgres/init/01_schema.sql` và dữ liệu mẫu tại
`docker/postgres/init/02_seed.sql.template`.

Database chịu trách nhiệm lưu:

- tài khoản, phiên đăng nhập, vai trò và quyền;
- inventory thiết bị và credential đã mã hóa;
- conversation/message từ Chat UI;
- Task, execution plan, execution và audit command;
- command thực thi trên thiết bị và kết quả audit;
- kết quả evaluation/benchmarking.

Agent và Tool không phải master data trong database. Tên Agent/Tool tại
`task_executions` chỉ là metadata audit; implementation nằm trong code.

Các nguyên tắc an toàn:

- mật khẩu người dùng được hash bằng bcrypt;
- refresh token chỉ lưu hash và tách riêng theo từng session;
- password/secret thiết bị dùng mã hóa đối xứng có thể giải mã; khóa mã hóa
  không nằm trong database hoặc source code;
- input/output/log không được chứa credential đã giải mã;
- command READ/WRITE được audit theo task, operation, execution và thiết bị;
- dữ liệu audit dùng `ON DELETE RESTRICT`, không cascade theo thao tác UI.

## 2. Quy ước schema vật lý

- Tất cả timestamp dùng `TIMESTAMPTZ` và ứng dụng ghi theo UTC.
- ID nghiệp vụ dùng `VARCHAR(64)` với prefix dễ nhận biết; audit/evaluation dùng
  UUID khi không cần ID hiển thị.
- Tên cột vật lý giữ nguyên tên trong tài liệu, không dùng tên rút gọn cần ánh
  xạ. Ví dụ: `user_status`, `task_status`, `task_type`, `operation_intent`,
  `operation_status`, `operation_parameters`, `operation_device_status`,
  `execution_status`, `action_log_status` và `evaluation_status`.

## 3. Danh sách 20 bảng

### 3.1 Authentication & Authorization

| Bảng | Mục đích chính |
| --- | --- |
| `roles` | Vai trò hệ thống và metadata audit. |
| `management_functions` | Module/chức năng được phân quyền. |
| `actions` | Hành động Add/Edit/Delete/View/Execute/Approve. |
| `permissions` | Một cặp duy nhất function + action. |
| `role_permissions` | Quan hệ nhiều-nhiều giữa role và permission. |
| `users` | Tài khoản, password hash, role và trạng thái. |
| `user_sessions` | Một user có nhiều refresh-token session độc lập. |

`refresh_token` và `expires_at` không đặt trong `users`, vì cách đó chỉ cho một
phiên trên một tài khoản và làm mất khả năng thu hồi từng thiết bị đăng nhập.

### 3.2 Network Inventory

| Bảng | Mục đích chính |
| --- | --- |
| `brands` | Hãng và danh sách Netmiko driver được hỗ trợ. |
| `categories` | Router/Switch/Firewall/... |
| `credentials` | Credential dùng lại cho nhiều device, lưu ciphertext. |
| `devices` | Endpoint kết nối, driver, vị trí và audit user. |

Ràng buộc/trigger quan trọng:

- `devices.hostname` là duy nhất;
- `(devices.host, devices.port)` là duy nhất;
- port thuộc `[1, 65535]`;
- `device_type` phải thuộc `brands.supported_drivers`;
- `brands.supported_drivers` là JSON array gồm string không rỗng, không trùng;
- `created_by` không đổi khi update; `last_updated_by` ghi người cập nhật gần nhất.

### 3.3 Conversation Management

| Bảng | Mục đích chính |
| --- | --- |
| `conversations` | Phiên chat thuộc một user. |
| `messages` | Message USER/AGENT trong conversation. |

Khi thêm message, trigger cập nhật `conversations.last_updated_at` để danh sách
hội thoại có thể sắp xếp đúng theo hoạt động gần nhất.

### 3.4 AI Execution Management

| Bảng | Mục đích chính |
| --- | --- |
| `tasks` | Yêu cầu gốc và trạng thái end-to-end. |
| `task_operations` | Các intent logic do Planner tạo. |
| `operation_dependencies` | DAG dependency giữa operation trong cùng task. |
| `task_operation_devices` | Device, role và access mode của từng operation. |
| `task_executions` | Mỗi lần Agent/Tool thực thi. |
| `device_action_logs` | Command thực tế đã gửi xuống device. |

Task source trigger bảo đảm:

- source message là message `USER`;
- message thuộc đúng conversation;
- task user là owner của conversation;
- `input_message` giữ nguyên nội dung message nguồn.

Dependency trigger bảo đảm hai operation cùng task, không tự phụ thuộc và không
tạo chu trình. Execution trigger bảo đảm task → operation → operation-device
không bị liên kết chéo.

### 3.5 AI Evaluation & Benchmarking

| Bảng | Mục đích chính |
| --- | --- |
| `task_evaluations` | Goal, RCA, remediation, safety và evidence của task. |

Mỗi Task có tối đa một evaluation trong phiên bản hiện tại. Chỉ Task đã ở trạng
thái kết thúc (`SUCCESS`, `PARTIAL_SUCCESS`, `FAILED`, `REJECTED`) mới được đánh
giá. Trạng thái workflow không được dùng thay cho kết quả goal evaluation.

## 4. Quan hệ chính

```text
roles ──< users ──< user_sessions
  │         │
  │         ├──< conversations ──< messages
  │         │          │               │
  │         │          └──< tasks >────┘ source_message_id
  │         │                  │
  │         │                  ├──< task_operations
  │         │                  │       ├──< operation_dependencies
  │         │                  │       └──< task_operation_devices >── devices
  │         │                  │                  │
  │         │                  ├──< task_executions
  │         │                  ├──< device_action_logs
  │         │                  └──── task_evaluations
  │         │
  │         └── audit FK: created_by / last_updated_by / approved_by
  │
  └──< role_permissions >── permissions >── management_functions/actions

brands/categories/credentials ──< devices
```

## 5. Vòng đời Task

`tasks.task_status`:

- `PENDING`: chưa được Planner xử lý;
- `PLANNING`: đang tạo execution plan;
- `RUNNING`: Orchestrator đang thực thi hoặc chờ approval;
- `SUCCESS`: mục tiêu bắt buộc hoàn tất;
- `PARTIAL_SUCCESS`: có kết quả dùng được nhưng chưa hoàn tất toàn bộ;
- `FAILED`: mục tiêu không hoàn thành do lỗi;
- `REJECTED`: WRITE bắt buộc bị từ chối và không có kết quả đủ để tính partial.

`tasks.task_type`:

- `UNCLASSIFIED`;
- `INFORMATION_RETRIEVAL`;
- `DIAGNOSIS`;
- `CONFIGURATION`;
- `REMEDIATION`;
- `COMPOSITE`.

`started_at` bắt buộc từ `PLANNING`; `completed_at` chỉ có ở trạng thái kết thúc.

## 6. Audit thao tác thiết bị

`device_action_logs` ghi lại từng command READ/WRITE thực tế đã gửi xuống thiết
bị và liên kết nó với Task, Operation, operation-device và execution tương ứng.
Trigger kiểm tra các liên kết này thuộc cùng một luồng thực thi, tránh audit log
tham chiếu chéo giữa các Task hoặc thiết bị.

`device_action_logs.action_type` giữ nghĩa audit cấp cao `READ`/`WRITE`.
`action_phase` bổ sung chi tiết `PRE_CHECK`, `APPLY`, `POST_CHECK`, `ROLLBACK`,
`ROLLBACK_VERIFY` mà không làm sai định nghĩa READ/WRITE trong tài liệu.

`action_log_status = UNKNOWN` dùng khi command có thể đã được gửi nhưng kết quả cuối không
xác định. Với WRITE/UNKNOWN, không tự động retry nếu chưa chứng minh thao tác có
tính idempotent.

## 7. Dữ liệu seed

Seed gồm:

- 4 role, 8 management function, 6 action và 20 permission;
- 4 tài khoản development theo từng role;
- 5 brand kèm supported driver và 5 category;
- 1 credential GNS3 được mã hóa AES-256 qua `pgcrypto`;
- 13 thiết bị Cisco: P1, P2, PE1, PE2, CE-1A/B, CE-2A/B, Switch1-4, P3;
- 1 conversation và 2 message;
- 1 Task `COMPOSITE` hoàn chỉnh;
- 3 operation, 2 dependency và 3 device mapping;
- 6 execution (Planner, Network, Analyst);
- 5 device action log (READ, PRE_CHECK, WRITE/APPLY, POST_CHECK);
- 1 evaluation `PASS` có evidence.

Không seed `user_sessions`, vì refresh token giả không có giá trị nghiệp vụ và
dễ tạo thói quen xử lý secret sai.

## 8. Nguồn sự thật và cách khởi tạo

- Schema: `docker/postgres/init/01_schema.sql`.
- Seed: `docker/postgres/init/02_seed.sql.template`.
- Khóa credential được `02_seed.sh` truyền qua biến psql `encryption_key` từ
  `DEVICE_CREDENTIAL_ENCRYPTION_KEY`; không được ghi cứng vào SQL.
- Init script của PostgreSQL chỉ chạy khi data volume còn trống. Với database đã
  có dữ liệu, chạy `python scripts/migrate.py` hoặc
  `docker compose run --rm migrate`; không xóa volume production.
- `migrations/versions/0001_initial_schema.sql` là migration đầu tiên và tham
  chiếu trực tiếp canonical DDL trong `01_schema.sql`.
- Migration đã chạy được lưu tại `schema_migrations` cùng SHA-256 checksum.
  Runner dùng transaction và advisory lock, đồng thời từ chối database không
  trống nhưng không khớp schema v1 thay vì tự động sửa/xóa dữ liệu.

Tài khoản seed chỉ dùng ở development. Mật khẩu mẫu phải được thay hoặc loại bỏ
hoàn toàn ở staging/production.
