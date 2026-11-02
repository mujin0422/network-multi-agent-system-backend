#!/usr/bin/env bash
set -euo pipefail

BACKEND_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORKSPACE_ROOT="$(cd "${BACKEND_ROOT}/.." && pwd)"
NIKA_HOME="${NIKA_HOME:-${WORKSPACE_ROOT}/nika}"
RUN_CONFIG="${BACKEND_ROOT}/integrations/nika/nika.yaml"
PROBLEM_ID="${1:-dc_clos_s_link_down}"

if [[ ! -x "${NIKA_HOME}/.venv/bin/nika" ]]; then
  echo "NIKA chưa được cài tại ${NIKA_HOME}." >&2
  echo "Xem hướng dẫn: ${BACKEND_ROOT}/integrations/nika/README.md" >&2
  exit 1
fi

if [[ ! -f "${BACKEND_ROOT}/.env" ]]; then
  echo "Không tìm thấy ${BACKEND_ROOT}/.env." >&2
  exit 1
fi

# Chỉ đọc hai biến cần thiết bằng dotenv. Không `source` toàn bộ .env vì các
# giá trị như APP_NAME có thể chứa khoảng trắng và không phải shell script.
NIKA_MODEL="${NIKA_MODEL:-$(
  "${NIKA_HOME}/.venv/bin/python" -c \
    'from dotenv import dotenv_values; import sys; print(dotenv_values(sys.argv[1]).get("NVIDIA_MODEL", ""))' \
    "${BACKEND_ROOT}/.env"
)}"
NIKA_CUSTOM_API_KEY="${NIKA_CUSTOM_API_KEY:-$(
  "${NIKA_HOME}/.venv/bin/python" -c \
    'from dotenv import dotenv_values; import sys; print(dotenv_values(sys.argv[1]).get("NVIDIA_API_KEY", ""))' \
    "${BACKEND_ROOT}/.env"
)}"

if [[ -z "${NIKA_MODEL}" || -z "${NIKA_CUSTOM_API_KEY}" ]]; then
  echo "NVIDIA_MODEL và NVIDIA_API_KEY phải được cấu hình trong backend/.env." >&2
  exit 1
fi

export NIKA_CUSTOM_API_KEY

exec "${NIKA_HOME}/.venv/bin/nika" agent run \
  --run-config "${RUN_CONFIG}" \
  --model "${NIKA_MODEL}" \
  --problem "${PROBLEM_ID}"
