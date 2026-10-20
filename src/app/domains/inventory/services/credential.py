"""Use cases cho resource Credential."""

from datetime import UTC, datetime

from app.core.exceptions import ResourceConflictError, ResourceNotFoundError
from app.core.utils import IdPrefix, generate_id
from app.domains.inventory.repositories import CredentialRepositoryProtocol
from app.domains.inventory.schemas import Credential, CredentialCreate, CredentialUpdate


class CredentialService:
    """Quản lý Credential mà không trả password hoặc secret ra ngoài."""

    def __init__(self, repository: CredentialRepositoryProtocol) -> None:
        self._repository = repository

    def create_credential(self, payload: CredentialCreate) -> Credential:
        """Tạo metadata và chuyển secret cho repository mã hóa."""

        self._ensure_unique_name(payload.name)
        now = datetime.now(UTC)
        credential = Credential(
            id=generate_id(IdPrefix.CREDENTIAL),
            name=payload.name,
            description=payload.description,
            username=payload.username,
            encryption_type=payload.encryption_type,
            created_by=payload.created_by,
            last_updated_by=payload.created_by,
            created_at=now,
            last_updated_at=now,
        )
        self._repository.create(credential, payload.password, payload.secret)
        return credential

    def list_credentials(self) -> list[Credential]:
        """Lấy danh sách metadata Credential."""

        return self._repository.list()

    def get_credential(self, credential_id: str) -> Credential:
        """Lấy metadata Credential hoặc phát sinh lỗi HTTP 404."""

        credential = self._repository.get(credential_id)
        if credential is None:
            raise ResourceNotFoundError(
                f"Không tìm thấy credential '{credential_id}'"
            )
        return credential

    def update_credential(
        self,
        credential_id: str,
        payload: CredentialUpdate,
    ) -> Credential:
        """Cập nhật metadata và các secret được gửi rõ ràng trong request."""

        current = self.get_credential(credential_id)
        fields_set = payload.model_fields_set
        changes = {"last_updated_by": payload.last_updated_by}
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
        self._ensure_unique_name(candidate.name, exclude_credential_id=credential_id)
        self._repository.update(
            candidate,
            password=payload.password,
            secret=payload.secret,
            update_password="password" in fields_set and payload.password is not None,
            update_secret="secret" in fields_set,
        )
        return candidate

    def _ensure_unique_name(
        self,
        name: str,
        exclude_credential_id: str | None = None,
    ) -> None:
        """Không cho phép tên Credential trùng nhau, không phân biệt hoa thường."""

        for credential in self._repository.list():
            if credential.id == exclude_credential_id:
                continue
            if credential.name.casefold() == name.casefold():
                raise ResourceConflictError(
                    f"Tên credential '{name}' đã được sử dụng"
                )
