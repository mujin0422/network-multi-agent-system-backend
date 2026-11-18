"""Điều phối USER message thành Task và bản nháp execution plan."""

from dataclasses import dataclass
from datetime import UTC, datetime

from app.agents.planner import PlannerAgent
from app.domains.conversation.schemas import Conversation, Message, MessageSender
from app.domains.conversation.services import ConversationService
from app.domains.execution.schemas import (
    ActivityActorType,
    ActivityEventStatus,
    ActivityEventType,
    ExecutionPlanCreate,
    TaskCreate,
    TaskDetail,
    TaskStatus,
)
from app.domains.execution.services import ExecutionService
from app.domains.inventory.services import DeviceService
from app.domains.inventory.providers import GNS3Provider
from app.domains.inventory.schemas import Device


@dataclass(frozen=True, slots=True)
class PlanningDraft:
    """Dữ liệu chuyển tiếp từ node plan sang configure hoặc execute."""

    task: TaskDetail
    plan: ExecutionPlanCreate
    devices: list[Device]
    interfaces_by_device_id: dict[str, list[str]]

    @property
    def requires_configuration(self) -> bool:
        """Cho biết kế hoạch có ít nhất một ánh xạ WRITE cần sinh CLI."""

        return any(
            device.access_mode.value == "WRITE"
            for operation in self.plan.operations
            for device in operation.devices
        )


