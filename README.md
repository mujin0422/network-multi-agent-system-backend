# Multi-Agent AI Network Automation Backend

FastAPI backend thử nghiệm cho nền tảng tự động hóa mạng bằng nhiều AI Agent.
Ứng dụng được tổ chức theo domain service: API và Agent chỉ gọi public service,
không truy cập trực tiếp repository hoặc provider nội bộ của domain.

## Yêu cầu

- Python 3.11 trở lên
- GNS3 Server nếu cần kết nối topology thật
- NVIDIA API key nếu sử dụng LLM

## Cài đặt cho môi trường phát triển

### Linux/macOS

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

### Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Lệnh editable install giúp import package `app` mà không cần đặt
`PYTHONPATH=src`. Setuptools có thể sinh `src/network_multi_agent_backend.egg-info`;
đây là metadata build và đã được Git ignore.

## Cấu hình môi trường

Tạo `.env` từ template:

```bash
cp .env.example .env
```

Các nhóm cấu hình chính trong `.env.example`:

- Application và logging
- NVIDIA AI provider
- Identity token signing secret and token lifetimes
- GNS3
- PostgreSQL device inventory
- Network connection timeout

Không commit `.env` vì file này chứa secret.

## Cấu hình thiết bị

Thiết bị được quản lý tập trung trong PostgreSQL qua API `/api/v1/devices`.
Backend không còn đọc `config/devices.yaml`. Khi agent cần kết nối, backend tìm
thiết bị bằng `id` hoặc `hostname` và lấy credential đã mã hóa từ database.

## Chạy API

Development với auto-reload:

```bash
fastapi dev src/app/main.py --host 0.0.0.0 --port 8000
```

Production mode, không auto-reload:

```bash
fastapi run src/app/main.py --host 0.0.0.0 --port 8000
```

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

Health check:

```text
GET http://127.0.0.1:8000/health
```

### API versioning

Toàn bộ public business API dùng prefix `/api/v1`. Ví dụ:

```text
GET  /api/v1/conversations/
GET  /api/v1/devices/
GET  /api/v1/tasks/
```

`v1` là version của HTTP contract, độc lập với version phát hành của ứng dụng.
Khi cần breaking change, tạo router `/api/v2` và giữ `/api/v1` trong thời gian
chuyển đổi; không thay đổi hành vi của `v1` âm thầm. Endpoint hạ tầng `/health`
không thuộc business API nên không đặt dưới prefix version.

## Docker: API, PostgreSQL và pgAdmin 4

Docker Compose khởi tạo ba service:

- `api`: FastAPI tại `http://localhost:8000`
- `db`: PostgreSQL tại `localhost:2204` (mặc định `POSTGRES_PORT`)
- `pgadmin`: pgAdmin 4 tại `http://localhost:5050`

Kiểm tra các biến `POSTGRES_*`, `PGADMIN_*` và
`DEVICE_CREDENTIAL_ENCRYPTION_KEY` trong `.env`, sau đó chạy:

```bash
docker compose config --quiet
docker compose build
docker compose up -d
docker compose ps
```

Xem log:

```bash
docker compose logs -f db
docker compose logs -f api
docker compose logs -f pgadmin
```

### Kết nối pgAdmin 4

Đăng nhập `http://localhost:5050` bằng:

```text
Email:    giá trị PGADMIN_DEFAULT_EMAIL trong .env
Password: giá trị PGADMIN_DEFAULT_PASSWORD trong .env
```

Server `mujin-server` được đăng ký tự động với cấu hình mặc định. Nếu
bạn thay `POSTGRES_DB` hoặc `POSTGRES_USER`, chạy `Register > Server` và nhập:

```text
Name:                 mujin-server
Host name/address:    db
Port:                 5432
Maintenance database: giá trị POSTGRES_DB
Username:             giá trị POSTGRES_USER
Password:             giá trị POSTGRES_PASSWORD
```

`db` là hostname dùng khi pgAdmin chạy trong cùng Docker Compose. Nếu dùng một
pgAdmin cài trực tiếp trên máy, host là `localhost` và port là `POSTGRES_PORT`.

### Kiểm tra schema

```bash
docker compose exec db psql \
  -U network_automation_user \
  -d network_automation_db \
  -c "\\dt"

```

Schema có 22 bảng nghiệp vụ, gồm authentication/RBAC, inventory, conversation,
AI runtime, activity timeline, operation-device approval và evaluation/benchmarking.
Docker bootstrap tạo schema rồi chèn reference/development seed từ
`02_seed.sql.template`. Init script chỉ chạy khi PostgreSQL volume được tạo lần đầu.

