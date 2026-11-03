#!/usr/bin/env python3
"""Safely reconcile migration tracking after Docker loaded the complete schema.

This deliberately does NOT replay historical CREATE/DROP/UPDATE SQL.
Run --check first; --apply records 0003-0006 only if all required
database objects, columns, indexes and constraints are already present.
"""

from __future__ import annotations

import argparse
import os
import sys

import psycopg

from scripts import migrate


def _present(conn: psycopg.Connection, name: str) -> bool:
    return conn.execute("SELECT to_regclass(%s) IS NOT NULL", (f"public.{name}",)).fetchone()[0]


def _columns(conn: psycopg.Connection, table: str) -> set[str]:
    rows = conn.execute(
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        """,
        (table,),
    ).fetchall()
    return {row[0] for row in rows}


def _required_columns(conn: psycopg.Connection, table: str, names: set[str], problems: list[str]) -> None:
    if not _present(conn, table):
        problems.append(f"Thiếu bảng {table}")
        return
    for name in sorted(names - _columns(conn, table)):
        problems.append(f"Thiếu cột {table}.{name}")


def _enum_labels(conn: psycopg.Connection, name: str) -> list[str]:
    return [
        row[0]
        for row in conn.execute(
            """
            SELECT e.enumlabel
            FROM pg_enum e
            JOIN pg_type t ON t.oid = e.enumtypid
            JOIN pg_namespace n ON n.oid = t.typnamespace
            WHERE n.nspname = 'public' AND t.typname = %s
            ORDER BY e.enumsortorder
            """,
            (name,),
        ).fetchall()
    ]


def _constraint(conn: psycopg.Connection, table: str, name: str) -> bool:
    return conn.execute(
        """
        SELECT EXISTS (
            SELECT 1 FROM pg_constraint c
            JOIN pg_class t ON t.oid = c.conrelid
            JOIN pg_namespace n ON n.oid = t.relnamespace
            WHERE n.nspname = 'public' AND t.relname = %s AND c.conname = %s
        )
        """,
        (table, name),
    ).fetchone()[0]


def verify_bootstrap(conn: psycopg.Connection) -> list[str]:
    """Check materialized effects of 0003-0006 (not only one sentinel type)."""
    problems: list[str] = []

    for name, labels in {
        "audit_actor_type": ["USER", "SYSTEM", "AGENT"],
        "audit_event_status": ["SUCCESS", "FAILED", "DENIED"],
    }.items():
        if _enum_labels(conn, name) != labels:
            problems.append(f"Enum {name} không khớp nội dung migration 0003")
    _required_columns(
        conn, "audit_logs",
        {"id", "actor_user_id", "actor_display_name", "actor_type", "action",
         "resource_type", "resource_id", "event_status", "summary", "event_data",
         "request_id", "source_ip", "user_agent", "occurred_at"},
        problems,
    )
    for name in (
        "idx_audit_logs_occurred_at", "idx_audit_logs_actor_time",
        "idx_audit_logs_resource_time", "idx_audit_logs_action_status_time",
        "idx_audit_logs_request_id",
    ):
        if not _present(conn, name):
            problems.append(f"Thiếu index {name} (0003)")
    for name in ("ck_audit_logs_actor", "ck_audit_logs_event_data_object"):
        if not _constraint(conn, "audit_logs", name):
            problems.append(f"Thiếu constraint audit_logs.{name} (0003)")

    _required_columns(
        conn, "benchmark_scenarios",
        {"id", "scenario_key", "version", "name", "description", "topology",
         "initial_message", "definition", "is_active", "created_by",
         "last_updated_by", "created_at", "last_updated_at"},
        problems,
    )
    _required_columns(
        conn, "benchmark_runs",
        {"id", "scenario_id", "scenario_version", "scenario_name", "scenario_snapshot",
         "status", "started_by", "initial_message", "conversation_id",
         "source_message_id", "task_id", "evaluation_id", "evaluation_result",
         "cleanup_required", "error_message", "started_at", "completed_at",
         "cleaned_at"},
        problems,
    )
    for name in (
        "idx_benchmark_scenarios_active_name", "idx_benchmark_runs_scenario_time",
        "idx_benchmark_runs_status_time",
    ):
        if not _present(conn, name):
            problems.append(f"Thiếu index {name} (0004)")
    for table, name in (
        ("benchmark_scenarios", "ck_benchmark_scenario_definition"),
        ("benchmark_scenarios", "ck_benchmark_scenario_time"),
        ("benchmark_runs", "ck_benchmark_run_time"),
    ):
        if not _constraint(conn, table, name):
            problems.append(f"Thiếu constraint {table}.{name} (0004)")

    metric_labels = _enum_labels(conn, "evaluation_metric_type")
    if metric_labels[:4] != ["GOAL", "RCA", "REMEDIATION", "SAFETY"]:
        problems.append("Enum evaluation_metric_type thiếu 4 giá trị cơ sở (0005)")
    _required_columns(
        conn, "task_evaluation_metrics",
        {"id", "evaluation_id", "metric_type", "result", "is_required",
         "was_attempted", "expected_value", "actual_value", "evidence",
         "created_at"},
        problems,
    )
    for name in (
        "idx_task_evaluation_metrics_type_result",
        "idx_task_evaluation_metrics_evaluation",
    ):
        if not _present(conn, name):
            problems.append(f"Thiếu index {name} (0005)")
    for name in (
        "uq_task_evaluation_metric_type", "ck_task_evaluation_metric_attempted",
    ):
        if not _constraint(conn, "task_evaluation_metrics", name):
            problems.append(f"Thiếu constraint task_evaluation_metrics.{name} (0005)")
    legacy = {
        "expected_outcome", "actual_outcome", "goal_result", "expected_root_cause",
        "predicted_root_cause", "rca_result", "remediation_required",
        "remediation_attempted", "remediation_result", "safety_result",
        "evaluation_evidence",
    }
    remaining = legacy & _columns(conn, "task_evaluations")
    if remaining:
        problems.append(f"Các cột cũ của 0005 vẫn tồn tại: {sorted(remaining)}")

    if not conn.execute(
        """
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'benchmark_scenarios'
              AND column_name = 'scenario_key' AND is_nullable = 'NO'
        )
        """
    ).fetchone()[0]:
        problems.append("benchmark_scenarios.scenario_key chưa NOT NULL (0006)")
    if not (
        _constraint(conn, "benchmark_scenarios", "uq_benchmark_scenarios_scenario_key")
        or _constraint(conn, "benchmark_scenarios", "benchmark_scenarios_scenario_key_key")
    ):
        problems.append("Thiếu UNIQUE constraint của scenario_key (0006)")
    for table, name in (
        ("benchmark_scenarios", "ck_benchmark_scenario_id_format"),
        ("benchmark_scenarios", "ck_benchmark_scenario_key_format"),
        ("benchmark_runs", "ck_benchmark_run_id_format"),
        ("benchmark_runs", "benchmark_runs_scenario_id_fkey"),
    ):
        if not _constraint(conn, table, name):
            problems.append(f"Thiếu constraint {table}.{name} (0006)")

    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    flags = parser.add_mutually_exclusive_group(required=True)
    flags.add_argument("--check", action="store_true", help="Chỉ kiểm tra, không ghi DB")
    flags.add_argument("--apply", action="store_true", help="Ghi lại lịch sử sau khi kiểm chứng")
    args = parser.parse_args()
    url = os.getenv("DATABASE_URL")
    if not url:
        print("Thiếu DATABASE_URL", file=sys.stderr)
        return 2

    try:
        migrations = {item.version: item for item in migrate.load_migrations()}
        with psycopg.connect(url, autocommit=True) as conn:
            conn.execute("SELECT pg_advisory_lock(hashtext(%s))", (migrate.LOCK_NAME,))
            try:
                if not migrate.migration_table_exists(conn):
                    raise RuntimeError("Chưa có schema_migrations; không thể reconcile an toàn")
                applied = migrate.applied_migrations(conn)
                migrate.verify_checksums(list(migrations.values()), applied)
                if not {"0001", "0002"}.issubset(applied):
                    raise RuntimeError("Cần xác minh và hoàn tất migration 0001, 0002 trước")
                problems = verify_bootstrap(conn)
                if problems:
                    print("Từ chối đồng bộ: schema chưa khớp toàn bộ 0003-0006.")
                    for issue in problems:
                        print(f" - {issue}")
                    return 1

                pending = [
                    migrations[v] for v in ("0003", "0004", "0005", "0006")
                    if v not in applied
                ]
                if args.check:
                    print("Schema 0003-0006 đủ các kiểm tra. Chưa thay đổi database.")
                    print("Có thể đồng bộ:", ", ".join(x.version for x in pending) or "không có")
                else:
                    with conn.transaction():
                        # Read-only checks were performed while holding the shared
                        # advisory lock. This transaction writes tracking rows only.
                        for migration in pending:
                            migrate.record_migration(conn, migration, 0)
                    print("Đã đồng bộ lịch sử:", ", ".join(x.version for x in pending) or "không có")
                print("0007: dùng 'python scripts/migrate.py' để áp dụng/ghi nhận sau.")
            finally:
                conn.execute("SELECT pg_advisory_unlock(hashtext(%s))", (migrate.LOCK_NAME,))
    except (psycopg.Error, RuntimeError, OSError) as error:
        print(f"Reconcile thất bại: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
