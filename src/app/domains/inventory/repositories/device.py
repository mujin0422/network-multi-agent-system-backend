"""Persistence contract và PostgreSQL adapter cho resource Device."""

from typing import Protocol

from sqlalchemy import func, select

from app.core.database import create_session_factory
from app.domains.inventory.models import DeviceModel
from app.domains.inventory.schemas import Device


class DeviceRepository(Protocol):
    """Cổng persistence tối thiểu mà ``DeviceService`` yêu cầu."""

    def save(self, device: Device) -> None: ...

    def get(self, device_id: str) -> Device | None: ...

    def get_by_hostname(self, hostname: str) -> Device | None: ...

    def list(self) -> list[Device]: ...


class PostgresDeviceRepository:
    """Lưu và đọc inventory từ bảng ``devices`` trong PostgreSQL.

    Repository chỉ truy vấn bảng thiết bị, không đọc hay trả về password/secret
    trong bảng ``credentials``.
    """

    def __init__(self, database_url: str) -> None:
        self._sessions = create_session_factory(database_url)

    def save(self, device: Device) -> None:
        """Insert hoặc update một device trong cùng một câu lệnh.

        ``ON CONFLICT (id)`` giúp cùng method phục vụ cả create và update.
        ``created_at`` không bị ghi đè khi update để bảo toàn thời điểm tạo.
        Context manager tự commit khi thành công và rollback khi có exception.
        """
        values = device.model_dump()
        with self._sessions.begin() as session:
            model = session.get(DeviceModel, device.id)
            if model is None:
                session.add(DeviceModel(**values))
                return
            for field, value in values.items():
                if field not in {"id", "created_at", "created_by"}:
                    setattr(model, field, value)

    def get(self, device_id: str) -> Device | None:
        """Đọc một thiết bị bằng primary key và validate thành schema Device."""
        with self._sessions() as session:
            model = session.get(DeviceModel, device_id)
            return Device.model_validate(model, from_attributes=True) if model else None

    def get_by_hostname(self, hostname: str) -> Device | None:
        """Đọc một thiết bị theo hostname, không phân biệt hoa thường."""

        statement = select(DeviceModel).where(
            func.lower(DeviceModel.hostname) == hostname.lower()
        )
        with self._sessions() as session:
            model = session.scalar(statement)
            return Device.model_validate(model, from_attributes=True) if model else None

    def list(self) -> list[Device]:
        """Đọc toàn bộ thiết bị từ database."""

        statement = select(DeviceModel)
        with self._sessions() as session:
            models = session.scalars(statement).all()
            return [Device.model_validate(item, from_attributes=True) for item in models]
