# Agents

`agents` là application layer điều phối AI và execution workflow. Agent không
sở hữu database table, không dùng repository/ORM trực tiếp và không expose HTTP
API riêng. Frontend gửi yêu cầu qua Message API của Conversation domain.

## Cấu trúc

```text
agents/
├── __init__.py
├── dependencies.py
├── planner/
│   ├── __init__.py
│   ├── agent.py
│   └── prompts.py
├── network/
│   ├── __init__.py
│   ├── agent.py
│   └── schemas.py
├── analyst/
│   ├── __init__.py
│   ├── agent.py
│   ├── prompts.py
│   └── schemas.py
└── orchestrator/
    ├── __init__.py
    ├── planning.py
    └── execution.py
```

Không dùng một `BaseAgent` chung vì mỗi agent có input/output và trách nhiệm
khác nhau. Không dùng registry hoặc keyword router để chọn agent; execution plan
và orchestrator quyết định thành phần cần gọi.

## Planner Agent

**Chức năng:** Chuyển USER message và public device inventory thành
`ExecutionPlanCreate` có cấu trúc.

Planner tạo mô tả cho:

- `task_operations`
- `operation_dependencies`
- `task_operation_devices`

Planner dùng NVIDIA LLM với structured output. Planner không ghi database, giải
mã credential, kết nối thiết bị hoặc thực thi command.

Các quy tắc chính:

- Chỉ dùng device ID được Orchestrator cung cấp.
- Dependency chỉ tham chiếu operation đứng trước.
- SOURCE/CONTEXT chỉ được READ.
- TARGET có thể READ hoặc WRITE.
- Operation WRITE phải phụ thuộc bước kiểm tra/phân tích cần thiết.
- `operation_intent`, enum và command giữ dạng kỹ thuật; nội dung diễn giải dùng
  tiếng Việt.

## Network Agent

**Chức năng:** Execution worker chạy operation trên từng thiết bị đã được Planner
gán qua `TaskOperationDevice`.

Input:

```text
Operation + TaskOperationDevice
```

Output:

```text
NetworkExecutionResult
```

Network Agent không dùng LLM và không phân tích output. Agent đọc command từ
`operation_parameters`, kiểm tra mapping rồi gọi `NetworkTool`. Backend có thể
là Netmiko trực tiếp hoặc Nornir kết hợp plugin Netmiko:

- READ → `send_command`
- WRITE → `send_config_set`

Các thư viện network là blocking I/O nên tool được gọi qua `asyncio.to_thread`;
event loop của FastAPI không bị chặn trong thời gian SSH/Telnet.

## Analyst Agent

**Chức năng:** Phân tích execution output và trả `AnalysisResult` bằng tiếng
Việt.

Analyst có thể tạo summary, findings, likely causes và recommendations. Analyst
không kết nối thiết bị, không chạy command và không tự thay đổi cấu hình.

## Planning Orchestrator

`PlanningOrchestrator` điều phối luồng:

```text
USER Message
  → tạo Task
  → lấy public Device inventory
  → gọi PlannerAgent
  → kiểm tra device ID
  → gọi ExecutionService lưu execution plan
```

Execution domain sinh ID, timestamp và trạng thái ban đầu. Ba nhóm record của
plan được PostgreSQL repository lưu trong cùng một transaction.

## Execution Orchestrator

`ExecutionOrchestrator` điều phối luồng:

```text
TaskDetail
  → sắp xếp Operation theo display_order
  → ExecutionService đọc lại Operation
  → lấy các TaskOperationDevice
  → gọi NetworkAgent cho từng mapping
  → thu thập NetworkExecutionResult
  → dừng chuỗi nếu một thiết bị thực thi thất bại
```

Operation được chạy tuần tự nên dependency luôn được xử lý sau
operation đứng trước. `ON_SUCCESS` chỉ cho phép chạy khi operation tiên
quyết thành công; `ON_COMPLETION` chấp nhận mọi trạng thái kết thúc.

Trong khi chạy, Orchestrator cập nhật lifecycle của Task, Operation và
TaskOperationDevice; mỗi lần gọi Network Agent được ghi vào
`task_executions`, còn command thực sự được backend trả kết quả được
ghi vào `device_action_logs`. Approval và retry trong tương lai vẫn thuộc
Execution Orchestrator/Execution domain, không đưa vào Network Agent hay tool.

## Dependency composition

`dependencies.py` là composition root cho agent layer:

- Khởi tạo NVIDIA chat model và Planner Agent.
- Khởi tạo Planning/Execution Orchestrator.
- Khởi tạo Network Agent và backend được chọn bởi `NETWORK_BACKEND`.
- Kết nối agent với public domain services.

File này không chứa business rule.

## Luồng phụ thuộc

```text
Message Router
  → PlanningOrchestrator
      ├── PlannerAgent
      ├── DeviceService
      └── ExecutionService
  → ExecutionOrchestrator
      ├── ExecutionService
      └── NetworkAgent
          └── NetworkTool
              ├── NetmikoNetworkTool
              └── NornirNetworkTool
                  └── NetworkService
```

Các cách gọi bị cấm:

```text
Agent   ─X→ ORM Model/Repository/Database
Planner ─X→ NetworkTool/DeviceConnectionProvider
Network ─X→ CredentialRepository/Netmiko/Nornir trực tiếp
Analyst ─X→ NetworkTool/DeviceConnectionProvider
Tool    ─X→ ExecutionRepository
Domain  ─X→ Agent implementation
```

## HTTP boundary

Không có `/api/v1/chat` hoặc `/api/v1/agents`. Điểm vào từ frontend là:

```text
POST /api/v1/conversations/{conversation_id}/messages
```

Chỉ USER message kích hoạt planning. Sau khi plan được lưu thành công,
route gọi Execution Orchestrator ngay trong cùng request. Agent và tool là
implementation nội bộ, không cho frontend lựa chọn hoặc gọi trực tiếp.
