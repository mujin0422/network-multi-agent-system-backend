"""Public compatibility module for the execution orchestrator.

Implementation details live in ``execution_runtime`` so existing imports remain
stable while each execution concern can evolve independently.
"""

from app.agents.orchestrator.execution_runtime import ExecutionOrchestrator

__all__ = ["ExecutionOrchestrator"]
