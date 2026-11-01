# NIKA benchmark proof of concept

PoC này chạy model NVIDIA đang cấu hình trong Backend trên một incident NIKA.
NIKA chịu trách nhiệm dựng lab, tiêm lỗi, cung cấp MCP tools và chấm điểm;
GNS3 cùng workflow vận hành hiện tại không bị thay đổi.

## Cấu trúc

- `nika.yaml`: cấu hình LangGraph ReAct harness và NVIDIA OpenAI-compatible API.
- `run-smoke.sh`: nạp `NVIDIA_API_KEY`/`NVIDIA_MODEL` từ `backend/.env` rồi chạy incident.

Secret chỉ tồn tại trong process benchmark và không được sao chép vào source NIKA.

## Chuẩn bị NIKA

Đặt NIKA cạnh `backend` và `frontend`:

```text
NetworkMultiAgentSystem/
├── backend/
├── frontend/
└── nika/
```

Cài đặt đầy đủ trên Linux host:

```bash
git clone --branch main https://github.com/sands-lab/nika.git ../nika
cd ../nika
./scripts/install.sh --skip-images
```

Installer cần `sudo` để nạp/persist module VRF, chỉnh inotify và thiết lập
Containerlab. Nếu chỉ thử scenario Kathará, có thể cài dependencies Python
trong `.venv`, nhưng cài đặt đầy đủ vẫn là cấu hình được hỗ trợ chính thức.

## Chạy smoke benchmark

Từ thư mục Backend:

```bash
./integrations/nika/run-smoke.sh
```

Incident mặc định là `dc_clos_s_link_down`. Có thể truyền incident khác:

```bash
./integrations/nika/run-smoke.sh <problem-id>
```

## Phạm vi PoC

Giai đoạn này xác nhận model hiện tại có thể:

1. Nhận mô tả incident từ NIKA.
2. Gọi MCP troubleshooting tools trong lab.
3. Tạo báo cáo chẩn đoán.
4. Submit detection, localization và root cause để NIKA chấm điểm.

PoC chưa thay thế Planner/Network/Analyst hiện tại. Bước tiếp theo là xây custom
NIKA agent adapter để tái sử dụng prompt, activity event và audit của hệ thống.
