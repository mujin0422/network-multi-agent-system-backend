"""Use cases điều phối benchmark_runs mà không lộ ground truth cho Agent/UI."""

from datetime import UTC, datetime

from app.domains.audit.transaction import audit_mutation, record_audit_in_session
from app.core.database import DatabaseUnitOfWork
from app.core.utils import IdPrefix, generate_id
from app.domains.benchmark.repositories import (
    BenchmarkRunRepositoryProtocol,
    BenchmarkScenarioRepositoryProtocol,
)
from app.domains.benchmark.schemas import (
    BenchmarkAction,
    BenchmarkCheck,
    BenchmarkRun,
    BenchmarkRunRecord,
    BenchmarkRunStatus,
    BenchmarkScenario,
)
from app.domains.benchmark.utils import (
    build_benchmark_action_commands,
    build_benchmark_evaluation,
    to_public_benchmark_run,
)
from app.domains.conversation.schemas import Conversation, Message, MessageType
from app.domains.evaluation.repositories import TaskEvaluationRepositoryProtocol
from app.domains.execution.schemas import AccessMode, TaskDetail
from app.tools import NetworkTool


class BenchmarkRunService:
    def __init__(
        self,
        run_repository: BenchmarkRunRepositoryProtocol,
        scenario_repository: BenchmarkScenarioRepositoryProtocol,
        evaluation_repository: TaskEvaluationRepositoryProtocol,
        network_tool: NetworkTool,
        uow: DatabaseUnitOfWork | None = None,
    ) -> None:
        """Khởi tạo BenchmarkRunService cùng các phụ thuộc cần thiết."""
        self._runs = run_repository
        self._scenarios = scenario_repository
        self._evaluations = evaluation_repository
        self._network_tool = network_tool
        self._uow = uow

    def list_runs(self, limit: int = 50) -> list[BenchmarkRun]:
        """Truy vấn danh sách dữ liệu theo phạm vi của phương thức list_runs."""
        return [to_public_benchmark_run(run) for run in self._runs.get_all(limit)]

    def get_run(self, run_id: str) -> BenchmarkRun:
        """Truy vấn dữ liệu theo phạm vi của phương thức get_run."""
        return to_public_benchmark_run(self._runs.get_by_id(run_id))

    def start(self, scenario_id: str, user_id: str) -> BenchmarkRun:
        """Tạo mới dữ liệu theo nghiệp vụ của phương thức start."""
        scenario = self._scenarios.get_by_id(scenario_id)
        if not scenario.is_active:
            raise ValueError("Benchmark scenario đang bị vô hiệu hóa")
        snapshot = BenchmarkScenario.model_validate(scenario.model_dump())
        now = datetime.now(UTC)
        run = BenchmarkRunRecord(
            id=generate_id(IdPrefix.BENCHMARK_RUN),
            scenario_id=scenario.id,
            scenario_version=scenario.version,
            scenario_name=scenario.name,
            status=BenchmarkRunStatus.PREPARING,
            started_by=user_id,
            initial_message=scenario.initial_message,
            started_at=now,
            scenario_snapshot=snapshot,
        )
        # Record the start request atomically BEFORE any network side effect.
        # SQL rollback cannot undo commands sent to physical network devices.
        if self._uow is None:
            with audit_mutation(
                "BENCHMARK_RUN_START", "BENCHMARK_RUN", run.id, actor_user_id=user_id
            ):
                self._runs.save(run)
        else:
            with self._uow.begin() as session:
                self._runs.save_in_session(session, run)
                record_audit_in_session(
                    session, action="BENCHMARK_RUN_START",
                    resource_type="BENCHMARK_RUN", resource_id=run.id,
                    actor_user_id=user_id,
                )
        injection_started = False
        try:
            self._execute_checks(scenario.preconditions)
            injection_started = True
            self._execute_actions(scenario.injection)
            self._execute_checks(scenario.fault_verification)
            run = run.model_copy(
                update={
                    "status": BenchmarkRunStatus.READY,
                    "cleanup_required": True,
                }
            )
        except Exception as exc:
            cleanup_error: str | None = None
            if injection_started:
                try:
                    self._execute_actions(scenario.cleanup)
                except Exception as cleanup_exc:
                    cleanup_error = str(cleanup_exc)
            run = run.model_copy(
                update={
                    "status": BenchmarkRunStatus.FAILED,
                    "error_message": (
                        f"{exc}; cleanup cũng thất bại: {cleanup_error}"
                        if cleanup_error
                        else str(exc)
                    ),
                    "cleanup_required": cleanup_error is not None,
                    "completed_at": datetime.now(UTC),
                }
            )
        # Runtime status is persisted separately after network execution.
        self._runs.save(run)
        return to_public_benchmark_run(run)

    def bind_message(
        self,
        run_id: str,
        conversation: Conversation,
        message: Message,
    ) -> None:
        """Xử lý trạng thái nghiệp vụ trong phương thức bind_message."""
        run = self._runs.get_by_id(run_id)
        if run.status != BenchmarkRunStatus.READY:
            raise ValueError("Benchmark run chưa sẵn sàng để bắt đầu Chat")
        self._runs.save(
            run.model_copy(
                update={
                    "status": BenchmarkRunStatus.RUNNING,
                    "conversation_id": conversation.id,
                    "source_message_id": message.id,
                }
            )
        )

    def complete(
        self,
        run_id: str,
        task: TaskDetail,
        response: Message | None,
    ) -> None:
        """Xử lý trạng thái nghiệp vụ trong phương thức complete."""
        run = self._runs.get_by_id(run_id)
        if run.status != BenchmarkRunStatus.RUNNING:
            return
        if response is None or response.message_type != MessageType.FINAL_RESPONSE:
            return
        now = datetime.now(UTC)
        evaluation, rca_result = build_benchmark_evaluation(
            run,
            task,
            response,
            now,
        )
        completed_run = run.model_copy(
            update={
                "status": BenchmarkRunStatus.COMPLETED,
                "task_id": task.id,
                "evaluation_id": str(evaluation.id),
                "evaluation_result": rca_result.value,
                "completed_at": now,
            }
        )
        if self._uow is None:
            # Compatibility with in-memory repositories in existing tests.
            self._evaluations.save(evaluation)
            self._runs.save(completed_run)
        else:
            # Never commit evaluation while leaving the run RUNNING, or vice versa.
            with self._uow.begin() as session:
                self._evaluations.save_in_session(session, evaluation)
                self._runs.save_in_session(session, completed_run)

    def complete_for_task(
        self,
        task: TaskDetail,
        response: Message | None,
    ) -> None:
        """Finalize a resumed benchmark only once a FINAL_RESPONSE is available.

        The benchmark run is linked by the source user message, including when
        the workflow pauses for approvals and resumes later in another request.
        """
        run = self._runs.get_by_source_message_id(task.source_message_id)
        if run is None or run.status != BenchmarkRunStatus.RUNNING:
            return
        if response is None or response.message_type != MessageType.FINAL_RESPONSE:
            return
        self.complete(run.id, task, response)

    def fail(self, run_id: str, error: Exception) -> None:
        """Xử lý trạng thái nghiệp vụ trong phương thức fail."""
        run = self._runs.get_by_id(run_id)
        self._runs.save(
            run.model_copy(
                update={
                    "status": BenchmarkRunStatus.FAILED,
                    "error_message": str(error),
                    "completed_at": datetime.now(UTC),
                }
            )
        )

    def cleanup(self, run_id: str) -> BenchmarkRun:
        """Kết thúc hoặc loại bỏ dữ liệu theo nghiệp vụ của phương thức cleanup."""
        run = self._runs.get_by_id(run_id)
        if run.cleanup_required:
            self._execute_actions(run.scenario_snapshot.cleanup)
        cleaned = run.model_copy(
            update={
                "status": BenchmarkRunStatus.CLEANED,
                "cleanup_required": False,
                "cleaned_at": datetime.now(UTC),
            }
        )
        if self._uow is None:
            with audit_mutation("BENCHMARK_RUN_CLEANUP", "BENCHMARK_RUN", cleaned.id):
                self._runs.save(cleaned)
        else:
            with self._uow.begin() as session:
                self._runs.save_in_session(session, cleaned)
                record_audit_in_session(
                    session, action="BENCHMARK_RUN_CLEANUP",
                    resource_type="BENCHMARK_RUN", resource_id=cleaned.id,
                )
        return to_public_benchmark_run(cleaned)

    def _execute_checks(self, checks: list[BenchmarkCheck]) -> None:
        """Thực thi tác vụ nội bộ của phương thức _execute_checks."""
        for check in checks:
            results = self._network_tool.execute(
                check.device,
                AccessMode.READ,
                [check.command],
            )
            output = "\n".join(result.output for result in results)
            expected = check.assertion.contains
            unexpected = check.assertion.not_contains
            if expected is not None and expected.casefold() not in output.casefold():
                raise RuntimeError(
                    f"Verification thất bại trên {check.device}: output không chứa "
                    f"'{expected}'"
                )
            if unexpected is not None and unexpected.casefold() in output.casefold():
                raise RuntimeError(
                    f"Verification thất bại trên {check.device}: output vẫn chứa "
                    f"'{unexpected}'"
                )

    def _execute_actions(self, actions: list[BenchmarkAction]) -> None:
        """Thực thi tác vụ nội bộ của phương thức _execute_actions."""
        for action in actions:
            self._network_tool.execute(
                action.device,
                AccessMode.WRITE,
                build_benchmark_action_commands(action),
            )
