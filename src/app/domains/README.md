# Domains

Mỗi domain sở hữu nghiệp vụ, contract và persistence của chính nó. Hai domain
không import trực tiếp implementation của nhau.

## Cấu trúc chuẩn

```text
domain/
  schemas.py      # Pydantic input/output contract
  provider.py     # external source: HTTP, RSS, Selenium, vendor API
  service.py      # use case orchestration
  README.md       # ownership và hướng dẫn mở rộng
```

`models.py` và `repository.py` chỉ được thêm khi domain có persistence. Module hỗ trợ như `router.py`, `registry.py` hoặc `base.py` được phép khi đó là khái niệm riêng của domain.

## Domain hiện tại

- `network`: GNS3 và khả năng kết nối/thực thi trên thiết bị qua Netmiko.
- `inventory`: public service quản lý metadata thiết bị và constraint duy nhất.
- `conversation`: public service quản lý conversation và message.
- `execution`: public service quản lý Task, Operation, approval và ChangeSet.

`inventory` dùng PostgreSQL khi chạy Docker và giữ adapter in-memory cho unit
test. `network` đọc cấu hình kết nối từ PostgreSQL qua repository riêng; password
được giải mã chỉ khi cần mở kết nối Netmiko và không nằm trong response API.

## Dependency direction

```text
provider -> schema + core
repository -> model + schema
service -> provider + repository
api/worker/agent -> service
```

Provider không ghi database trực tiếp. Repository không gọi website bên ngoài.

Service là nơi phối hợp hai phần này. API không đi tắt vào provider/repository.

Agent và agent tool adapter được đặt ngoài domain, trong `agents/` (ví dụ `agents/tools/network.py`), và chỉ gọi public service của domain. Điều này giữ domain độc lập với framework agent.
