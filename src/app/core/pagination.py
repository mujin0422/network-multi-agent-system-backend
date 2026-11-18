"""Shared pagination contract for collection APIs."""

from math import ceil
from typing import Generic, TypeVar

from pydantic import BaseModel, Field


T = TypeVar("T")


class PageResponse(BaseModel, Generic[T]):
    """Trang dữ liệu kèm metadata để frontend không phải tự đếm toàn bộ bảng."""

    items: list[T]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total_pages: int = Field(ge=0)

    @classmethod
    def create(
        cls,
        items: list[T],
        *,
        total: int,
        page: int,
        page_size: int,
    ) -> "PageResponse[T]":
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=ceil(total / page_size) if total else 0,
        )
