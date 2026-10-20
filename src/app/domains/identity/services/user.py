"""Use cases quản lý tài khoản người dùng."""

from datetime import UTC, datetime

from app.core.exceptions import ResourceConflictError, ResourceNotFoundError
from app.core.utils import IdPrefix, generate_id
from app.domains.identity.repositories import IdentityRepositoryProtocol
from app.domains.identity.schemas import User, UserCreate, UserRecord, UserUpdate
from app.domains.identity.utils import hash_password


class UserService:
    """Tạo và cập nhật user, không để lộ password hash qua API."""

    def __init__(self, repository: IdentityRepositoryProtocol) -> None:
        self._repository = repository

    def create_user(self, payload: UserCreate) -> User:
        self._ensure_role_exists(payload.role_id)
        self._ensure_unique_email(payload.email)
        record = UserRecord(
            id=generate_id(IdPrefix.USER),
            role_id=payload.role_id,
            email=payload.email,
            password_hash=hash_password(payload.password),
            full_name=payload.full_name,
            user_status=payload.user_status,
            created_at=datetime.now(UTC),
            last_updated_at=None,
            last_login_at=None,
        )
        self._repository.save_user(record)
        return User.model_validate(record.model_dump())

    def list_users(self) -> list[User]:
        """Lấy danh sách user công khai, không bao gồm password hash."""

        return self._repository.list_users()

    def get_user(self, user_id: str) -> User:
        """Lấy user theo ID hoặc phát sinh lỗi nếu không tồn tại."""

        user = self._repository.get_user(user_id)
        if user is None:
            raise ResourceNotFoundError(f"Không tìm thấy user '{user_id}'")
        return user

    def update_user(self, user_id: str, payload: UserUpdate) -> User:
        current = self._repository.get_user_with_password(user_id)
        if current is None:
            raise ResourceNotFoundError(f"Không tìm thấy user '{user_id}'")

        changes = payload.model_dump(
            exclude_unset=True,
            exclude_none=True,
            exclude={"password"},
        )
        if "role_id" in changes:
            self._ensure_role_exists(changes["role_id"])
        if "email" in changes:
            self._ensure_unique_email(changes["email"], exclude_user_id=user_id)
        if payload.password is not None:
            changes["password_hash"] = hash_password(payload.password)
        changes["last_updated_at"] = datetime.now(UTC)

        updated = current.model_copy(update=changes)
        self._repository.save_user(updated)
        return User.model_validate(updated.model_dump())

    def _ensure_role_exists(self, role_id: str) -> None:
        if self._repository.get_role(role_id) is None:
            raise ResourceNotFoundError(f"Không tìm thấy role '{role_id}'")

    def _ensure_unique_email(
        self,
        email: str,
        exclude_user_id: str | None = None,
    ) -> None:
        existing = self._repository.get_user_by_email(email)
        if existing is not None and existing.id != exclude_user_id:
            raise ResourceConflictError(f"Email '{email}' đã được sử dụng")
