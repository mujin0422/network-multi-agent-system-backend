"""Kiểm tra quy ước ID dùng chung với database design."""

import re
from datetime import UTC, datetime
from uuid import UUID

from app.core.utils import IdPrefix, generate_id, generate_uuid


def test_generate_business_id_uses_documented_prefix_and_utc_date() -> None:
    identifier = generate_id(IdPrefix.USER)
    date_part = datetime.now(UTC).strftime("%d%m%y")

    assert re.fullmatch(rf"user-{date_part}-[0-9a-f]{{8}}", identifier)
    assert len(identifier) <= 64


def test_all_business_id_prefixes_fit_database_column() -> None:
    for prefix in IdPrefix:
        identifier = generate_id(prefix)

        assert identifier.startswith(f"{prefix.value}-")
        assert len(identifier) <= 64


def test_generate_uuid_returns_uuid_for_uuid_backed_tables() -> None:
    assert isinstance(generate_uuid(), UUID)
