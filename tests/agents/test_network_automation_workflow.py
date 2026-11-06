"""Tests for LangGraph ownership of the end-to-end agent workflow."""

import asyncio
from types import SimpleNamespace

from app.agents.analyst import AnalysisResult
from app.agents.workflow import NetworkAutomationWorkflow
from app.diagnostics import EvidenceCoverage, EvidenceType
from app.domains.execution.schemas import TaskType


class StubGNS3Provider:
    def __init__(self, calls):
        self.calls = calls

    def check_server_available(self):
        self.calls.append("check_gns3")
        return {"version": "test"}


class StubPlanning:
    def __init__(self, calls):
        self.calls = calls

    async def plan_user_message(self, conversation, message):
        self.calls.append("plan")
        return SimpleNamespace(id="task-1", task_type=TaskType.DIAGNOSIS)


class StubExecution:
    def __init__(self, calls):
        self.calls = calls

    async def execute_task(self, task):
        self.calls.append("execute")
        return [{"task": task, "status": "SUCCESS"}]

    def load_task_for_operation_device(self, operation_device_id):
        self.calls.append(f"load:{operation_device_id}")
        return SimpleNamespace(id="task-resumed", task_type=TaskType.DIAGNOSIS)

    async def execute_investigation(self, task_id, plan):
        self.calls.append("investigate")
        return []


class StubAnalysis:
    def __init__(self, calls):
        self.calls = calls

    async def analyze(self, task, results, evidence_coverage=None):
        self.calls.append("analyze")
        return AnalysisResult(
            summary="Không phát hiện bất thường.",
            is_anomaly=False,
            confidence=1.0,
        )

    def build_investigation_plan(self, analysis, **kwargs):
        return object()

    def evaluate_evidence_coverage(self, results, playbook_keys):
        return EvidenceCoverage(
            applicable=False,
            playbook_keys=[],
            required=[],
            observed=[],
            missing=[],
            coverage=1.0,
        )

    def record_evidence_gate(self, task_id, coverage, investigation_round, stop_reason):
        pass

    def finalize_response(self, task, analysis):
        return {"task": task, "result_count": 1}


def build_workflow(calls):
    return NetworkAutomationWorkflow(
        StubGNS3Provider(calls),
        StubPlanning(calls),
        StubExecution(calls),
        StubAnalysis(calls),
    )


def test_message_entrypoint_runs_all_langgraph_nodes_in_order() -> None:
    calls = []
    workflow = build_workflow(calls)

    state = asyncio.run(workflow.run_message("conversation", "message"))

    assert calls == ["check_gns3", "plan", "execute", "analyze"]
    assert state["task"].id == "task-1"
    assert state["response"]["result_count"] == 1


def test_approval_entrypoint_resumes_at_execution_node() -> None:
    calls = []
    workflow = build_workflow(calls)

    state = asyncio.run(workflow.resume_after_approval("opdv-1"))

    assert calls == ["load:opdv-1", "execute", "analyze"]
    assert state["task"].id == "task-resumed"


def test_workflow_exposes_langgraph_diagram() -> None:
    diagram = build_workflow([]).graph_mermaid()

    assert "check_gns3" in diagram
    assert "plan" in diagram
    assert "execute" in diagram
    assert "analyze" in diagram
    assert "investigate" in diagram
    assert "finalize" in diagram


def test_workflow_collects_more_evidence_before_finalizing() -> None:
    calls = []

    class IterativeAnalysis(StubAnalysis):
        def __init__(self, calls):
            super().__init__(calls)
            self.round = 0

        async def analyze(self, task, results, evidence_coverage=None):
            self.calls.append("analyze")
            self.round += 1
            if self.round == 1:
                return AnalysisResult(
                    summary="Chưa đủ bằng chứng.",
                    requires_more_data=True,
                    evidence_gaps=["Thiếu trạng thái thiết bị đối diện"],
                    suggested_checks=[
                        {
                            "device": "P2",
                            "commands": ["show ip ospf neighbor"],
                            "reason": "Đối chiếu adjacency ở đầu bên kia",
                        }
                    ],
                )
            return AnalysisResult(
                summary="Đã đủ bằng chứng.",
                is_anomaly=True,
                confidence=0.9,
                root_causes=[
                    {
                        "device": "P1",
                        "interface": None,
                        "fault_type": "ospf_network_missing",
                    }
                ],
            )

    workflow = NetworkAutomationWorkflow(
        StubGNS3Provider(calls),
        StubPlanning(calls),
        StubExecution(calls),
        IterativeAnalysis(calls),
        max_investigation_rounds=2,
    )

    state = asyncio.run(workflow.run_message("conversation", "message"))

    assert calls == [
        "check_gns3",
        "plan",
        "execute",
        "analyze",
        "investigate",
        "analyze",
    ]
    assert state["investigation_round"] == 1
    assert state["analysis"].confidence == 0.9


def test_workflow_blocks_finalize_until_playbook_evidence_is_complete() -> None:
    calls = []

    class GateAnalysis(StubAnalysis):
        def __init__(self, calls):
            super().__init__(calls)
            self.coverage_checks = 0
            self.gate_record = None

        def evaluate_evidence_coverage(self, results, playbook_keys):
            self.coverage_checks += 1
            missing = (
                [EvidenceType.INTERFACE_CONFIG]
                if self.coverage_checks <= 2
                else []
            )
            return EvidenceCoverage(
                applicable=True,
                playbook_keys=["mpls_disabled"],
                required=[
                    EvidenceType.INTERFACE_STATUS,
                    EvidenceType.INTERFACE_CONFIG,
                    EvidenceType.MPLS_INTERFACE,
                ],
                observed=(
                    [EvidenceType.INTERFACE_STATUS, EvidenceType.MPLS_INTERFACE]
                    if missing
                    else [
                        EvidenceType.INTERFACE_STATUS,
                        EvidenceType.INTERFACE_CONFIG,
                        EvidenceType.MPLS_INTERFACE,
                    ]
                ),
                missing=missing,
                coverage=2 / 3 if missing else 1.0,
            )

        def record_evidence_gate(
            self, task_id, coverage, investigation_round, stop_reason
        ):
            self.gate_record = (coverage.coverage, investigation_round, stop_reason)

    analysis = GateAnalysis(calls)
    workflow = NetworkAutomationWorkflow(
        StubGNS3Provider(calls),
        StubPlanning(calls),
        StubExecution(calls),
        analysis,
        max_investigation_rounds=2,
    )

    state = asyncio.run(
        workflow.run_message(
            "conversation",
            SimpleNamespace(message="Chẩn đoán MPLS trên P1"),
        )
    )

    assert calls == [
        "check_gns3",
        "plan",
        "execute",
        "analyze",
        "investigate",
        "analyze",
    ]
    assert state["evidence_coverage"].complete is True
    assert analysis.gate_record == (1.0, 1, "EVIDENCE_COMPLETE")
