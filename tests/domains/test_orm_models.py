"""Ensure ORM metadata covers the canonical 20-table database design."""

from app.core.database import Base
from app.domains.conversation.models import ConversationModel, MessageModel
from app.domains.evaluation.models import TaskEvaluationModel
from app.domains.execution.models import (
    DeviceActionLogModel,
    OperationDependencyModel,
    OperationModel,
    TaskExecutionModel,
    TaskModel,
    TaskOperationDeviceModel,
)
from app.domains.identity.models import (
    ActionModel,
    ManagementFunctionModel,
    PermissionModel,
    RoleModel,
    RolePermissionModel,
    UserModel,
    UserSessionModel,
)
from app.domains.inventory.models import (
    BrandModel,
    CategoryModel,
    CredentialModel,
    DeviceModel,
)
from tests.domains.test_database_schemas import SCHEMA_FIELDS


ORM_MODELS = [
    RoleModel,
    ManagementFunctionModel,
    ActionModel,
    PermissionModel,
    RolePermissionModel,
    UserModel,
    UserSessionModel,
    BrandModel,
    CategoryModel,
    CredentialModel,
    DeviceModel,
    ConversationModel,
    MessageModel,
    TaskModel,
    OperationModel,
    OperationDependencyModel,
    TaskOperationDeviceModel,
    TaskExecutionModel,
    DeviceActionLogModel,
    TaskEvaluationModel,
]


def test_orm_covers_all_domain_tables() -> None:
    expected_tables = {
        "roles",
        "management_functions",
        "actions",
        "permissions",
        "role_permissions",
        "users",
        "user_sessions",
        "brands",
        "categories",
        "credentials",
        "devices",
        "conversations",
        "messages",
        "tasks",
        "task_operations",
        "operation_dependencies",
        "task_operation_devices",
        "task_executions",
        "device_action_logs",
        "task_evaluations",
    }

    assert {model.__tablename__ for model in ORM_MODELS} == expected_tables
    assert expected_tables <= set(Base.metadata.tables)


def test_orm_columns_match_database_record_schemas() -> None:
    for model, (_, expected_fields) in zip(ORM_MODELS, SCHEMA_FIELDS, strict=True):
        assert set(model.__table__.columns.keys()) == expected_fields
