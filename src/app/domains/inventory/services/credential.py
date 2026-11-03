"""Use cases cho resource Credential."""

from datetime import UTC, datetime

from app.domains.audit.transaction import audit_mutation, record_audit_in_session
from app.core.database import DatabaseUnitOfWork

from app.core.exceptions import ResourceNotFoundError
from app.core.utils import IdPrefix, generate_id
from app.domains.inventory.repositories import CredentialRepository
from app.domains.inventory.schemas import Credential, CredentialCreate, CredentialUpdate
from app.domains.inventory.utils import ensure_unique_name


class CredentialService:
    """Quản lý Credential mà không trả password hoặc secret ra ngoài."""

    def __init__(
        self, repository: CredentialRepository, uow: DatabaseUnitOfWork | None = None
    ) -> None:
        self._repository = repository
        self._uow = uow

    # =============================================================================
    # Credential — tạo, lấy và cập nhật thông tin đăng nhập
    # =============================================================================

    def create_credential(
        self,
        payload: CredentialCreate,
        actor_user_id: str,
    ) -> Credential:
        """Tạo metadata và chuyển secret cho repository mã hóa."""

        ensure_unique_name(
            self._repository.get_all(),
            payload.name,
            resource_label="credential",
        )
        now = datetime.now(UTC)
        credential = Credential(
            id=generate_id(IdPrefix.CREDENTIAL),
            name=payload.name,
            description=payload.description,
            username=payload.username,
            encryption_type=payload.encryption_type,
            created_by=actor_user_id,
            last_updated_by=actor_user_id,
            created_at=now,
            last_updated_at=now,
        )
        if self._uow is None:
            with audit_mutation(
                "CREDENTIAL_CREATE", "CREDENTIAL", credential.id,
                actor_user_id=actor_user_id,
            ):
                self._repository.create(
                    credential, password=payload.password, secret=payload.secret,
                )
        else:
            with self._uow.begin() as session:
                self._repository.create_in_session(
                    session, credential,
                    password=payload.password, secret=payload.secret,
                )
                record_audit_in_session(
                    session, action="CREDENTIAL_CREATE",
                    resource_type="CREDENTIAL", resource_id=credential.id,
                    actor_user_id=actor_user_id,
                )
        return credential

    def list_credentials(self) -> list[Credential]:
        """Lấy danh sách metadata Credential."""

        return self._repository.get_all()

    def get_credential(self, credential_id: str) -> Credential:
        """Lấy metadata Credential hoặc phát sinh lỗi HTTP 404."""

        credential = self._repository.get_by_id(credential_id)
        if credential is None:
            raise ResourceNotFoundError(
                f"Không tìm thấy credential '{credential_id}'"
            )
        return credential

    def update_credential(
        self,
        credential_id: str,
        payload: CredentialUpdate,
        actor_user_id: str,
    ) -> Credential:
        """Cập nhật metadata và các secret được gửi rõ ràng trong request."""

        current = self.get_credential(credential_id)
        fields_set = payload.model_fields_set
        changes = {"last_updated_by": actor_user_id}
        if "name" in fields_set and payload.name is not None:
            changes["name"] = payload.name
        if "description" in fields_set:
            changes["description"] = payload.description
        if "username" in fields_set and payload.username is not None:
            changes["username"] = payload.username
        if "encryption_type" in fields_set and payload.encryption_type is not None:
            changes["encryption_type"] = payload.encryption_type
        candidate = current.model_copy(
            update={**changes, "last_updated_at": datetime.now(UTC)}
        )
        ensure_unique_name(
            self._repository.get_all(),
            candidate.name,
            resource_label="credential",
            exclude_id=credential_id,
        )
        update_password = "password" in fields_set and payload.password is not None
        update_secret = "secret" in fields_set
        if self._uow is None:
            with audit_mutation(
                "CREDENTIAL_UPDATE", "CREDENTIAL", candidate.id,
                actor_user_id=actor_user_id,
            ):
                self._repository.update(
                    candidate, password=payload.password, secret=payload.secret,
                    update_password=update_password, update_secret=update_secret,
                )
        else:
            with self._uow.begin() as session:
                self._repository.update_in_session(
                    session, candidate,
                    password=payload.password, secret=payload.secret,
                    update_password=update_password, update_secret=update_secret,
                )
                record_audit_in_session(
                    session, action="CREDENTIAL_UPDATE",
                    resource_type="CREDENTIAL", resource_id=candidate.id,
                    actor_user_id=actor_user_id,
                )
        return candidate

    # =============================================================================
    # Xác minh tên Credential
    # =============================================================================

    def _ensure_unique_name(
        self,
        name: str,
        exclude_credential_id: str | None = None,
    ) -> None:
        """Không cho phép tên Credential trùng nhau, không phân biệt hoa thường."""

        for credential in self._repository.get_all():
            if credential.id == exclude_credential_id:
                continue
            if credential.name.casefold() == name.casefold():
                raise ResourceConflictError(
                    f"Tên credential '{name}' đã được sử dụng"
                )
