# Network domain

Domain này sở hữu inventory thiết bị, URL GNS3 và kết nối Netmiko.

## Thành phần

- `schemas.py`: contract cấu hình thiết bị và trạng thái mạng.
- `provider.py`: đọc YAML và giao tiếp với GNS3/Netmiko.
- `service.py`: use case được API hoặc agent tool adapter gọi.

Provider không chứa logic HTTP của FastAPI và không được import ngược từ `core`.
Khi agent cần thao tác mạng, adapter của agent chỉ gọi `NetworkService` thay vì gọi
Netmiko trực tiếp.
