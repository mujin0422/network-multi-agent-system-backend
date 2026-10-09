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

- `network`: inventory, GNS3 URL và kết nối thiết bị qua Netmiko.

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
