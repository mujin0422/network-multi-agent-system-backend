# Tools

`tools` chứa adapter thực thi hành động cụ thể cho agent. Tool không quyết định
workflow, không phân tích yêu cầu người dùng và không sở hữu business state.

## Cấu trúc

```text
tools/
├── README.md
├── __init__.py
└── network/
    ├── __init__.py
    ├── protocol.py
    ├── schemas.py
    └── backends/
        ├── __init__.py
        ├── netmiko.py
        └── nornir.py
```

### `protocol.py`

Định nghĩa `NetworkTool` contract. Network Agent phụ thuộc contract này thay vì
phụ thuộc trực tiếp vào Netmiko, nhờ đó có thể test bằng stub và thay adapter.

### `schemas.py`

Định nghĩa dữ liệu thô do tool trả về, hiện tại là `CommandResult`. Schema tool
không chứa password, secret hoặc connection object.

### `backends/netmiko.py`

Triển khai `NetmikoNetworkTool`:

1. Gọi public `NetworkService` để mở kết nối.
2. `NetworkService` dùng Inventory provider/repository để tải và giải mã
   credential.
3. Dùng `send_command` cho READ.
4. Dùng `send_config_set` cho WRITE.
5. Luôn `disconnect()` trong `finally`.
6. Chỉ trả command và output, không trả credential.

### `backends/nornir.py`

Triển khai `NornirNetworkTool`. Nornir điều phối execution, còn
`nornir-netmiko` là plugin đăng nhập và gửi command:

1. Lấy `DeviceConfig` đã giải mã thông qua `NetworkService`.
2. Tạo inventory động trong memory, không tạo YAML chứa secret.
3. Chạy bằng `ThreadedRunner` với số worker lấy từ cấu hình.
4. READ dùng `netmiko_send_command`; WRITE dùng `netmiko_send_config`.
5. Chuẩn hóa output về cùng `CommandResult` contract.

## Chọn backend

```env
# Thực thi trực tiếp bằng Netmiko (mặc định)
NETWORK_BACKEND=netmiko

# Nornir điều phối, Netmiko thực hiện kết nối
NETWORK_BACKEND=nornir
NORNIR_NUM_WORKERS=20
```

`netmiko` phù hợp với luồng một thiết bị. `nornir` là lựa chọn để mở rộng thực
thi song song nhiều thiết bị. Agent không cần thay đổi khi chuyển backend.

## Ranh giới trách nhiệm

Tool được phép:

- Gọi public domain service.
- Gọi SDK/framework bên ngoài như Netmiko.
- Chuyển đổi input kỹ thuật thành lời gọi SDK.
- Trả kết quả thực thi thô hoặc phát sinh lỗi kỹ thuật.

Tool không được phép:

- Truy cập ORM model hoặc repository trực tiếp.
- Tạo Task, Operation hoặc cập nhật workflow state.
- Tự quyết định thiết bị, command hoặc access mode.
- Phân tích kết quả hoặc tạo câu trả lời cho người dùng.
- Ghi password, secret hay token vào log/result.

## Luồng gọi chuẩn

```text
ExecutionOrchestrator
  → NetworkAgent
  → NetworkTool contract
  → NetmikoNetworkTool hoặc NornirNetworkTool
  → NetworkService
  → DeviceConnectionProvider
  → Netmiko hoặc nornir-netmiko
  → thiết bị mạng
```

Không gọi theo chiều ngược lại. Tool không được gọi Orchestrator hoặc Agent.

## Mở rộng

Khi thêm integration mới, tạo package riêng theo capability:

```text
tools/
├── network/
├── retrieval/
└── notification/
```

Mỗi package chỉ nên có protocol, schema và implementation thực sự cần thiết;
không tạo folder/file giữ chỗ.
