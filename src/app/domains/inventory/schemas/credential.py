"""Schemas ánh xạ bảng ``credentials``."""

from datetime import datetime

from pydantic import BaseModel, Field


class Credential(BaseModel):
    """Metadata credential an toàn để quản lý mà không trả ciphertext."""

    id: str = Field(description="Khóa chính của credential.")
    name: str = Field(max_length=150, description="Tên credential duy nhất.")
    description: str | None = Field(default=None, description="Mô tả credential.")
    username: str = Field(max_length=255, description="Username kết nối thiết bị.")
    encryption_type: str = Field(
        max_length=100,
        description="Thuật toán/định dạng mã hóa password và secret.",
    )
    created_by: str = Field(description="ID user tạo credential.")
    last_updated_by: str | None = Field(
        default=None,
        description="ID user cập nhật credential gần nhất.",
    )
    created_at: datetime = Field(description="Thời điểm tạo theo UTC.")
    last_updated_at: datetime = Field(description="Thời điểm cập nhật theo UTC.")


class CredentialRecord(Credential):
    """Bản ghi nội bộ đầy đủ với ciphertext bị loại khỏi serialization."""

    password: str = Field(
        exclude=True,
        repr=False,
        description="Password ciphertext ASCII-armored lưu trong database.",
    )
    secret: str | None = Field(
        default=None,
        exclude=True,
        repr=False,
        description="Enable-secret ciphertext; null nếu không sử dụng.",
    )
