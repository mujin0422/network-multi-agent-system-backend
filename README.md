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
POST /api/v1/chat/
GET  /api/v1/agents/
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

### Kiểm tra schema và dữ liệu seed

```bash
docker compose exec db psql \
  -U network_automation_user \
  -d network_automation_db \
  -c "\\dt"

docker compose exec db psql \
  -U network_automation_user \
  -d network_automation_db \
  -c "SELECT hostname, host, port, device_type FROM devices ORDER BY port;"
```

Schema có 20 bảng nghiệp vụ, gồm authentication/RBAC, inventory, conversation,
AI runtime và evaluation/benchmarking.
Init script chỉ chạy khi PostgreSQL volume được tạo lần đầu.

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

Muốn chạy lại schema/seed từ đầu, lệnh sau sẽ **xóa toàn bộ dữ liệu database và
pgAdmin đang lưu trong Docker volumes**:

```bash
docker compose down -v
docker compose up -d --build
```

Dừng hệ thống nhưng giữ dữ liệu:

```bash
docker compose down
```

Các device được seed với `host = 127.0.0.1` đúng dữ liệu đầu vào. Khi backend
chạy trong container và cần kết nối console GNS3 trên máy host, cập nhật `host`
thành `host.docker.internal` hoặc bổ sung bước ánh xạ tại network provider.

## Chạy test

Sau khi cài editable package:

```bash
pytest
```

`pyproject.toml` cũng khai báo `src` trong pytest config, vì vậy test vẫn nhận ra
package khi chạy từ project root.

## Domain hiện tại

```text
src/app/domains/
├── identity/        # User, session và RBAC (planned)
├── inventory/       # Device inventory, GNS3 và Netmiko access
├── conversation/    # Conversation và Message
├── execution/       # Task, Operation và audit
└── evaluation/      # Evaluation và benchmarking (planned)
```

`conversation` và `execution` hiện dùng repository in-memory để
frontend có thể test contract API. Dữ liệu mất khi API restart. Repository SQL có
thể được thay qua dependency injection mà không đổi route hoặc domain service.

## Source layout

```text
src/app/
├── agents/          # Agent implementations, registry và routing
├── core/            # Settings, logging, ID và shared errors
├── domains/         # Domain services, persistence và HTTP routers
├── tools/           # Agent tool adapters
└── main.py           # FastAPI entry point và router composition
```

Prototype cũ được lưu riêng trong `src_legacy/` để tham khảo; nó không thuộc
package được khai báo trong `pyproject.toml` và không phải một phần của schema v1.
