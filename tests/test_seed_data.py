"""Regression checks cho development seed, không cần PostgreSQL đang chạy."""

import re
from pathlib import Path


SEED_PATH = Path("docker/postgres/init/02_seed.sql.template")


def test_seed_uses_database_design_id_formats() -> None:
    seed = SEED_PATH.read_text(encoding="utf-8")
    patterns = {
        "role": r"role-\d{6}-\d{8}",
        "user": r"user-\d{6}-\d{8}",
        "func": r"func-\d{8}",
        "acts": r"acts-\d{8}",
        "perm": r"perm-\d{8}",
        "brnd": r"brnd-\d{6}-\d{4}",
        "catg": r"catg-\d{6}-\d{8}",
        "cred": r"cred-\d{6}-\d{8}",
        "devc": r"devc-\d{6}-\d{8}",
    }

    for prefix, pattern in patterns.items():
        identifiers = set(re.findall(rf"'{prefix}-[^']+'", seed))
        assert identifiers
        assert all(re.fullmatch(rf"'{pattern}'", value) for value in identifiers)


def test_seed_contains_one_admin_and_no_runtime_group_data() -> None:
    seed = SEED_PATH.read_text(encoding="utf-8")

    assert seed.count("crypt('Admin@123'") == 1
    assert seed.count("phamdinhduythai@gmail.com") == 1
    assert "host.docker.internal" in seed
    assert "'Execute'" not in seed

    runtime_tables = (
        "conversations",
        "messages",
        "tasks",
        "task_operations",
        "operation_dependencies",
        "task_operation_devices",
        "task_executions",
        "device_action_logs",
        "task_activity_events",
        "operation_device_approvals",
        "task_evaluations",
    )
    for table in runtime_tables:
        assert not re.search(rf"INSERT\s+INTO\s+{table}\b", seed, re.IGNORECASE)
