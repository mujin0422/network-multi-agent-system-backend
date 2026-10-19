"""Use cases quản lý vai trò."""

from datetime import UTC, datetime

from app.core.exceptions import ResourceConflictError, ResourceNotFoundError
from app.core.utils import generate_id
from app.domains.identity.repositories import IdentityRepository
from app.domains.identity.schemas import Role, RoleCreate, RoleUpdate


class RoleService:
    """Tạo và cập nhật role cùng thông tin audit."""

    def __init__(self, repository: IdentityRepository) -> None:
        self._repository = repository

    def create_role(self, payload: RoleCreate, actor_id: str) -> Role:
        self._ensure_unique_name(payload.name)
        now = datetime.now(UTC)
        role = Role(
            id=generate_id("role"),
            **payload.model_dump(),
            created_by=actor_id,
            last_updated_by=actor_id,
            created_at=now,
            last_updated_at=now,
        )
        self._repository.save_role(role)
        return role

    def update_role(
        self,
        role_id: str,
        payload: RoleUpdate,
        actor_id: str,
    ) -> Role:
        current = self._repository.get_role(role_id)
        if current is None:
            raise ResourceNotFoundError(f"Không tìm thấy role '{role_id}'")

        changes = payload.model_dump(exclude_unset=True, exclude_none=True)
        if "name" in changes:
            self._ensure_unique_name(changes["name"], exclude_role_id=role_id)
        if "description" in payload.model_fields_set:
            changes["description"] = payload.description
        changes.update(
            last_updated_by=actor_id,
            last_updated_at=datetime.now(UTC),
        )
        updated = current.model_copy(update=changes)
        self._repository.save_role(updated)
        return updated

    def _ensure_unique_name(
        self,
        name: str,
        exclude_role_id: str | None = None,
    ) -> None:
        existing = self._repository.get_role_by_name(name)
        if existing is not None and existing.id != exclude_role_id:
            raise ResourceConflictError(f"Tên role '{name}' đã được sử dụng")
