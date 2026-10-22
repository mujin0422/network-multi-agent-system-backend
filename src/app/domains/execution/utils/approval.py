"""Canonical hashing for immutable operation-device approval snapshots."""

import hashlib
import json


def build_approval_request_hash(
    operation_device_id: str,
    commands: list[str],
) -> str:
    """Hash mapping ID and ordered commands using canonical UTF-8 JSON."""

    canonical_payload = json.dumps(
        {
            "commands": commands,
            "operation_device_id": operation_device_id,
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical_payload.encode()).hexdigest()
