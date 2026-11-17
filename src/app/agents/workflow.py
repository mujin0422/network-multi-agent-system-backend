"""Workflow LangGraph điều phối toàn bộ vòng đời tự động hóa mạng."""

from typing import Literal, NotRequired, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.analyst import AnalysisResult
from app.agents.network import NetworkExecutionResult
from app.agents.orchestrator import (
    AnalysisOrchestrator,
    ConfigurationOrchestrator,
    ExecutionOrchestrator,
    PlanningDraft,
    PlanningOrchestrator,
)
from app.diagnostics import EvidenceCoverage, get_playbook, select_playbooks
from app.domains.conversation.schemas import Conversation, Message
from app.domains.execution.schemas import ActivityActorType, TaskDetail, TaskType
from app.domains.inventory.providers import GNS3Provider


class NetworkWorkflowState(TypedDict):
    """Trạng thái được trao đổi giữa các node của LangGraph.

    Trạng thái nghiệp vụ vẫn do domain service lưu trong PostgreSQL. LangGraph
    chỉ quản lý dữ liệu chuyển tiếp giữa các node để không tạo thêm một nguồn
    dữ liệu cạnh tranh cho vòng đời Task, Operation và Approval.
    """

    entry_mode: Literal["message", "approval"]
    conversation: NotRequired[Conversation]
    message: NotRequired[Message]
    task: NotRequired[TaskDetail]
    planning_draft: NotRequired[PlanningDraft]
    execution_results: NotRequired[list[NetworkExecutionResult]]
    response: NotRequired[Message | None]
    analysis: NotRequired[AnalysisResult | None]
    investigation_round: NotRequired[int]
    playbook_keys: NotRequired[list[str]]
    evidence_coverage: NotRequired[EvidenceCoverage]
    evidence_stop_reason: NotRequired[str]