class PlanningOrchestrator:
    """Điều phối use case biến một USER message thành kế hoạch có thể thực thi."""

    def __init__(
        self,
        planner: PlannerAgent,
        execution_service: ExecutionService,
        device_service: DeviceService,
        gns3_provider: GNS3Provider | None = None,
        conversation_service: ConversationService | None = None,
        conversation_context_messages: int = 5,
    ) -> None:
        """Khởi tạo các agent và domain service phục vụ giai đoạn lập kế hoạch."""

        # Planner chỉ lập kế hoạch bằng LLM. Hai domain service chịu trách nhiệm
        # đọc/ghi dữ liệu nghiệp vụ; Orchestrator không truy cập repository trực tiếp.
        self._planner = planner
        self._execution_service = execution_service
        self._device_service = device_service
        self._gns3_provider = gns3_provider
        self._conversation_service = conversation_service
        self._conversation_context_messages = conversation_context_messages

    async def prepare_user_message(
        self,
        conversation: Conversation,
        message: Message,
    ) -> PlanningDraft:
        """Tạo Task và kế hoạch nháp nhưng chưa lưu Operation.

        Thứ tự xử lý:
        1. Kiểm tra nguồn và quan hệ của message.
        2. Tạo Task gốc để lưu dấu vết yêu cầu.
        3. Lấy inventory mà Planner được phép lựa chọn.
        4. Gọi Planner Agent để sinh kế hoạch có cấu trúc.
        5. Kiểm tra lại device ID và interface do LLM trả về.
        6. Trả bản nháp cho node configure hoặc bước lưu kế hoạch READ.
        """

        # Bước 1: Kiểm tra nguồn và quan hệ của message.
        # Bước 1.1: Chỉ message do USER gửi mới được chuyển thành task. Việc này
        # ngăn message trả lời của ASSISTANT tạo thêm task theo vòng lặp.
        if message.sender_by != MessageSender.USER:
            raise ValueError("Planner chỉ nhận message từ USER")

        # Bước 1.2: Message và Conversation được truyền riêng nên phải xác nhận chúng thực
        # sự thuộc cùng một luồng hội thoại trước khi ghi dữ liệu execution.
        if message.conversation_id != conversation.id:
            raise ValueError("Message không thuộc conversation được cung cấp")

        # Bước 2: Tạo Task trước khi gọi LLM. Task liên kết ngược tới chính
        # source_message_id để truy vết yêu cầu nào đã tạo ra kế hoạch này.
        task = self._execution_service.create_task(
            TaskCreate(
                conversation_id=conversation.id,
                source_message_id=message.id,
                user_id=conversation.user_id,
                input_message=message.message,
            )
        )
        self._execution_service.record_activity(
            task.id,
            ActivityActorType.ORCHESTRATOR,
            ActivityEventType.MESSAGE_RECEIVED,
            event_data={"message_id": message.id},
        )
        self._execution_service.record_activity(
            task.id,
            ActivityActorType.ORCHESTRATOR,
            ActivityEventType.TASK_CREATED,
        )

        # Bước 3: Chỉ cung cấp cho Planner các thiết bị đang có trong Inventory.
        # Planner không tự truy vấn database và cũng không được tự bịa device ID.
        devices = self._device_service.list_available_devices()

        # Bước 4: Planner dùng LLM để chuyển câu tiếng Việt thành PlannedTask,
        # gồm operations, dependencies và danh sách device của từng operation.
        failure_actor = ActivityActorType.PLANNER
        failure_stage = "PLANNING"
        try:
            node_interfaces = (
                self._gns3_provider.list_node_interfaces()
                if self._gns3_provider is not None
                else {}
            )
            topology_neighbors = (
                self._gns3_provider.list_topology_neighbors()
                if self._gns3_provider is not None
                else {}
            )
            conversation_history = (
                self._conversation_service.get_recent_messages_before(
                    message,
                    limit=self._conversation_context_messages,
                )
                if self._conversation_service is not None
                and self._conversation_context_messages > 0
                else []
            )
            plan = await self._planner.plan(
                message.message,
                devices,
                node_interfaces=node_interfaces,
                topology_neighbors=topology_neighbors,
                conversation_history=conversation_history,
            )
            self._execution_service.record_activity(
                task.id,
                ActivityActorType.PLANNER,
                ActivityEventType.PLAN_GENERATED,
                event_data={"operation_count": len(plan.operations)},
            )
            interfaces_by_device_id = {
                device.id: node_interfaces.get(device.hostname, []) for device in devices
            }
            PlannerAgent._validate_interface_commands(plan, interfaces_by_device_id)

            # Bước 5: Không tin hoàn toàn output LLM. Tất cả device ID trong kế
            # hoạch phải thuộc inventory vừa cung cấp.
            available_device_ids = {device.id for device in devices}
            planned_device_ids = {
                device.device_id
                for operation in plan.operations
                for device in operation.devices
            }
            unknown_device_ids = planned_device_ids - available_device_ids
            if unknown_device_ids:
                unknown = ", ".join(sorted(unknown_device_ids))
                raise ValueError(f"Planner trả về device không tồn tại: {unknown}")
        except Exception as exc:
            self.fail_task(task, failure_actor, failure_stage, exc)
            raise

        # Bước 6: Chưa lưu Operation để node configure có thể bổ sung CLI WRITE.
        return PlanningDraft(
            task=task,
            plan=plan,
            devices=devices,
            interfaces_by_device_id=interfaces_by_device_id,
        )

    def persist_plan(
        self,
        draft: PlanningDraft,
        plan: ExecutionPlanCreate | None = None,
    ) -> TaskDetail:
        """Lưu kế hoạch READ hoặc kế hoạch WRITE đã được configure hoàn chỉnh."""

        final_plan = plan or draft.plan
        try:
            # Bước 1: Kiểm tra lại device ID sau node configure trước khi lưu.
            available_device_ids = {device.id for device in draft.devices}
            planned_device_ids = {
                device.device_id
                for operation in final_plan.operations
                for device in operation.devices
            }
            unknown_device_ids = planned_device_ids - available_device_ids
            if unknown_device_ids:
                unknown = ", ".join(sorted(unknown_device_ids))
                raise ValueError(f"Planner trả về device không tồn tại: {unknown}")

            # Bước 2: Chuyển plan thành operation, dependency và device mapping.
            planned_task = self._execution_service.create_execution_plan(
                draft.task.id,
                final_plan,
            )
        except Exception as exc:
            self.fail_task(
                draft.task,
                ActivityActorType.PLANNER,
                "PLAN_PERSISTENCE",
                exc,
            )
            raise
        self._execution_service.record_activity(
            draft.task.id,
            ActivityActorType.PLANNER,
            ActivityEventType.OPERATIONS_CREATED,
            event_data={"count": len(planned_task.operations)},
        )
        self._execution_service.record_activity(
            draft.task.id,
            ActivityActorType.PLANNER,
            ActivityEventType.DEPENDENCIES_CREATED,
            event_data={
                "count": sum(
                    len(operation.dependencies) for operation in final_plan.operations
                )
            },
        )
        self._execution_service.record_activity(
            draft.task.id,
            ActivityActorType.PLANNER,
            ActivityEventType.DEVICES_ASSIGNED,
            event_data={
                "count": sum(
                    len(operation.devices) for operation in final_plan.operations
                )
            },
        )
        return planned_task

    def fail_task(
        self,
        task: TaskDetail,
        actor: ActivityActorType,
        stage: str,
        error: Exception,
    ) -> None:
        """Đánh dấu Task thất bại và lưu nguyên nhân theo giai đoạn điều phối."""

        self._execution_service.update_task(
            task.model_copy(
                update={
                    "task_status": TaskStatus.FAILED,
                    "completed_at": datetime.now(UTC),
                }
            )
        )
        self._execution_service.record_activity(
            task.id,
            actor,
            ActivityEventType.TASK_FAILED,
            ActivityEventStatus.FAILED,
            event_data={"error": str(error), "stage": stage},
        )
