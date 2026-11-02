"""Repository tạo cấu hình kết nối thiết bị."""

from sqlalchemy import case, func, or_, select

from app.core.database import create_session_factory
from app.domains.inventory.models import CredentialModel, DeviceModel
from app.domains.inventory.schemas import DeviceConfig


class DeviceConfigRepository:
    """Read device metadata and decrypted credentials from PostgreSQL.

    Password and enable secret are only materialized for the Netmiko connection
    flow. They are never returned by the public Inventory API.
    """

    def __init__(self, database_url: str, encryption_key: str) -> None:
        """Khởi tạo DeviceConfigRepository cùng các phụ thuộc cần thiết."""
        self._sessions = create_session_factory(database_url)
        self._encryption_key = encryption_key

    def get_by_identifier(self, device_identifier: str) -> DeviceConfig | None:
        # Cho phép agent gọi bằng cả primary key (devc-...) và hostname (P1).
        # Credential chỉ được giải mã trong luồng kết nối và không được ghi log.
        """Truy vấn dữ liệu theo phạm vi của phương thức get_by_identifier."""
        statement = (
            select(
                DeviceModel.hostname.label("gns3_node_name"),
                DeviceModel.device_type,
                DeviceModel.host.label("hostname"),
                DeviceModel.port,
                CredentialModel.username,
                func.pgp_sym_decrypt(
                    func.dearmor(CredentialModel.password),
                    self._encryption_key,
                ).label("password"),
                case(
                    (CredentialModel.secret.is_(None), ""),
                    else_=func.pgp_sym_decrypt(
                        func.dearmor(CredentialModel.secret),
                        self._encryption_key,
                    ),
                ).label("secret"),
            )
            .join(CredentialModel, CredentialModel.id == DeviceModel.credential_id)
            .where(
                or_(
                    DeviceModel.id == device_identifier,
                    func.lower(DeviceModel.hostname) == device_identifier.lower(),
                )
            )
            .limit(1)
        )
        with self._sessions() as session:
            row = session.execute(statement).mappings().one_or_none()
            return DeviceConfig.model_validate(row) if row else None
