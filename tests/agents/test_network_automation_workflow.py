"""Tests for LangGraph ownership of the end-to-end agent workflow."""

import asyncio

from app.agents.workflow import NetworkAutomationWorkflow


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
        return {"task_id": "task-1"}


class StubExecution:
    def __init__(self, calls):
        self.calls = calls

    async def execute_task(self, task):
        self.calls.append("execute")
        return [{"task": task, "status": "SUCCESS"}]

    def load_task_for_operation_device(self, operation_device_id):
        self.calls.append(f"load:{operation_device_id}")
        return {"task_id": "task-resumed"}


class StubAnalysis:
    def __init__(self, calls):
        self.calls = calls

    async def analyze_and_respond(self, task, results):
        self.calls.append("analyze")
        return {"task": task, "result_count": len(results)}


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
    assert state["task"] == {"task_id": "task-1"}
    assert state["response"]["result_count"] == 1


def test_approval_entrypoint_resumes_at_execution_node() -> None:
    calls = []
    workflow = build_workflow(calls)

    state = asyncio.run(workflow.resume_after_approval("opdv-1"))

    assert calls == ["load:opdv-1", "execute", "analyze"]
    assert state["task"] == {"task_id": "task-resumed"}


def test_workflow_exposes_langgraph_diagram() -> None:
    diagram = build_workflow([]).graph_mermaid()

    assert "check_gns3" in diagram
    assert "plan" in diagram
    assert "execute" in diagram
    assert "analyze" in diagram
