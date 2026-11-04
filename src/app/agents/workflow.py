"""Workflow LangGraph điều phối toàn bộ vòng đời tự động hóa mạng."""

from typing import NotRequired, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.analyst import AnalysisResult
from app.agents.network import NetworkExecutionResult
from app.agents.orchestrator import (
    AnalysisOrchestrator,
    ExecutionOrchestrator,
    PlanningOrchestrator,
)
from app.domains.conversation.schemas import Conversation, Message
from app.domains.execution.schemas import TaskDetail, TaskType
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
    analysis: NotRequired[AnalysisResult | None]
    investigation_round: NotRequired[int]


class NetworkAutomationWorkflow:
    """LangGraph đã biên dịch, điều phối lập kế hoạch, thực thi và phân tích."""

    def __init__(
        self,
        gns3_provider: GNS3Provider,
        planning: PlanningOrchestrator,
        execution: ExecutionOrchestrator,
        analysis: AnalysisOrchestrator,
        max_investigation_rounds: int = 2,
        diagnosis_confidence_threshold: float = 0.8,
    ) -> None:
        """Khởi tạo các dependency và biên dịch hai graph xử lý chính."""

        self._gns3_provider = gns3_provider
        self._planning = planning
        self._execution = execution
        self._analysis = analysis
        self._max_investigation_rounds = max_investigation_rounds
        self._diagnosis_confidence_threshold = diagnosis_confidence_threshold
        self._message_graph = self._build_message_graph()
        self._approval_graph = self._build_approval_graph()


    def _build_message_graph(self):
        """Tạo graph đầy đủ dành cho một message mới từ người dùng."""

        # Bước 1: Khai báo các node nghiệp vụ sẽ tham gia luồng message mới.
        builder = StateGraph(NetworkWorkflowState)
        builder.add_node("check_gns3", self._check_gns3)
        builder.add_node("plan", self._plan)
        builder.add_node("execute", self._execute)
        builder.add_node("analyze", self._analyze)
        builder.add_node("investigate", self._investigate)
        builder.add_node("finalize", self._finalize)

        # Bước 2: Nối luồng chính từ kiểm tra hạ tầng đến phân tích evidence.
        builder.add_edge(START, "check_gns3")
        builder.add_edge("check_gns3", "plan")
        builder.add_edge("plan", "execute")
        builder.add_edge("execute", "analyze")

        # Bước 3: Rẽ nhánh sang điều tra bổ sung khi kết luận chưa đủ tin cậy.
        builder.add_conditional_edges(
            "analyze",
            self._route_after_analysis,
            {"investigate": "investigate", "finalize": "finalize"},
        )

        # Bước 4: Phân tích lại evidence mới; chỉ finalize khi đủ dữ liệu/đủ vòng.
        builder.add_edge("investigate", "analyze")
        builder.add_edge("finalize", END)
        return builder.compile()


    def _build_approval_graph(self):
        """Tạo graph tiếp tục thực thi sau khi cấu hình được phê duyệt."""

        builder = StateGraph(NetworkWorkflowState)
        builder.add_node("execute", self._execute)
        builder.add_node("analyze", self._analyze)
        builder.add_node("investigate", self._investigate)
        builder.add_node("finalize", self._finalize)
        builder.add_edge(START, "execute")
        builder.add_edge("execute", "analyze")
        builder.add_conditional_edges(
            "analyze",
            self._route_after_analysis,
            {"investigate": "investigate", "finalize": "finalize"},
        )
        builder.add_edge("investigate", "analyze")
        builder.add_edge("finalize", END)
        return builder.compile()


    async def _check_gns3(self, _state: NetworkWorkflowState,) -> dict:
        """Kiểm tra nhanh khả năng truy cập GNS3 trước khi lập kế hoạch."""

        # Bước 1: Kiểm tra GNS3 Controller trước khi tạo Task và gọi thiết bị.
        # Đây chỉ là health probe; lệnh thiết bị vẫn do NetworkAgent thực hiện.
        self._gns3_provider.check_server_available()
        return {}


    async def _plan(self, state: NetworkWorkflowState) -> dict:
        """Đọc Conversation và Message từ state để tạo Task có kế hoạch."""

        # Bước 2: Chuyển yêu cầu người dùng thành Task, operation và dependency.
        conversation = state.get("conversation")
        message = state.get("message")
        if conversation is None or message is None:
            raise ValueError("Workflow lập kế hoạch cần Conversation và Message")
        task = await self._planning.plan_user_message(conversation, message)
        return {"task": task}


    async def _execute(self, state: NetworkWorkflowState) -> dict:
        """Thực thi Task trong state và trả kết quả mạng cho node kế tiếp."""

        # Bước 3: Thực thi DAG; WRITE có thể dừng tại Approval Gate.
        task = state.get("task")
        if task is None:
            raise ValueError("Workflow thực thi cần Task")
        results = await self._execution.execute_task(task)
        return {"execution_results": results}


    async def _analyze(self, state: NetworkWorkflowState) -> dict:
        """Phân tích kết quả thực thi và tạo phản hồi cuối cho hội thoại."""

        # Bước 4: Analyst tổng hợp toàn bộ output thành kết luận có cấu trúc.
        task = state.get("task")
        if task is None:
            raise ValueError("Workflow phân tích cần Task")
        analysis = await self._analysis.analyze(
            task,
            state.get("execution_results", []),
        )
        return {"analysis": analysis}


    def _route_after_analysis(self, state: NetworkWorkflowState) -> str:
        """Quyết định kết luận hay mở rộng điều tra dựa trên evidence hiện có."""

        # Bước 5: Đánh giá confidence, root cause và khoảng trống bằng chứng.
        task = state.get("task")
        analysis = state.get("analysis")
        current_round = state.get("investigation_round", 0)
        if (
            task is None
            or analysis is None
            or task.task_type not in {TaskType.DIAGNOSIS, TaskType.COMPOSITE}
        ):
            return "finalize"
        needs_more_evidence = analysis.requires_more_data or (
            analysis.is_anomaly is not False
            and (
                not analysis.root_causes
                or analysis.confidence < self._diagnosis_confidence_threshold
            )
        )
        if (
            needs_more_evidence
            and analysis.suggested_checks
            and current_round < self._max_investigation_rounds
        ):
            return "investigate"
        return "finalize"


    async def _investigate(self, state: NetworkWorkflowState) -> dict:
        """Thực thi check READ-only do Analyst đề nghị và cộng dồn evidence."""

        # Bước 6: Chuyển suggested_checks thành operation READ-only và thực thi.
        task = state.get("task")
        analysis = state.get("analysis")
        if task is None or analysis is None:
            raise ValueError("Workflow điều tra cần Task và AnalysisResult")
        plan = self._analysis.build_investigation_plan(analysis)
        if plan is None:
            return {"investigation_round": self._max_investigation_rounds}
        additional = await self._execution.execute_investigation(task.id, plan)
        return {
            "task": self._execution.load_task_for_operation_device(
                additional[0].operation_device_id
            ) if additional else task,
            "execution_results": state.get("execution_results", []) + additional,
            "investigation_round": state.get("investigation_round", 0) + 1,
        }


    async def _finalize(self, state: NetworkWorkflowState) -> dict:
        """Tạo phản hồi cuối duy nhất sau khi đủ evidence hoặc đạt giới hạn vòng."""

        # Bước 7: Tạo FINAL_RESPONSE duy nhất sau khi kết thúc vòng điều tra.
        task = state.get("task")
        if task is None:
            raise ValueError("Workflow kết luận cần Task")
        response = self._analysis.finalize_response(task, state.get("analysis"))
        return {"response": response}


    async def run_message(self, conversation: Conversation, message: Message,) -> NetworkWorkflowState:
        """Chạy graph đầy đủ cho một message do người dùng gửi."""

        return await self._message_graph.ainvoke(
            {
                "conversation": conversation,
                "message": message,
                "execution_results": [],
                "investigation_round": 0,
            }
        )


    async def resume_after_approval(self, operation_device_id: str,) -> NetworkWorkflowState:
        """Tiếp tục từ node thực thi bằng Task đã được lưu trong PostgreSQL."""

        task = self._execution.load_task_for_operation_device(operation_device_id)
        return await self._approval_graph.ainvoke(
            {
                "task": task,
                "execution_results": [],
                "investigation_round": 0,
            }
        )


    def graph_mermaid(self) -> str:
        """Xuất sơ đồ Mermaid ổn định để làm tài liệu và chẩn đoán."""

        return self._message_graph.get_graph().draw_mermaid()
