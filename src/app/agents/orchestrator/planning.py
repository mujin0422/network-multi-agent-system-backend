"""Điều phối USER message thành Task và execution plan."""

from datetime import UTC, datetime

from app.agents.planner import PlannerAgent
from app.domains.conversation.schemas import Conversation, Message, MessageSender
from app.domains.execution.schemas import (
    ActivityActorType,
    ActivityEventStatus,
    ActivityEventType,
    TaskCreate,
    TaskDetail,
    TaskStatus,
)
from app.domains.execution.services import ExecutionService
from app.domains.inventory.services import DeviceService


class PlanningOrchestrator:
    """Điều phối use case biến một USER message thành kế hoạch có thể thực thi."""

    def __init__(
        self,
        planner: PlannerAgent,
        execution_service: ExecutionService,
        device_service: DeviceService,
    ) -> None:
        # Planner chỉ lập kế hoạch bằng LLM. Hai domain service chịu trách nhiệm
        # đọc/ghi dữ liệu nghiệp vụ; Orchestrator không truy cập repository trực tiếp.
        self._planner = planner
        self._execution_service = execution_service
        self._device_service = device_service

    async def plan_user_message(
        self,
        conversation: Conversation,
        message: Message,
    ) -> TaskDetail:
        """Tạo Task và toàn bộ execution plan từ message của người dùng.

        Thứ tự xử lý:
        1. Kiểm tra nguồn và quan hệ của message.
        2. Tạo Task gốc để lưu dấu vết yêu cầu.
        3. Lấy inventory mà Planner được phép lựa chọn.
        4. Gọi Planner Agent để sinh kế hoạch có cấu trúc.
        5. Kiểm tra lại device ID do LLM trả về.
        6. Lưu operation, dependency và operation-device mapping.
        """

        # Bước 1: Chỉ message do USER gửi mới được chuyển thành task. Việc này
        # ngăn message trả lời của ASSISTANT tạo thêm task theo vòng lặp.
        if message.sender_by != MessageSender.USER:
            raise ValueError("Planner chỉ nhận message từ USER")

        # Message và Conversation được truyền riêng nên phải xác nhận chúng thực
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
        try:
            plan = await self._planner.plan(message.message, devices)
        except Exception as exc:
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
                ActivityActorType.PLANNER,
                ActivityEventType.TASK_FAILED,
                ActivityEventStatus.FAILED,
                event_data={"error": str(exc), "stage": "PLANNING"},
            )
            raise
        self._execution_service.record_activity(
            task.id,
            ActivityActorType.PLANNER,
            ActivityEventType.PLAN_GENERATED,
            event_data={"operation_count": len(plan.operations)},
        )

        try:
            # Bước 5: Không tin hoàn toàn output LLM. Tất cả device ID trong kế
            # hoạch phải thuộc inventory vừa cung cấp thì mới được phép lưu.
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

            # Bước 6: Chuyển plan thành operation, dependency và device mapping.
            planned_task = self._execution_service.create_execution_plan(task.id, plan)
        except Exception as exc:
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
                ActivityActorType.PLANNER,
                ActivityEventType.TASK_FAILED,
                ActivityEventStatus.FAILED,
                event_data={"error": str(exc), "stage": "PLAN_PERSISTENCE"},
            )
            raise
        self._execution_service.record_activity(
            task.id,
            ActivityActorType.PLANNER,
            ActivityEventType.OPERATIONS_CREATED,
            event_data={"count": len(planned_task.operations)},
        )
        self._execution_service.record_activity(
            task.id,
            ActivityActorType.PLANNER,
            ActivityEventType.DEPENDENCIES_CREATED,
            event_data={
                "count": sum(len(operation.dependencies) for operation in plan.operations)
            },
        )
        self._execution_service.record_activity(
            task.id,
            ActivityActorType.PLANNER,
            ActivityEventType.DEVICES_ASSIGNED,
            event_data={
                "count": sum(len(operation.devices) for operation in plan.operations)
            },
        )
        return planned_task
