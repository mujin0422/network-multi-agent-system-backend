"""LangGraph workflow for the end-to-end network automation lifecycle."""

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
    """State exchanged between LangGraph nodes.

    Business state remains persisted by the domain services in PostgreSQL.
    LangGraph owns the workflow transition state only, avoiding a second source
    of truth for Task, Operation and Approval lifecycle data.
    """

    conversation: NotRequired[Conversation]
    message: NotRequired[Message]
    task: NotRequired[TaskDetail]
    execution_results: NotRequired[list[NetworkExecutionResult]]
    response: NotRequired[Message | None]


class NetworkAutomationWorkflow:
    """Compiled LangGraph coordinating planning, execution and analysis."""

    def __init__(
        self,
        gns3_provider: GNS3Provider,
        planning: PlanningOrchestrator,
        execution: ExecutionOrchestrator,
        analysis: AnalysisOrchestrator,
    ) -> None:
        self._gns3_provider = gns3_provider
        self._planning = planning
        self._execution = execution
        self._analysis = analysis
        self._message_graph = self._build_message_graph()
        self._approval_graph = self._build_approval_graph()

    def _build_message_graph(self):
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
        # This is the same short availability probe used before LangGraph.
        # Device commands remain offloaded by NetworkAgent.
        self._gns3_provider.check_server_available()
        return {}

    async def _plan(self, state: NetworkWorkflowState) -> dict:
        conversation = state.get("conversation")
        message = state.get("message")
        if conversation is None or message is None:
            raise ValueError("Workflow lập kế hoạch cần Conversation và Message")
        task = await self._planning.plan_user_message(conversation, message)
        return {"task": task}

    async def _execute(self, state: NetworkWorkflowState) -> dict:
        task = state.get("task")
        if task is None:
            raise ValueError("Workflow thực thi cần Task")
        results = await self._execution.execute_task(task)
        return {"execution_results": results}

    async def _analyze(self, state: NetworkWorkflowState) -> dict:
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
        """Run the complete graph for one USER message."""

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
        """Enter the graph at execution using Task state persisted in PostgreSQL."""

        task = self._execution.load_task_for_operation_device(operation_device_id)
        return await self._approval_graph.ainvoke(
            {
                "task": task,
                "execution_results": [],
            }
        )

    def graph_mermaid(self) -> str:
        """Expose a deterministic diagram for documentation and diagnostics."""

        return self._message_graph.get_graph().draw_mermaid()
