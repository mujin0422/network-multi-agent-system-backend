"""HTTP routes của Conversation domain."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.agents.dependencies import (
    get_execution_orchestrator,
    get_gns3_provider,
    get_planning_orchestrator,
)
from app.agents.orchestrator import ExecutionOrchestrator, PlanningOrchestrator
from app.domains.conversation.schemas import (
    Conversation,
    ConversationCreate,
    ConversationDetail,
    Message,
    MessageCreate,
    MessageSender,
)
from app.domains.conversation.routers.dependencies import get_conversation_service
from app.domains.conversation.services import ConversationService
from app.domains.identity.routers.dependencies import require_permission
from app.domains.identity.schemas import User
from app.domains.inventory.providers import GNS3Provider


router = APIRouter()


# CREATE (Convesation) — Tạo conversation mới.
@router.post("/", response_model=Conversation, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    payload: ConversationCreate,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
    _user: Annotated[User, Depends(require_permission("Chatbot", "Execute"))],
) -> Conversation:
    return service.create(payload)


# READ (Conversation) — Lấy danh sách conversation, có thể lọc theo mã người dùng.
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


# READ (Conversation) — Lấy chi tiết conversation theo mã.
@router.get(
    "/{conversation_id}",
    response_model=ConversationDetail,
    summary="Lấy chi tiết conversation theo mã",
)
async def get_conversation(
    conversation_id: str,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
    _user: Annotated[User, Depends(require_permission("Chatbot", "View"))],
) -> ConversationDetail:
    return service.get(conversation_id)


# READ (Message) — Lấy danh sách message theo mã conversation.
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


# CREATE (Message) — Thêm message vào conversation.
@router.post(
    "/{conversation_id}/messages",
    response_model=Message,
    status_code=status.HTTP_201_CREATED,
)
async def add_message(
    conversation_id: str,
    payload: MessageCreate,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
    planning_orchestrator: Annotated[
        PlanningOrchestrator,
        Depends(get_planning_orchestrator),
    ],
    execution_orchestrator: Annotated[
        ExecutionOrchestrator,
        Depends(get_execution_orchestrator),
    ],
    gns3_provider: Annotated[GNS3Provider, Depends(get_gns3_provider)],
    _user: Annotated[User, Depends(require_permission("Chatbot", "Execute"))],
) -> Message:
    """Lưu message và kích hoạt planning nếu người gửi là USER.

    Endpoint này là điểm bắt đầu của AI workflow; client không gọi trực tiếp Planner Agent hoặc Orchestrator.
    """

    # Bước 1: Xác nhận conversation tồn tại và lấy đủ user_id cần để tạo Task.
    conversation = service.get(conversation_id)

    # Bước 2: Lưu message trước. Nhờ vậy Task luôn có source_message_id hợp lệ & lịch sử hội thoại vẫn còn nếu bước gọi LLM gặp lỗi.
    message = service.add_message(conversation_id, payload)

    # Bước 3: (CHECK) Chỉ USER message kích hoạt Planner. Message của ASSISTANT/SYSTEM được lưu như lịch sử nhưng không tạo task mới, tránh lặp vô hạn.
    if message.sender_by == MessageSender.USER:
        # Bước 3.1: Chỉ kiểm tra GNS3 Server có đang bật hay không.
        # Không tự mở project và không tự bật node.
        gns3_provider.check_server_available()

        # Bước 3.2: Planner tạo Task và lưu nguyên tử Operation, Dependency cùng
        # Operation Device. Chỉ khi transaction này thành công mới có TaskDetail.
        task = await planning_orchestrator.plan_user_message(conversation, message)

        # Bước 3.3: Thực thi tuần tự các operation vừa lưu. ExecutionOrchestrator
        # đọc lại Operation/TaskOperationDevice từ database rồi gọi NetworkAgent.
        await execution_orchestrator.execute_task(task)

    # Bước 4: API trả message sau khi planning và execution đã hoàn tất.
    return message
