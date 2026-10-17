"""Map shared application exceptions to HTTP responses."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions.domain import (
    InvalidStateTransitionError,
    ResourceConflictError,
    ResourceNotFoundError,
)


def register_error_handlers(app: FastAPI) -> None:
    """Đăng ký error mapping một lần khi khởi tạo FastAPI."""

    @app.exception_handler(ResourceNotFoundError)
    async def handle_not_found(
        _request: Request,
        exc: ResourceNotFoundError,
    ) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(ResourceConflictError)
    async def handle_conflict(
        _request: Request,
        exc: ResourceConflictError,
    ) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(InvalidStateTransitionError)
    async def handle_invalid_transition(
        _request: Request,
        exc: InvalidStateTransitionError,
    ) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})