### Initial migration

Không xóa volume chỉ để nhận schema mới. Chạy migration có version:

```bash
docker compose run --rm migrate
```

Kiểm tra migration nào đã chạy hoặc còn chờ:

```bash
docker compose run --rm migrate python scripts/migrate.py --status
```

`0001_initial_schema.sql` là version đầu tiên của dự án và dùng chung canonical
DDL với `01_schema.sql`. Runner dùng checksum, transaction và PostgreSQL advisory
lock. Database không trống nhưng không đúng initial schema sẽ bị từ chối thay vì
tự động thay đổi. Chi tiết xem
[`migrations/README.md`](migrations/README.md).

Muốn chạy lại schema từ đầu, lệnh sau sẽ **xóa toàn bộ dữ liệu database và
pgAdmin đang lưu trong Docker volumes**:

```bash
docker compose down -v
docker compose up -d --build
```

Dừng hệ thống nhưng giữ dữ liệu:

```bash
docker compose down
```

Khi thêm Device chạy trên GNS3 của máy host, dùng `host.docker.internal` làm
`host` để API trong container có thể kết nối tới console của thiết bị.

Sau khi lưu USER message, route gọi GNS3 Controller `GET /v2/version` để
kiểm tra GNS3 Server có đang bật hay không. Nếu không truy cập được,
API trả HTTP `503` và không gọi Planner. Bước này không mở project,
không bật node và không khởi động tiến trình GNS3 trên hệ điều hành.

```env
GNS3_IP=127.0.0.1
GNS3_PORT=3080
GNS3_REQUEST_TIMEOUT=10
```

## Chạy test

Sau khi cài editable package, unit test identity không cần PostgreSQL:

```bash
pytest tests/domains/test_identity_service.py -q
```

Identity API cần PostgreSQL đã có schema và ít nhất một Role/User hợp lệ. Với
Docker Compose, tạo `.env`,
đặt secret ngẫu nhiên cho `AUTH_JWT_SECRET`, `POSTGRES_PASSWORD`,
`PGADMIN_DEFAULT_PASSWORD` và `DEVICE_CREDENTIAL_ENCRYPTION_KEY`, sau đó chạy:

```bash
docker compose up -d --build
docker compose ps
curl http://localhost:8000/health
```

Sau khi database mới được bootstrap, đăng nhập bằng tài khoản seed rồi kiểm tra
token và quyền qua API:

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \\
  -H 'Content-Type: application/json' \\
  -d '{"email":"phamdinhduythai@gmail.com","password":"Admin@123"}'
```

Lấy `access_token` trong response và dùng header `Authorization: Bearer <token>`
để gọi `/api/v1/auth/me` hoặc route cần quyền như `/api/v1/devices/`. Refresh
bằng `POST /api/v1/auth/refresh` với `{"refresh_token":"..."}`; refresh token cũ
sẽ bị thu hồi. Swagger UI tại `/docs` cho phép thực hiện các bước này trực tiếp.

Luồng chỉ tạo Conversation khi người dùng gửi Message đầu tiên được mô tả tại
[`docs/conversation-first-message-flow.md`](docs/conversation-first-message-flow.md).

Các luồng bảo mật và thực thi chi tiết:

- [End-to-end từ USER message đến khi thực thi hoàn tất](docs/end-to-end-ai-request-execution-flow.md)
- [Credential thiết bị, đăng nhập và thực thi command](docs/network-device-credential-execution-flow.md)
- [Đăng nhập API, JWT, session và phân quyền RBAC](docs/authentication-authorization-jwt-flow.md)

Chạy toàn bộ test:

```bash
pytest
```

`pyproject.toml` cũng khai báo `src` trong pytest config, vì vậy test vẫn nhận ra
package khi chạy từ project root.

## Domain hiện tại

```text
src/app/domains/
├── identity/        # Authentication, session và RBAC
├── inventory/       # Device inventory, GNS3 và Netmiko access
├── conversation/    # Conversation và Message
├── execution/       # Task, Operation và audit
└── evaluation/      # Evaluation và benchmarking (planned)
```

Các domain sử dụng PostgreSQL repository qua dependency injection. Unit test có
thể thay repository thật bằng stub mà không đổi route hoặc domain service.

## Source layout

```text
src/app/
├── agents/          # Agent implementations, registry và routing
├── core/            # Settings, logging, ID và shared errors
├── domains/         # Domain services, persistence và HTTP routers
├── tools/           # Agent tool adapters
└── main.py           # FastAPI entry point và router composition
```
