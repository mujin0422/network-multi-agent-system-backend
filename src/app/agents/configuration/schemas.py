"""Schema structured output của Configuration Agent."""

from pydantic import BaseModel, Field


class GeneratedConfiguration(BaseModel):
    """Danh sách CLI được sinh cho một WRITE operation."""
    operation_order: int = Field(ge=1, description="Thứ tự của WRITE operation trong kế hoạch.")
    commands: list[str] = Field(min_length=1, description="Danh sách các lệnh CLI được sinh cho WRITE operation.")


class GeneratedConfigurationSet(BaseModel):
    """Tập cấu hình tương ứng với các WRITE operation trong kế hoạch."""
    configurations: list[GeneratedConfiguration] = Field(min_length=1, description="Danh sách các cấu hình được sinh cho các WRITE operation.")