class NetworkAutomationWorkflow:
    """LangGraph đã biên dịch, điều phối lập kế hoạch, thực thi và phân tích."""

    def __init__(
        self,
        gns3_provider: GNS3Provider,
        planning: PlanningOrchestrator,
        configuration: ConfigurationOrchestrator,
        execution: ExecutionOrchestrator,
        analysis: AnalysisOrchestrator,
        max_investigation_rounds: int = 2,
        diagnosis_confidence_threshold: float = 0.8,
    ) -> None:
        """Khởi tạo dependency và biên dịch graph xử lý thống nhất."""

        self._gns3_provider = gns3_provider
        self._planning = planning
        self._configuration = configuration
        self._execution = execution
        self._analysis = analysis
        self._max_investigation_rounds = max_investigation_rounds
        self._diagnosis_confidence_threshold = diagnosis_confidence_threshold
        self._graph = self._build_graph()

    def _build_graph(self):
        """Tạo một graph có entry route cho message mới và approval resume."""

        # Bước 1: Khai báo một lần toàn bộ node được hai chế độ kích hoạt dùng chung.
        builder = StateGraph(NetworkWorkflowState)
        builder.add_node("check_gns3", self._check_gns3)
        builder.add_node("plan", self._plan)
        builder.add_node("configure", self._configure)
        builder.add_node("execute", self._execute)
        builder.add_node("analyze", self._analyze)
        builder.add_node("investigate", self._investigate)
        builder.add_node("finalize", self._finalize)

        # Bước 2: Message mới phải kiểm tra GNS3 và lập kế hoạch; approval resume
        # đi thẳng đến execute bằng Task đã được tải từ PostgreSQL.
        builder.add_conditional_edges(
            START,
            self._route_entry,
            {"message": "check_gns3", "approval": "execute"},
        )
        builder.add_edge("check_gns3", "plan")
        builder.add_conditional_edges(
            "plan",
            self._route_after_plan,
            {"configure": "configure", "execute": "execute"},
        )
        builder.add_edge("configure", "execute")
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

    @staticmethod
    async def _route_entry(state: NetworkWorkflowState) -> str:
        """Chọn điểm vào graph theo nguồn kích hoạt đã được backend xác định."""

        entry_mode = state.get("entry_mode")
        if entry_mode not in {"message", "approval"}:
            raise ValueError("Workflow cần entry_mode là 'message' hoặc 'approval'")
        return entry_mode


    async def _check_gns3(self, _state: NetworkWorkflowState) -> dict:
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
        draft = await self._planning.prepare_user_message(conversation, message)
        task = (
            draft.task
            if draft.requires_configuration
            else self._planning.persist_plan(draft)
        )
        message_text = getattr(message, "message", str(message))
        return {
            "task": task,
            "planning_draft": draft,
            "playbook_keys": [
                playbook.key for playbook in select_playbooks(message_text)
            ],
        }

    @staticmethod
    async def _route_after_plan(state: NetworkWorkflowState) -> str:
        """Chỉ đi qua node configure khi kế hoạch có Operation WRITE."""

        draft = state.get("planning_draft")
        if draft is None:
            raise ValueError("Workflow thiếu planning draft sau node plan")
        return "configure" if draft.requires_configuration else "execute"

    async def _configure(self, state: NetworkWorkflowState) -> dict:
        """Sinh CLI WRITE, kiểm tra kết quả và lưu kế hoạch hoàn chỉnh."""

        draft = state.get("planning_draft")
        if draft is None:
            raise ValueError("Workflow cấu hình cần planning draft")
        try:
            configured_plan = await self._configuration.configure_plan(
                draft.task.id,
                draft.plan,
                draft.devices,
                draft.interfaces_by_device_id,
            )
        except Exception as exc:
            self._planning.fail_task(
                draft.task,
                ActivityActorType.CONFIGURATION,
                "CONFIGURATION",
                exc,
            )
            raise
        task = self._planning.persist_plan(draft, configured_plan)
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
        playbook_keys = state.get("playbook_keys", [])
        coverage = self._analysis.evaluate_evidence_coverage(
            state.get("execution_results", []),
            playbook_keys,
        )
        analysis = await self._analysis.analyze(
            task,
            state.get("execution_results", []),
            evidence_coverage=coverage,
        )
        if analysis is not None:
            derived_keys = [
                playbook.key
                for cause in [*analysis.root_causes, *analysis.suspected_causes]
                if (playbook := get_playbook(cause.fault_type)) is not None
            ]
            playbook_keys = list(dict.fromkeys([*playbook_keys, *derived_keys]))
            coverage = self._analysis.evaluate_evidence_coverage(
                state.get("execution_results", []),
                playbook_keys,
            )
        return {
            "analysis": analysis,
            "evidence_coverage": coverage,
            "playbook_keys": playbook_keys,
        }


    async def _route_after_analysis(self, state: NetworkWorkflowState) -> str:
        """Quyết định kết luận hay mở rộng điều tra dựa trên evidence hiện có."""

        # Bước 5: Đánh giá confidence, root cause và khoảng trống bằng chứng.
        task = state.get("task")
        analysis = state.get("analysis")
        current_round = state.get("investigation_round", 0)
        coverage = state.get("evidence_coverage")
        if (
            task is None
            or analysis is None
            or task.task_type not in {TaskType.DIAGNOSIS, TaskType.COMPOSITE}
        ):
            return "finalize"
        # Root cause đã vượt qua Causal Evidence Gate và playbook evidence đã
        # đầy đủ thì kết luận ngay. Không để các khoảng trống phụ làm vòng sau
        # thay thế một RCA đã được xác nhận bằng suspected/unknown.
        if analysis.root_causes and coverage is not None and coverage.complete:
            return "finalize"
        playbook_incomplete = bool(
            coverage is not None and coverage.applicable and not coverage.complete
        )
        needs_more_evidence = (
            playbook_incomplete
            or analysis.requires_more_data
            or (
                analysis.is_anomaly is not False
                and (
                    not analysis.root_causes
                    or analysis.confidence < self._diagnosis_confidence_threshold
                )
            )
        )
        if (
            needs_more_evidence
            and (playbook_incomplete or bool(analysis.suggested_checks))
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
        coverage = state.get("evidence_coverage")
        plan = self._analysis.build_investigation_plan(
            analysis,
            playbook_keys=state.get("playbook_keys", []),
            missing_evidence=(coverage.missing if coverage is not None else []),
            execution_results=state.get("execution_results", []),
        )
        if plan is None:
            return {
                "investigation_round": self._max_investigation_rounds,
                "evidence_stop_reason": "NO_ADDITIONAL_CHECKS",
            }
        additional = await self._execution.execute_investigation(task.id, plan)
        return {
            "task": self._execution.load_task_for_operation_device(
                additional[0].operation_device_id
            )
            if additional
            else task,
            "execution_results": state.get("execution_results", []) + additional,
            "investigation_round": state.get("investigation_round", 0) + 1,
            "evidence_stop_reason": "INVESTIGATION_EXECUTED",
        }


    async def _finalize(self, state: NetworkWorkflowState) -> dict:
        """Tạo phản hồi cuối duy nhất sau khi đủ evidence hoặc đạt giới hạn vòng."""

        # Bước 7: Tạo FINAL_RESPONSE duy nhất sau khi kết thúc vòng điều tra.
        task = state.get("task")
        if task is None:
            raise ValueError("Workflow kết luận cần Task")
        coverage = state.get("evidence_coverage")
        stop_reason = state.get("evidence_stop_reason")
        if coverage is not None:
            if coverage.complete:
                stop_reason = "EVIDENCE_COMPLETE"
            elif (
                stop_reason != "NO_ADDITIONAL_CHECKS"
                and state.get("investigation_round", 0)
                >= self._max_investigation_rounds
            ):
                stop_reason = "MAX_ROUNDS_REACHED"
            self._analysis.record_evidence_gate(
                task.id,
                coverage,
                state.get("investigation_round", 0),
                stop_reason or "FINALIZED_WITHOUT_PLAYBOOK_GATE",
            )
        response = self._analysis.finalize_response(task, state.get("analysis"))
        return {"response": response}


    async def run_message(self, conversation: Conversation, message: Message) -> NetworkWorkflowState:
        """Chạy graph đầy đủ cho một message do người dùng gửi."""

        return await self._graph.ainvoke(
            {
                "entry_mode": "message",
                "conversation": conversation,
                "message": message,
                "execution_results": [],
                "investigation_round": 0,
                "playbook_keys": [],
            }
        )


    async def resume_after_approval(self, operation_device_id: str) -> NetworkWorkflowState:
        """Tiếp tục từ node thực thi bằng Task đã được lưu trong PostgreSQL."""

        task = self._execution.load_task_for_operation_device(operation_device_id)
        playbook_keys = [
            playbook.key
            for playbook in select_playbooks(getattr(task, "input_message", ""))
        ]
        return await self._graph.ainvoke(
            {
                "entry_mode": "approval",
                "task": task,
                "execution_results": [],
                "investigation_round": 0,
                "playbook_keys": playbook_keys,
            }
        )


    def graph_mermaid(self) -> str:
        """Xuất sơ đồ Mermaid ổn định để làm tài liệu và chẩn đoán."""
        return self._graph.get_graph().draw_mermaid()
