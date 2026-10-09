#!/usr/bin/env bash
set -Eeuo pipefail

# PostgreSQL entrypoint chạy file này duy nhất khi volume database còn trống.
# Khóa mã hóa chỉ được truyền qua environment/psql variable, không ghi vào SQL.
: "${DEVICE_CREDENTIAL_ENCRYPTION_KEY:?DEVICE_CREDENTIAL_ENCRYPTION_KEY is required}"

psql \
  --username "${POSTGRES_USER}" \
  --dbname "${POSTGRES_DB}" \
  --set ON_ERROR_STOP=1 \
  --set encryption_key="${DEVICE_CREDENTIAL_ENCRYPTION_KEY}" \
  --file /docker-entrypoint-initdb.d/02_seed.sql.template
