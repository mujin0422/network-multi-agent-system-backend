"""Đối chiếu Pydantic schema với 20 bảng trong tài liệu database."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import BaseModel

from app.domains.conversation.schemas import Conversation, Message
from app.domains.evaluation.schemas import TaskEvaluation
from app.domains.execution.schemas import (
    DeviceActionLog,
    Operation,
    OperationDependency,
    Task,
    TaskExecution,
    TaskOperationDevice,
)
from app.domains.identity.schemas import (
    Action,
    ManagementFunction,
    Permission,
    Role,
    RolePermission,
    UserRecord,
    UserSessionRecord,
)
from app.domains.inventory.schemas import (
    Brand,
    Category,
    CredentialRecord,
    Device,
)


SCHEMA_FIELDS: list[tuple[type[BaseModel], set[str]]] = [
    (
        Role,
        {
            "id",
            "name",
            "description",
            "created_by",
            "last_updated_by",
            "created_at",
            "last_updated_at",
        },
    ),
    (ManagementFunction, {"id", "name", "description"}),
    (Action, {"id", "name", "description"}),
    (Permission, {"id", "function_id", "action_id"}),
    (RolePermission, {"role_id", "permission_id"}),
    (
        UserRecord,
        {
            "id",
            "role_id",
            "email",
            "password_hash",
            "full_name",
            "user_status",
            "created_at",
            "last_updated_at",
            "last_login_at",
        },
    ),
    (
        UserSessionRecord,
        {
            "id",
            "user_id",
            "refresh_token_hash",
            "expires_at",
            "created_at",
            "revoked_at",
        },
    ),
    (Brand, {"id", "name", "supported_drivers"}),
    (Category, {"id", "name"}),
    (
        CredentialRecord,
        {
            "id",
            "name",
            "description",
            "username",
            "password",
            "secret",
            "encryption_type",
            "created_by",
            "last_updated_by",
            "created_at",
            "last_updated_at",
        },
    ),
    (
        Device,
        {
            "id",
            "credential_id",
            "brand_id",
            "category_id",
            "created_by",
            "last_updated_by",
            "hostname",
            "host",
            "port",
            "device_type",
            "location",
            "created_at",
            "last_updated_at",
        },
    ),
    (
        Conversation,
        {"id", "user_id", "title", "created_at", "last_updated_at"},
    ),
    (Message, {"id", "conversation_id", "sender_by", "message", "created_at"}),
    (
        Task,
        {
            "id",
            "conversation_id",
            "source_message_id",
            "user_id",
            "input_message",
            "task_status",
            "task_type",
            "started_at",
            "completed_at",
            "created_at",
        },
    ),
    (
        Operation,
        {
            "id",
            "task_id",
            "operation_intent",
            "display_order",
            "operation_status",
            "operation_parameters",
            "created_at",
            "started_at",
            "completed_at",
        },
    ),
    (
        OperationDependency,
        {
            "id",
            "operation_id",
            "depends_on_operation_id",
            "dependency_type",
            "created_at",
        },
    ),
    (
        TaskOperationDevice,
        {
            "id",
            "operation_id",
            "device_id",
            "operation_device_status",
            "device_role",
            "access_mode",
            "error_message",
            "started_at",
            "completed_at",
        },
    ),
    (
        TaskExecution,
        {
            "id",
            "task_id",
            "operation_id",
            "operation_device_id",
            "agent_name",
            "tool_name",
            "step_order",
            "input",
            "output",
            "execution_status",
            "error_message",
            "started_at",
            "completed_at",
            "duration_ms",
            "created_at",
        },
    ),
    (
        DeviceActionLog,
        {
            "id",
            "task_id",
            "operation_id",
            "operation_device_id",
            "execution_id",
            "device_id",
            "rollback_of_action_id",
            "action_type",
            "action_phase",
            "sequence_number",
            "command",
            "result",
            "action_log_status",
            "error_message",
            "executed_at",
        },
    ),
    (
        TaskEvaluation,
        {
            "id",
            "task_id",
            "evaluation_status",
            "expected_outcome",
            "actual_outcome",
            "goal_result",
            "expected_root_cause",
            "predicted_root_cause",
            "rca_result",
            "remediation_required",
            "remediation_attempted",
            "remediation_result",
            "safety_result",
            "evaluation_evidence",
            "evaluator_type",
            "evaluator_version",
            "created_at",
            "evaluated_at",
        },
    ),
]


@pytest.mark.parametrize(("schema", "expected_fields"), SCHEMA_FIELDS)
def test_schema_fields_match_database_table(
    schema: type[BaseModel],
    expected_fields: set[str],
) -> None:
    """Tên trường phải khớp bảng và mọi trường đều có chú thích OpenAPI."""

    assert set(schema.model_fields) == expected_fields
    assert all(field.description for field in schema.model_fields.values())


def test_internal_secrets_are_excluded_from_serialization() -> None:
    """Record nội bộ nhận secret nhưng không vô tình trả chúng qua API/log."""

    now = datetime.now(UTC)
    user = UserRecord(
        id="user-test",
        role_id="role-admin",
        email="admin@example.com",
        password_hash="bcrypt-hash",
        full_name="Administrator",
        user_status="ACTIVE",
        created_at=now,
    )
    session = UserSessionRecord(
        id=uuid4(),
        user_id=user.id,
        refresh_token_hash="refresh-token-hash",
        expires_at=now + timedelta(days=1),
        created_at=now,
    )
    credential = CredentialRecord(
        id="cred-lab",
        name="Lab credential",
        username="netops",
        password="encrypted-password",
        secret="encrypted-secret",
        encryption_type="PGP_SYM_AES256",
        created_by=user.id,
        created_at=now,
        last_updated_at=now,
    )

    assert "password_hash" not in user.model_dump()
    assert "refresh_token_hash" not in session.model_dump()
    assert "password" not in credential.model_dump()
    assert "secret" not in credential.model_dump()
