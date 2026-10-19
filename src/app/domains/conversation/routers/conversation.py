"""HTTP routes của Conversation domain."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from app.domains.identity.routers.dependencies import require_permission
from app.domains.identity.schemas import User

from app.domains.conversation.schemas import (
    Conversation,
    ConversationCreate,
    ConversationDetail,
    Message,
    MessageCreate,
)
from app.domains.conversation.services import ConversationService
from app.domains.conversation.routers.dependencies import get_conversation_service


router = APIRouter()


@router.post("/", response_model=Conversation, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    payload: ConversationCreate,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
    _user: Annotated[User, Depends(require_permission("Chatbot", "Execute"))],
) -> Conversation:
    return service.create(payload)


# READ — Lấy danh sách conversation, có thể lọc theo mã người dùng.
@router.get(
    "/",
    response_model=list[Conversation],
    summary="Lấy danh sách conversation",
)
async def list_conversations(
    service: Annotated[ConversationService, Depends(get_conversation_service)],
    _user: Annotated[User, Depends(require_permission("Chatbot", "View"))],
    user_id: Annotated[
        str | None,
        Query(description="Chỉ lấy conversation thuộc user này."),
    ] = None,
) -> list[Conversation]:
    """Trả toàn bộ conversation hoặc lọc theo user_id nếu được cung cấp."""

    return service.list(user_id)


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: str,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
    _user: Annotated[User, Depends(require_permission("Chatbot", "View"))],
) -> ConversationDetail:
    return service.get(conversation_id)


# READ — Lấy danh sách message theo mã conversation.
@router.get(
    "/{conversation_id}/messages",
    response_model=list[Message],
    summary="Lấy danh sách message theo conversation",
)
async def list_messages(
    conversation_id: str,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
    _user: Annotated[User, Depends(require_permission("Chatbot", "View"))],
) -> list[Message]:
    """Trả message thuộc conversation hoặc HTTP 404 nếu conversation không có."""

    return service.list_messages(conversation_id)


@router.post(
    "/{conversation_id}/messages",
    response_model=Message,
    status_code=status.HTTP_201_CREATED,
)
async def add_message(
    conversation_id: str,
    payload: MessageCreate,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
    _user: Annotated[User, Depends(require_permission("Chatbot", "Execute"))],
) -> Message:
    return service.add_message(conversation_id, payload)
