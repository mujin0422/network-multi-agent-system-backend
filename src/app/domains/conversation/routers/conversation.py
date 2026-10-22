"""HTTP routes của Conversation domain."""

from typing import Annotated

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status

from app.agents.dependencies import (
    get_analysis_orchestrator,
    get_execution_orchestrator,
    get_gns3_provider,
    get_planning_orchestrator,
)
from app.agents.orchestrator import AnalysisOrchestrator, ExecutionOrchestrator, PlanningOrchestrator
from app.domains.conversation.schemas import (
    Conversation,
    ConversationDetail,
    ConversationStart,
    ConversationStarted,
    Message,
    MessageCreate,
    MessageSender,
)
from app.domains.conversation.routers.dependencies import (
    get_conversation_service,
    get_conversation_title_generator,
)
from app.domains.conversation.services import (
    ConversationService,
    ConversationTitleGeneratorProtocol,
)
from app.domains.identity.routers.dependencies import require_permission
from app.domains.identity.schemas import User
from app.domains.inventory.providers import GNS3Provider


router = APIRouter()
logger = logging.getLogger(__name__)


async def _generate_conversation_title(
    service: ConversationService,
    title_generator: ConversationTitleGeneratorProtocol,
    conversation: Conversation,
    first_message: Message,
) -> None:
    """Sinh title nền để không chặn response của message đầu tiên."""

    try:
        title = await title_generator.generate(first_message.message)
        service.update_title(conversation, title)
    except Exception:
        logger.exception("Không thể tạo title cho conversation %s", conversation.id)


async def _run_ai_workflow(
    conversation: Conversation,
    message: Message,
    planning_orchestrator: PlanningOrchestrator,
    execution_orchestrator: ExecutionOrchestrator,
    analysis_orchestrator: AnalysisOrchestrator,
    gns3_provider: GNS3Provider,
) -> None:
    """Chạy workflow sau khi HTTP response đã trả để UI polling timeline."""

    try:
        gns3_provider.check_server_available()
        task = await planning_orchestrator.plan_user_message(conversation, message)
        results = await execution_orchestrator.execute_task(task)
        await analysis_orchestrator.analyze_and_respond(task, results)
    except Exception:
        logger.exception("AI workflow thất bại cho message %s", message.id)


async def _run_first_message_workflow(
    service: ConversationService,
    title_generator: ConversationTitleGeneratorProtocol,
    conversation: Conversation,
    message: Message,
    planning_orchestrator: PlanningOrchestrator,
    execution_orchestrator: ExecutionOrchestrator,
    analysis_orchestrator: AnalysisOrchestrator,
    gns3_provider: GNS3Provider,
) -> None:
    """Ưu tiên workflow; sinh title sau để không gọi hai LLM đồng thời."""

    await _run_ai_workflow(
        conversation,
        message,
        planning_orchestrator,
        execution_orchestrator,
        analysis_orchestrator,
        gns3_provider,
    )
    await _generate_conversation_title(
        service,
        title_generator,
        conversation,
        message,
    )


# CREATE (Conversation + first Message) — Chỉ tạo conversation khi User gửi thật.
@router.post(
    "/messages",
    response_model=ConversationStarted,
    status_code=status.HTTP_201_CREATED,
    summary="Bắt đầu conversation bằng USER_REQUEST đầu tiên",
)
async def start_conversation(
    payload: ConversationStart,
    background_tasks: BackgroundTasks,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
    title_generator: Annotated[
        ConversationTitleGeneratorProtocol,
        Depends(get_conversation_title_generator),
    ],
    planning_orchestrator: Annotated[
        PlanningOrchestrator,
        Depends(get_planning_orchestrator),
    ],
    execution_orchestrator: Annotated[
        ExecutionOrchestrator,
        Depends(get_execution_orchestrator),
    ],
    analysis_orchestrator: Annotated[
        AnalysisOrchestrator,
        Depends(get_analysis_orchestrator),
    ],
    gns3_provider: Annotated[GNS3Provider, Depends(get_gns3_provider)],
    user: Annotated[User, Depends(require_permission("Chatbot", "Add"))],
) -> ConversationStarted:
    """Tạo Conversation, lưu Message đầu tiên, sinh title và chạy AI workflow."""

    # Bước 1: Transaction ngắn tạo Conversation và USER_REQUEST đầu tiên.
    started = service.start(user.id, payload)

    # Bước 2: Sinh title và chạy AI workflow đồng thời trong background.
    # task_activity_events và hiển thị từng bước khi chúng vừa được lưu.
    background_tasks.add_task(
        _run_first_message_workflow,
        service,
        title_generator,
        started.conversation,
        started.message,
        planning_orchestrator,
        execution_orchestrator,
        analysis_orchestrator,
        gns3_provider,
    )

    return ConversationStarted(
        conversation=started.conversation,
        message=started.message,
    )


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
    background_tasks: BackgroundTasks,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
    planning_orchestrator: Annotated[
        PlanningOrchestrator,
        Depends(get_planning_orchestrator),
    ],
    execution_orchestrator: Annotated[
        ExecutionOrchestrator,
        Depends(get_execution_orchestrator),
    ],
    analysis_orchestrator: Annotated[
        AnalysisOrchestrator,
        Depends(get_analysis_orchestrator),
    ],
    gns3_provider: Annotated[GNS3Provider, Depends(get_gns3_provider)],
    _user: Annotated[User, Depends(require_permission("Chatbot", "Add"))],
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
        # Workflow chạy sau khi API trả message. Frontend dùng source message ID
        # để phát hiện Task mới và cập nhật timeline theo thời gian thực.
        background_tasks.add_task(
            _run_ai_workflow,
            conversation,
            message,
            planning_orchestrator,
            execution_orchestrator,
            analysis_orchestrator,
            gns3_provider,
        )

    # Bước 4: API trả ngay message đã lưu.
    return message
