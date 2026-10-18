"""HTTP routes cho resource Credential."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.domains.inventory.routers.dependencies import get_credential_service
from app.domains.inventory.schemas import Credential, CredentialCreate, CredentialUpdate
from app.domains.inventory.services import CredentialService


router = APIRouter()


# CREATE — Thêm Credential và mã hóa secret trước khi lưu.
@router.post(
    "/",
    response_model=Credential,
    status_code=status.HTTP_201_CREATED,
    summary="Thêm credential",
)
async def create_credential(
    payload: CredentialCreate,
    service: Annotated[CredentialService, Depends(get_credential_service)],
) -> Credential:
    return service.create_credential(payload)


# READ — Lấy danh sách metadata Credential, không chứa password/secret.
@router.get(
    "/",
    response_model=list[Credential],
    summary="Lấy danh sách credential",
)
async def list_credentials(
    service: Annotated[CredentialService, Depends(get_credential_service)],
) -> list[Credential]:
    return service.list_credentials()


# READ — Lấy metadata một Credential theo ID.
@router.get(
    "/{credential_id}",
    response_model=Credential,
    summary="Lấy credential theo ID",
)
async def get_credential(
    credential_id: str,
    service: Annotated[CredentialService, Depends(get_credential_service)],
) -> Credential:
    return service.get_credential(credential_id)


# UPDATE — Sửa metadata, password hoặc secret của Credential.
@router.patch(
    "/{credential_id}",
    response_model=Credential,
    summary="Cập nhật credential",
)
async def update_credential(
    credential_id: str,
    payload: CredentialUpdate,
    service: Annotated[CredentialService, Depends(get_credential_service)],
) -> Credential:
    return service.update_credential(credential_id, payload)


# DELETE chưa được triển khai vì Credential có thể đang được Device tham chiếu.
