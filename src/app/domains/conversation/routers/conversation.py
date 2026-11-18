"""HTTP routes của Conversation domain."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from fastapi.concurrency import run_in_threadpool

from app.domains.conversation.schemas import (
    Conversation,
    ConversationDetail,
    ConversationPage,
    ConversationStart,
    ConversationStarted,
    ConversationTitleUpdate,
    Message,
    MessageCreate,
    MessagePage,
    MessageSender,
)
from app.domains.conversation.routers.dependencies import get_conversation_service
from app.domains.conversation.services import ConversationService
from app.domains.identity.routers.dependencies import require_permission
from app.domains.identity.schemas import User
from app.domains.benchmark.routers.dependencies import get_benchmark_run_service
from app.domains.benchmark.services import BenchmarkRunService
from app.domains.workflow_job.dependencies import get_workflow_job_service
from app.domains.workflow_job.service import WorkflowJobService


router = APIRouter()


# CREATE (Conversation + first Message) — Chỉ tạo conversation khi User gửi thật.
@router.post(
    "/messages",
    response_model=ConversationStarted,
    status_code=status.HTTP_201_CREATED,
    summary="Bắt đầu conversation bằng USER_REQUEST đầu tiên",
)
async def start_conversation(
    payload: ConversationStart,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
    benchmark_service: Annotated[
        BenchmarkRunService,
        Depends(get_benchmark_run_service),
    ],
    workflow_jobs: Annotated[
        WorkflowJobService,
        Depends(get_workflow_job_service),
    ],
    user: Annotated[User, Depends(require_permission("Chatbot", "Add"))],
) -> ConversationStarted:
    """Tạo Conversation, lưu Message đầu tiên, sinh title và chạy AI workflow."""

    # Bước 1: Transaction ngắn tạo Conversation và USER_REQUEST đầu tiên.
    started = await run_in_threadpool(service.start, user.id, payload)

    if payload.benchmark_run_id is not None:
        await run_in_threadpool(
            benchmark_service.bind_message,
            payload.benchmark_run_id,
            started.conversation,
            started.message,
        )

    # Bước 2: Enqueue durable job; worker riêng chạy LangGraph và sinh title.
    await run_in_threadpool(
        workflow_jobs.enqueue_message,
        started.conversation.id,
        started.message.id,
        benchmark_run_id=payload.benchmark_run_id,
        generate_title=True,
    )

    return ConversationStarted(
        conversation=started.conversation,
        message=started.message,
    )


# READ (Conversation) — Lấy danh sách conversation, có thể lọc theo mã người dùng.
@router.get(
    "/",
    response_model=ConversationPage,
    summary="Lấy danh sách conversation",
)
def list_conversations(
    service: Annotated[ConversationService, Depends(get_conversation_service)],
    _user: Annotated[User, Depends(require_permission("Chatbot", "View"))],
    user_id: Annotated[
        str | None,
        Query(description="Chỉ lấy conversation thuộc user này."),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query()] = None,
) -> ConversationPage:
    """Trả một trang conversation mới nhất bằng cursor pagination."""

    return service.list_page(user_id=user_id, limit=limit, cursor=cursor)


# READ (Conversation) — Lấy chi tiết conversation theo mã.
@router.get(
    "/{conversation_id}",
    response_model=ConversationDetail,
    summary="Lấy chi tiết conversation theo mã",
)
def get_conversation(
    conversation_id: str,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
    _user: Annotated[User, Depends(require_permission("Chatbot", "View"))],
) -> ConversationDetail:
    return service.get(conversation_id)


@router.patch(
    "/{conversation_id}/title",
    response_model=Conversation,
    summary="Đổi tiêu đề conversation",
)
def rename_conversation(
    conversation_id: str,
    payload: ConversationTitleUpdate,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
    user: Annotated[User, Depends(require_permission("Chatbot", "Add"))],
) -> Conversation:
    """Đổi tiêu đề conversation thuộc người dùng đang đăng nhập."""

    return service.rename(conversation_id, user.id, payload)


# READ (Message) — Lấy danh sách message theo mã conversation.
@router.get(
    "/{conversation_id}/messages",
    response_model=MessagePage,
    summary="Lấy danh sách message theo conversation",
)
def list_messages(
    conversation_id: str,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
    _user: Annotated[User, Depends(require_permission("Chatbot", "View"))],
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
    cursor: Annotated[str | None, Query()] = None,
) -> MessagePage:
    """Trả một trang message gần nhất hoặc các message cũ theo cursor."""

    return service.list_message_page(
        conversation_id,
        limit=limit,
        cursor=cursor,
    )


# CREATE (Message) — Thêm message vào conversation.
@router.post(
    "/{conversation_id}/messages",
    response_model=Message,
    status_code=status.HTTP_201_CREATED,
)
async def create_message(
    conversation_id: str,
    payload: MessageCreate,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
    workflow_jobs: Annotated[
        WorkflowJobService,
        Depends(get_workflow_job_service),
    ],
    _user: Annotated[User, Depends(require_permission("Chatbot", "Add"))],
) -> Message:
    """Lưu message và kích hoạt planning nếu người gửi là USER.

    Endpoint này là điểm bắt đầu của AI workflow; client không gọi trực tiếp Planner Agent hoặc Orchestrator.
    """

    # Bước 1: Xác nhận conversation tồn tại và lấy đủ user_id cần để tạo Task.
    conversation = await run_in_threadpool(service.get, conversation_id)

    # Bước 2: Lưu message trước. Nhờ vậy Task luôn có source_message_id hợp lệ & lịch sử hội thoại vẫn còn nếu bước gọi LLM gặp lỗi.
    message = await run_in_threadpool(
        service.create_message,
        conversation_id,
        payload,
    )

    # Bước 3: (CHECK) Chỉ USER message kích hoạt Planner. Message của ASSISTANT/SYSTEM được lưu như lịch sử nhưng không tạo task mới, tránh lặp vô hạn.
    if message.sender_by == MessageSender.USER:
        # Worker riêng claim durable job sau khi API trả message.
        await run_in_threadpool(
            workflow_jobs.enqueue_message,
            conversation.id,
            message.id,
        )

    # Bước 4: API trả ngay message đã lưu.
    return message
