# Database migrations

Đây là migration history đầu tiên của dự án mới. Project dùng SQL có version vì
persistence layer sử dụng `psycopg` trực tiếp, không dùng SQLAlchemy ORM.

## Initial version

`0001_initial_schema.sql` đại diện cho toàn bộ schema v1. File dùng directive
`-- @canonical-schema`; runner lấy DDL từ
`docker/postgres/init/01_schema.sql`. Nhờ đó Docker bootstrap và migration không
duy trì hai bản SQL giống nhau dễ bị lệch.

Nếu PostgreSQL đã được Docker init bằng `01_schema.sql`, runner kiểm tra các bảng
và cột đặc trưng rồi ghi version `0001` mà không chạy lại `CREATE TABLE`.
Database không trống nhưng không khớp initial schema sẽ bị từ chối.

## Quy ước

- File nằm trong `migrations/versions`.
- Tên file: `NNNN_ten_migration.sql`.
- Migration đã chạy không được sửa; runner kiểm tra SHA-256 checksum.
- Mỗi migration chạy trong transaction riêng.
- PostgreSQL advisory lock ngăn hai instance migrate đồng thời.
- Không đặt seed/demo data trong migration.
- Migration chỉ đi lên; rollback schema phải là một migration mới.

## Chạy migration

Local:

```bash
python scripts/migrate.py
python scripts/migrate.py --status
```

Docker Compose:

```bash
docker compose run --rm migrate
docker compose run --rm migrate python scripts/migrate.py --status
```

## Tạo migration tiếp theo

1. Tạo file mới, ví dụ `0002_add_topologies.sql`.
2. Viết SQL nâng cấp từ version `0001` lên `0002`.
3. Cập nhật `docker/postgres/init/01_schema.sql` để database tạo mới nhận schema
   cuối cùng ngay lập tức.
4. Không sửa `0001_initial_schema.sql` sau khi đã dùng ở môi trường chia sẻ.
5. Kiểm thử cả database trống và database đang ở version trước.
