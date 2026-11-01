"""Workflow LangGraph điều phối toàn bộ vòng đời tự động hóa mạng."""

from typing import NotRequired, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.network import NetworkExecutionResult
from app.agents.orchestrator import (
    AnalysisOrchestrator,
    ExecutionOrchestrator,
    PlanningOrchestrator,
)
from app.domains.conversation.schemas import Conversation, Message
from app.domains.execution.schemas import TaskDetail
from app.domains.inventory.providers import GNS3Provider


class NetworkWorkflowState(TypedDict):
    """Trạng thái được trao đổi giữa các node của LangGraph.

    Trạng thái nghiệp vụ vẫn do domain service lưu trong PostgreSQL. LangGraph
    chỉ quản lý dữ liệu chuyển tiếp giữa các node để không tạo thêm một nguồn
    dữ liệu cạnh tranh cho vòng đời Task, Operation và Approval.
    """

    conversation: NotRequired[Conversation]
    message: NotRequired[Message]
    task: NotRequired[TaskDetail]
    execution_results: NotRequired[list[NetworkExecutionResult]]
    response: NotRequired[Message | None]


class NetworkAutomationWorkflow:
    """LangGraph đã biên dịch, điều phối lập kế hoạch, thực thi và phân tích."""

    def __init__(
        self,
        gns3_provider: GNS3Provider,
        planning: PlanningOrchestrator,
        execution: ExecutionOrchestrator,
        analysis: AnalysisOrchestrator,
    ) -> None:
        """Khởi tạo các dependency và biên dịch hai graph xử lý chính."""

        self._gns3_provider = gns3_provider
        self._planning = planning
        self._execution = execution
        self._analysis = analysis
        self._message_graph = self._build_message_graph()
        self._approval_graph = self._build_approval_graph()

    def _build_message_graph(self):
        """Tạo graph đầy đủ dành cho một message mới từ người dùng."""

        builder = StateGraph(NetworkWorkflowState)
        builder.add_node("check_gns3", self._check_gns3)
        builder.add_node("plan", self._plan)
        builder.add_node("execute", self._execute)
        builder.add_node("analyze", self._analyze)

        builder.add_edge(START, "check_gns3")
        builder.add_edge("check_gns3", "plan")
        builder.add_edge("plan", "execute")
        builder.add_edge("execute", "analyze")
        builder.add_edge("analyze", END)
        return builder.compile()

    def _build_approval_graph(self):
        """Tạo graph tiếp tục thực thi sau khi cấu hình được phê duyệt."""

        builder = StateGraph(NetworkWorkflowState)
        builder.add_node("execute", self._execute)
        builder.add_node("analyze", self._analyze)
        builder.add_edge(START, "execute")
        builder.add_edge("execute", "analyze")
        builder.add_edge("analyze", END)
        return builder.compile()

    async def _check_gns3(
        self,
        _state: NetworkWorkflowState,
    ) -> dict:
        """Kiểm tra nhanh khả năng truy cập GNS3 trước khi lập kế hoạch."""

        # Đây chỉ là health probe; lệnh thiết bị vẫn do NetworkAgent thực hiện.
        self._gns3_provider.check_server_available()
        return {}

    async def _plan(self, state: NetworkWorkflowState) -> dict:
        """Đọc Conversation và Message từ state để tạo Task có kế hoạch."""

        conversation = state.get("conversation")
        message = state.get("message")
        if conversation is None or message is None:
            raise ValueError("Workflow lập kế hoạch cần Conversation và Message")
        task = await self._planning.plan_user_message(conversation, message)
        return {"task": task}

    async def _execute(self, state: NetworkWorkflowState) -> dict:
        """Thực thi Task trong state và trả kết quả mạng cho node kế tiếp."""

        task = state.get("task")
        if task is None:
            raise ValueError("Workflow thực thi cần Task")
        results = await self._execution.execute_task(task)
        return {"execution_results": results}

    async def _analyze(self, state: NetworkWorkflowState) -> dict:
        """Phân tích kết quả thực thi và tạo phản hồi cuối cho hội thoại."""

        task = state.get("task")
        if task is None:
            raise ValueError("Workflow phân tích cần Task")
        response = await self._analysis.analyze_and_respond(
            task,
            state.get("execution_results", []),
        )
        return {"response": response}

    async def run_message(
        self,
        conversation: Conversation,
        message: Message,
    ) -> NetworkWorkflowState:
        """Chạy graph đầy đủ cho một message do người dùng gửi."""

        return await self._message_graph.ainvoke(
            {
                "conversation": conversation,
                "message": message,
                "execution_results": [],
            }
        )

    async def resume_after_approval(
        self,
        operation_device_id: str,
    ) -> NetworkWorkflowState:
        """Tiếp tục từ node thực thi bằng Task đã được lưu trong PostgreSQL."""

        task = self._execution.load_task_for_operation_device(operation_device_id)
        return await self._approval_graph.ainvoke(
            {
                "task": task,
                "execution_results": [],
            }
        )

    def graph_mermaid(self) -> str:
        """Xuất sơ đồ Mermaid ổn định để làm tài liệu và chẩn đoán."""

        return self._message_graph.get_graph().draw_mermaid()
