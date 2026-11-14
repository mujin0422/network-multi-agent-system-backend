"""Schema structured output của Configuration Agent."""

from pydantic import BaseModel, Field


class GeneratedConfiguration(BaseModel):
    """Danh sách CLI được sinh cho một WRITE operation."""

    operation_order: int = Field(ge=1)
    commands: list[str] = Field(min_length=1)


class GeneratedConfigurationSet(BaseModel):
    """Tập cấu hình tương ứng với các WRITE operation trong kế hoạch."""

    configurations: list[GeneratedConfiguration]
