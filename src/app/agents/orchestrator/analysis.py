"""Điều phối kết quả thực thi thành phản hồi cuối trong conversation."""

from app.agents.analyst import AnalystAgent, AnalysisResult
from app.agents.network import NetworkExecutionResult
from app.domains.conversation.schemas import Message, MessageCreate, MessageSender, MessageType
from app.domains.conversation.services import ConversationService
from app.domains.execution.schemas import (
    ActivityActorType,
    ActivityEventStatus,
    ActivityEventType,
    TaskDetail,
    TaskStatus,
)
from app.domains.execution.services import ExecutionService


class AnalysisOrchestrator:
    """Gọi Analyst Agent, lưu timeline và message AGENT/FINAL_RESPONSE."""

    def __init__(
        self,
        analyst: AnalystAgent,
        execution_service: ExecutionService,
        conversation_service: ConversationService,
    ) -> None:
        self._analyst = analyst
        self._execution_service = execution_service
        self._conversation_service = conversation_service

    async def analyze_and_respond(
        self,
        task: TaskDetail,
        execution_results: list[NetworkExecutionResult],
    ) -> Message | None:
        current_task = self._execution_service.get_task(task.id)
        if current_task.task_status == TaskStatus.RUNNING:
            return self._save_waiting_response(current_task)

        self._execution_service.record_activity(
            task.id,
            ActivityActorType.ANALYST,
            ActivityEventType.ANALYSIS_STARTED,
        )
        try:
            analysis = await self._analyst.analyze(
                [result.model_dump(mode="json") for result in execution_results]
            )
        except Exception as exc:
            self._execution_service.record_activity(
                task.id,
                ActivityActorType.ANALYST,
                ActivityEventType.ANALYSIS_COMPLETED,
                ActivityEventStatus.FAILED,
                event_data={"error": str(exc)},
            )
            raise

        self._execution_service.record_activity(
            task.id,
            ActivityActorType.ANALYST,
            ActivityEventType.ANALYSIS_COMPLETED,
            event_data={"requires_more_data": analysis.requires_more_data},
        )
        message = self._conversation_service.add_message(
            current_task.conversation_id,
            MessageCreate(
                sender_by=MessageSender.AGENT,
                reply_to_message_id=current_task.source_message_id,
                message_type=MessageType.FINAL_RESPONSE,
                message=self._format_analysis(analysis),
            ),
        )
        self._execution_service.record_activity(
            task.id,
            ActivityActorType.ANALYST,
            ActivityEventType.FINAL_RESPONSE_CREATED,
            event_data={"message_id": message.id},
        )
        return message

    def _save_waiting_response(self, task: TaskDetail) -> Message:
        return self._conversation_service.add_message(
            task.conversation_id,
            MessageCreate(
                sender_by=MessageSender.AGENT,
                reply_to_message_id=task.source_message_id,
                message_type=MessageType.APPROVAL_REQUEST,
                message="Kế hoạch đã được tạo. Một hoặc nhiều thao tác cấu hình đang chờ bạn phê duyệt.",
            ),
        )

    @staticmethod
    def _format_analysis(analysis: AnalysisResult) -> str:
        sections = [analysis.summary]
        for title, values in (
            ("Phát hiện", analysis.findings),
            ("Nguyên nhân có khả năng", analysis.likely_causes),
            ("Khuyến nghị", analysis.recommendations),
        ):
            if values:
                sections.append(f"{title}:\n" + "\n".join(f"- {item}" for item in values))
        return "\n\n".join(sections)
