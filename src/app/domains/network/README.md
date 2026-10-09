# Network domain

Domain này sở hữu URL GNS3 và khả năng kết nối/thực thi qua Netmiko. Thiết bị và
credential được quản lý tập trung trong PostgreSQL; domain không đọc file YAML.

## Thành phần

- `schemas.py`: contract cấu hình thiết bị và trạng thái mạng.
- `repository.py`: đọc thiết bị và credential mã hóa từ PostgreSQL.
- `provider.py`: mở kết nối thiết bị qua Netmiko.
- `service.py`: use case được API hoặc agent tool adapter gọi.

Provider không chứa logic HTTP của FastAPI và không được import ngược từ `core`.
Khi agent cần thao tác mạng, adapter của agent chỉ gọi `NetworkService` thay vì gọi
Netmiko trực tiếp.
