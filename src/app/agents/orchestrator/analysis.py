"""Điều phối kết quả thực thi thành phản hồi cuối trong conversation."""

from datetime import UTC, datetime

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
from app.domains.inventory.services import DeviceService


class AnalysisOrchestrator:
    """Gọi Analyst Agent, lưu timeline và message AGENT/FINAL_RESPONSE."""

    def __init__(
        self,
        analyst: AnalystAgent,
        execution_service: ExecutionService,
        conversation_service: ConversationService,
        device_service: DeviceService,
    ) -> None:
        self._analyst = analyst
        self._execution_service = execution_service
        self._conversation_service = conversation_service
        self._device_service = device_service

    async def analyze_and_respond(
        self,
        task: TaskDetail,
        execution_results: list[NetworkExecutionResult],
    ) -> Message | None:
        current_task = self._execution_service.get_task(task.id)
        if current_task.task_status == TaskStatus.RUNNING:
            return self._save_waiting_response(current_task)

        analysis_started_at = datetime.now(UTC)
        self._execution_service.record_activity(
            task.id,
            ActivityActorType.ANALYST,
            ActivityEventType.ANALYSIS_STARTED,
            ActivityEventStatus.RUNNING,
            started_at=analysis_started_at,
        )
        analysis_inputs = self._build_analysis_inputs(execution_results)
        fallback_error: str | None = None
        try:
            analysis = await self._analyst.analyze(analysis_inputs)
        except Exception as exc:
            # Không để lỗi định dạng đầu ra của LLM làm mất toàn bộ phản hồi.
            # Kết quả dự phòng chỉ mô tả trạng thái thực thi, không tự suy diễn
            # nguyên nhân mạng khi chưa có phân tích hợp lệ.
            fallback_error = str(exc)
            analysis = self._build_fallback_analysis(analysis_inputs)

        self._execution_service.record_activity(
            task.id,
            ActivityActorType.ANALYST,
            ActivityEventType.ANALYSIS_COMPLETED,
            event_data={
                "requires_more_data": analysis.requires_more_data,
                "used_fallback": fallback_error is not None,
                **({"fallback_reason": fallback_error} if fallback_error else {}),
            },
            started_at=analysis_started_at,
            completed_at=datetime.now(UTC),
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

    def _build_analysis_inputs(
        self,
        execution_results: list[NetworkExecutionResult],
    ) -> list[dict]:
        """Expose readable hostnames to the LLM instead of internal IDs."""

        hostnames = {
            device.id: device.hostname
            for device in self._device_service.list_available_devices()
        }
        return [
            {
                "device": hostnames.get(result.device_id, result.device_id),
                "access_mode": result.access_mode.value,
                "status": result.status.value,
                "command_results": [
                    item.model_dump(mode="json") for item in result.results
                ],
                "error_message": result.error_message,
            }
            for result in execution_results
        ]

    @staticmethod
    def _build_fallback_analysis(analysis_inputs: list[dict]) -> AnalysisResult:
        findings: list[str] = []
        for item in analysis_inputs[:4]:
            device = str(item.get("device") or "Thiết bị không xác định")
            status = str(item.get("status") or "UNKNOWN")
            command_count = len(item.get("command_results") or [])
            if status == "SUCCESS":
                findings.append(
                    f"{device}: đã thực thi thành công {command_count} lệnh kiểm tra."
                )
            else:
                findings.append(f"{device}: quá trình thực thi có trạng thái {status}.")

        device_names = ", ".join(
            str(item.get("device") or "thiết bị không xác định")
            for item in analysis_inputs[:4]
        )
        if not device_names:
            device_names = "các thiết bị được chọn"
        return AnalysisResult(
            summary=(
                f"Đã thu thập kết quả lệnh từ {device_names}, nhưng hệ thống chưa "
                "thể chuẩn hóa nội dung phân tích từ mô hình ngôn ngữ."
            ),
            findings=findings,
            likely_causes=[],
            recommendations=[
                "Thử gửi lại yêu cầu hoặc kiểm tra output lệnh đã lưu trong chi tiết task."
            ],
            requires_more_data=True,
        )

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
        sections = [f"Tóm tắt\n{analysis.summary.strip()}"]
        for title, values in (
            ("Phát hiện chính", analysis.findings),
            ("Nguyên nhân có khả năng", analysis.likely_causes),
            ("Hành động đề xuất", analysis.recommendations),
        ):
            if values:
                sections.append(
                    f"{title}\n" + "\n".join(f"• {item.strip()}" for item in values)
                )
        if analysis.requires_more_data:
            sections.append(
                "Trạng thái dữ liệu\n"
                "Cần thu thập thêm dữ liệu trước khi kết luận nguyên nhân gốc."
            )
        return "\n\n".join(sections)
