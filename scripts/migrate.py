#!/usr/bin/env python3
"""Apply ordered PostgreSQL SQL migrations with checksums and advisory locking."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import psycopg


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = PROJECT_ROOT / "migrations" / "versions"
SCHEMA_SNAPSHOT = PROJECT_ROOT / "docker" / "postgres" / "init" / "01_schema.sql"
INITIAL_VERSION = "0001"
LOCK_NAME = "network_multi_agent_schema_migrations"
CANONICAL_SCHEMA_DIRECTIVE = "-- @canonical-schema"
VERSION_PATTERN = re.compile(r"^(?P<version>\d{4})_(?P<name>[a-z0-9_]+)\.sql$")


@dataclass(frozen=True)
class Migration:
    version: str
    name: str
    path: Path
    sql: str
    checksum: str


def load_migrations() -> list[Migration]:
    migrations: list[Migration] = []
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        match = VERSION_PATTERN.match(path.name)
        if not match:
            raise RuntimeError(f"Tên migration không hợp lệ: {path.name}")
        sql = path.read_text(encoding="utf-8")
        migrations.append(
            Migration(
                version=match.group("version"),
                name=match.group("name"),
                path=path,
                sql=sql,
                checksum=hashlib.sha256(sql.encode()).hexdigest(),
            )
        )
    versions = [migration.version for migration in migrations]
    if not migrations:
        raise RuntimeError("Không tìm thấy migration")
    if versions != sorted(set(versions)):
        raise RuntimeError("Migration version phải duy nhất và tăng dần")
    if versions[0] != INITIAL_VERSION:
        raise RuntimeError(f"Migration đầu tiên phải là {INITIAL_VERSION}")
    return migrations


def canonical_schema_sql() -> str:
    """Remove psql-only and transaction wrapper lines from the canonical DDL."""
    lines = SCHEMA_SNAPSHOT.read_text(encoding="utf-8").splitlines()
    return "\n".join(
        line
        for line in lines
        if not line.lstrip().startswith("\\")
        and line.strip().upper() not in {"BEGIN;", "COMMIT;"}
    )


def executable_sql(migration: Migration) -> str:
    if migration.sql.lstrip().startswith(CANONICAL_SCHEMA_DIRECTIVE):
        if migration.version != INITIAL_VERSION:
            raise RuntimeError("Chỉ migration 0001 được dùng canonical schema")
        return canonical_schema_sql()
    return migration.sql


def migration_table_exists(connection: psycopg.Connection) -> bool:
    row = connection.execute(
        "SELECT to_regclass('public.schema_migrations') IS NOT NULL"
    ).fetchone()
    return bool(row[0])


def applied_migrations(connection: psycopg.Connection) -> dict[str, str]:
    if not migration_table_exists(connection):
        return {}
    rows = connection.execute(
        "SELECT version, checksum FROM schema_migrations ORDER BY version"
    ).fetchall()
    return {version: checksum for version, checksum in rows}


def user_tables(connection: psycopg.Connection) -> set[str]:
    rows = connection.execute(
        """
        SELECT tablename
          FROM pg_tables
         WHERE schemaname = 'public'
           AND tablename <> 'schema_migrations'
        """
    ).fetchall()
    return {row[0] for row in rows}


def column_exists(
    connection: psycopg.Connection,
    table_name: str,
    column_name: str,
) -> bool:
    row = connection.execute(
        """
        SELECT EXISTS (
            SELECT 1
              FROM information_schema.columns
             WHERE table_schema = 'public'
               AND table_name = %s
               AND column_name = %s
        )
        """,
        (table_name, column_name),
    ).fetchone()
    return bool(row[0])


def is_initial_schema(connection: psycopg.Connection) -> bool:
    required_tables = {
        "users",
        "devices",
        "conversations",
        "messages",
        "tasks",
        "task_operations",
        "task_activity_events",
        "operation_device_approvals",
        "task_evaluations",
    }
    tables = user_tables(connection)
    return required_tables.issubset(tables) and all(
        (
            column_exists(connection, "users", "user_status"),
            column_exists(connection, "tasks", "task_status"),
            column_exists(connection, "tasks", "task_type"),
            column_exists(connection, "task_operations", "operation_intent"),
            column_exists(connection, "messages", "message_type"),
            column_exists(connection, "messages", "reply_to_message_id"),
            column_exists(
                connection,
                "operation_device_approvals",
                "operation_device_id",
            ),
            column_exists(
                connection,
                "task_executions",
                "execution_status",
            ),
        )
    )


def create_tracking_table(connection: psycopg.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version VARCHAR(16) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            checksum CHAR(64) NOT NULL,
            execution_ms BIGINT NOT NULL CHECK (execution_ms >= 0),
            applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def record_migration(
    connection: psycopg.Connection,
    migration: Migration,
    execution_ms: int,
) -> None:
    connection.execute(
        """
        INSERT INTO schema_migrations (version, name, checksum, execution_ms)
        VALUES (%s, %s, %s, %s)
        """,
        (migration.version, migration.name, migration.checksum, execution_ms),
    )


def verify_checksums(
    migrations: list[Migration],
    applied: dict[str, str],
) -> None:
    known = {migration.version: migration for migration in migrations}
    unknown = sorted(set(applied) - set(known))
    if unknown:
        raise RuntimeError(f"Database có migration không tồn tại trong code: {unknown}")
    for version, checksum in applied.items():
        if known[version].checksum != checksum:
            raise RuntimeError(
                f"Checksum migration {version} đã thay đổi; không được sửa migration đã chạy"
            )


def baseline_initialized_database(
    connection: psycopg.Connection,
    initial_migration: Migration,
) -> None:
    """Register Docker-initialized schema without replaying CREATE statements."""
    if not is_initial_schema(connection):
        raise RuntimeError(
            "Database không trống và không khớp initial schema; từ chối tự động sửa."
        )
    create_tracking_table(connection)
    record_migration(connection, initial_migration, 0)
    print(f"Đã nhận diện initial schema và ghi version {INITIAL_VERSION}")


def print_status(
    connection: psycopg.Connection,
    migrations: list[Migration],
) -> None:
    applied = applied_migrations(connection)
    if not user_tables(connection):
        schema_state = "empty"
    elif is_initial_schema(connection):
        schema_state = "initial"
    else:
        schema_state = "unknown"
    print(f"Schema: {schema_state}")
    for migration in migrations:
        state = "APPLIED" if migration.version in applied else "PENDING"
        print(f"{migration.version}  {state:7}  {migration.name}")


def migrate(database_url: str) -> None:
    migrations = load_migrations()
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute("SELECT pg_advisory_lock(hashtext(%s))", (LOCK_NAME,))
        try:
            if not migration_table_exists(connection) and user_tables(connection):
                with connection.transaction():
                    baseline_initialized_database(connection, migrations[0])

            if not migration_table_exists(connection):
                with connection.transaction():
                    create_tracking_table(connection)

            applied = applied_migrations(connection)
            verify_checksums(migrations, applied)

            for migration in migrations:
                if migration.version in applied:
                    continue
                print(f"Áp dụng {migration.version}_{migration.name} ...")
                started = time.monotonic()
                with connection.transaction():
                    connection.execute(executable_sql(migration), prepare=False)
                    execution_ms = int((time.monotonic() - started) * 1000)
                    record_migration(connection, migration, execution_ms)
                print(f"Hoàn tất {migration.version} ({execution_ms} ms)")

            verify_checksums(migrations, applied_migrations(connection))
            print("Database schema đã ở version mới nhất.")
        finally:
            connection.execute("SELECT pg_advisory_unlock(hashtext(%s))", (LOCK_NAME,))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL"),
        help="PostgreSQL URL; mặc định lấy từ DATABASE_URL.",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Chỉ hiển thị trạng thái, không thay đổi database.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Alias của --status.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.database_url:
        print("Thiếu DATABASE_URL hoặc --database-url", file=sys.stderr)
        return 2
    try:
        migrations = load_migrations()
        if args.status or args.dry_run:
            with psycopg.connect(args.database_url) as connection:
                print_status(connection, migrations)
        else:
            migrate(args.database_url)
    except (psycopg.Error, RuntimeError, OSError) as error:
        print(f"Migration thất bại: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
