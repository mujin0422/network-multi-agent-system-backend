#!/usr/bin/env python3
"""Chạy tuần tự các Benchmark Scenario qua API để tạo dữ liệu đánh giá đầy đủ."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from sqlalchemy import select

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from app.core.database import create_session_factory  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.domains.audit.models.audit_log import AuditLogModel  # noqa: E402
from app.domains.benchmark.models import BenchmarkRunModel  # noqa: E402
from app.domains.conversation.models import (  # noqa: E402
    ConversationModel,
    MessageModel,
)
from app.domains.evaluation.models import (  # noqa: E402
    TaskEvaluationMetricModel,
    TaskEvaluationModel,
)
from app.domains.execution.models import (  # noqa: E402
    DeviceActionLogModel,
    OperationDependencyModel,
    OperationDeviceApprovalModel,
    OperationModel,
    TaskActivityEventModel,
    TaskExecutionModel,
    TaskModel,
    TaskOperationDeviceModel,
)


TERMINAL_RUN_STATUSES = {"COMPLETED", "FAILED", "CLEANED"}
DEFAULT_TIMEZONE = "Asia/Ho_Chi_Minh"


class RunnerError(RuntimeError):
    """Lỗi có ngữ cảnh rõ ràng để runner báo ra command line."""


class CleanupError(RunnerError):
    """Cleanup không thể xác nhận; runner phải dừng để tránh nhiễm scenario."""


@dataclass(frozen=True)
class RunnerConfig:
    api_url: str
    email: str
    password: str
    run_date: date
    timezone: ZoneInfo
    scenario_ids: frozenset[str]
    approve_writes: bool
    force: bool
    poll_seconds: float
    timeout_seconds: float
    request_timeout_seconds: float
    cooldown_seconds: float
    cleanup_retries: int
    cleanup_retry_delay_seconds: float
    database_url: str


class ApiClient:
    """HTTP client nhỏ dùng thư viện chuẩn để script không cần dependency mới."""

    def __init__(self, base_url: str, request_timeout: float) -> None:
        self._base_url = base_url.rstrip("/")
        self._request_timeout = request_timeout
        self._access_token: str | None = None
        self._refresh_token: str | None = None

    def login(self, email: str, password: str) -> None:
        """Đăng nhập và lưu access token cho các request tiếp theo."""

        response = self.request(
            "POST",
            "/api/v1/auth/login",
            {"email": email, "password": password},
            authenticated=False,
        )
        token = response.get("access_token")
        if not isinstance(token, str) or not token:
            raise RunnerError("API đăng nhập không trả access_token")
        self._access_token = token
        self._refresh_token = response.get("refresh_token")

    def request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        query: dict[str, Any] | None = None,
        authenticated: bool = True,
        retry_auth: bool = True,
    ) -> Any:
        """Gửi JSON request và chuyển lỗi HTTP thành RunnerError dễ đọc."""

        url = f"{self._base_url}{path}"
        if query:
            url = f"{url}?{urlencode(query)}"
        headers = {"Accept": "application/json"}
        if authenticated:
            if self._access_token is None:
                raise RunnerError("Chưa đăng nhập API")
            headers["Authorization"] = f"Bearer {self._access_token}"
        body = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(payload).encode("utf-8")
        request = Request(url, data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=self._request_timeout) as response:
                content = response.read()
                return json.loads(content) if content else None
        except HTTPError as exc:
            if exc.code == 401 and authenticated and retry_auth:
                self._refresh_access_token()
                return self.request(
                    method,
                    path,
                    payload,
                    query=query,
                    authenticated=True,
                    retry_auth=False,
                )
            detail = exc.read().decode("utf-8", errors="replace")
            raise RunnerError(
                f"{method} {path} thất bại ({exc.code}): {detail}"
            ) from exc
        except URLError as exc:
            raise RunnerError(f"Không kết nối được API {self._base_url}: {exc}") from exc

    def _refresh_access_token(self) -> None:
        """Xoay token để runner dài hạn không bị dừng khi access token hết hạn."""

        if not self._refresh_token:
            raise RunnerError("Access token hết hạn và không có refresh token")
        response = self.request(
            "POST",
            "/api/v1/auth/refresh",
            {"refresh_token": self._refresh_token},
            authenticated=False,
        )
        access_token = response.get("access_token")
        refresh_token = response.get("refresh_token")
        if not access_token or not refresh_token:
            raise RunnerError("Không thể xoay token cho runner")
        self._access_token = access_token
        self._refresh_token = refresh_token


class BenchmarkTimestampBackfiller:
    """Dịch đồng bộ timestamp của toàn bộ record thuộc một Benchmark Run."""

    def __init__(self, database_url: str, timezone: ZoneInfo) -> None:
        self._sessions = create_session_factory(database_url)
        self._timezone = timezone

    def shift_to_date(self, run_id: str, target_date: date) -> None:
        """Đưa ngày bắt đầu run về target_date và giữ nguyên mọi khoảng thời gian."""

        with self._sessions.begin() as session:
            run = session.get(BenchmarkRunModel, run_id, with_for_update=True)
            if run is None:
                raise RunnerError(f"Không tìm thấy Benchmark Run {run_id} để backfill")
            source_started_at = self._aware(run.started_at)
            local_started_at = source_started_at.astimezone(self._timezone)
            target_started_at = local_started_at.replace(
                year=target_date.year,
                month=target_date.month,
                day=target_date.day,
            )
            delta = target_started_at.astimezone(UTC) - source_started_at.astimezone(UTC)
            if delta == timedelta(0):
                return

            conversation = (
                session.get(ConversationModel, run.conversation_id)
                if run.conversation_id
                else None
            )
            task = session.get(TaskModel, run.task_id) if run.task_id else None
            if task is None and run.source_message_id:
                task = session.scalar(
                    select(TaskModel).where(
                        TaskModel.source_message_id == run.source_message_id
                    )
                )
            task_id = task.id if task is not None else None
            evaluation = (
                session.get(TaskEvaluationModel, run.evaluation_id)
                if run.evaluation_id
                else None
            )
            if evaluation is None and task_id:
                evaluation = session.scalar(
                    select(TaskEvaluationModel).where(
                        TaskEvaluationModel.task_id == task_id
                    )
                )

            messages = (
                list(
                    session.scalars(
                        select(MessageModel).where(
                            MessageModel.conversation_id == run.conversation_id
                        )
                    )
                )
                if run.conversation_id
                else []
            )
            operations = (
                list(
                    session.scalars(
                        select(OperationModel).where(OperationModel.task_id == task_id)
                    )
                )
                if task_id
                else []
            )
            operation_ids = [operation.id for operation in operations]
            mappings = (
                list(
                    session.scalars(
                        select(TaskOperationDeviceModel).where(
                            TaskOperationDeviceModel.operation_id.in_(operation_ids)
                        )
                    )
                )
                if operation_ids
                else []
            )
            mapping_ids = [mapping.id for mapping in mappings]
            dependencies = (
                list(
                    session.scalars(
                        select(OperationDependencyModel).where(
                            OperationDependencyModel.operation_id.in_(operation_ids)
                        )
                    )
                )
                if operation_ids
                else []
            )
            executions = (
                list(
                    session.scalars(
                        select(TaskExecutionModel).where(
                            TaskExecutionModel.task_id == task_id
                        )
                    )
                )
                if task_id
                else []
            )
            action_logs = (
                list(
                    session.scalars(
                        select(DeviceActionLogModel).where(
                            DeviceActionLogModel.task_id == task_id
                        )
                    )
                )
                if task_id
                else []
            )
            activity_events = (
                list(
                    session.scalars(
                        select(TaskActivityEventModel).where(
                            TaskActivityEventModel.task_id == task_id
                        )
                    )
                )
                if task_id
                else []
            )
            approvals = (
                list(
                    session.scalars(
                        select(OperationDeviceApprovalModel).where(
                            OperationDeviceApprovalModel.operation_device_id.in_(
                                mapping_ids
                            )
                        )
                    )
                )
                if mapping_ids
                else []
            )
            metrics = (
                list(
                    session.scalars(
                        select(TaskEvaluationMetricModel).where(
                            TaskEvaluationMetricModel.evaluation_id == evaluation.id
                        )
                    )
                )
                if evaluation is not None
                else []
            )

            resource_ids = {
                run.id,
                *(message.id for message in messages),
                *(operation.id for operation in operations),
                *(mapping.id for mapping in mappings),
                *(execution.id for execution in executions),
                *(approval.id for approval in approvals),
            }
            if run.conversation_id:
                resource_ids.add(run.conversation_id)
            if task_id:
                resource_ids.add(task_id)
            if evaluation is not None:
                resource_ids.add(str(evaluation.id))
            audit_logs = list(
                session.scalars(
                    select(AuditLogModel).where(
                        AuditLogModel.resource_id.in_(resource_ids)
                    )
                )
            )

            self._shift(run, delta, "started_at", "completed_at", "cleaned_at")
            self._shift(conversation, delta, "created_at", "last_updated_at")
            self._shift(task, delta, "created_at", "started_at", "completed_at")
            self._shift(evaluation, delta, "created_at", "evaluated_at")
            for message in messages:
                self._shift(message, delta, "created_at")
            for operation in operations:
                self._shift(operation, delta, "created_at", "started_at", "completed_at")
            for mapping in mappings:
                self._shift(mapping, delta, "started_at", "completed_at")
            for dependency in dependencies:
                self._shift(dependency, delta, "created_at")
            for execution in executions:
                self._shift(execution, delta, "created_at", "started_at", "completed_at")
            for action_log in action_logs:
                self._shift(action_log, delta, "executed_at")
            for event in activity_events:
                self._shift(event, delta, "created_at", "started_at", "completed_at")
            for approval in approvals:
                self._shift(
                    approval,
                    delta,
                    "created_at",
                    "requested_at",
                    "decided_at",
                    "expires_at",
                )
            for metric in metrics:
                self._shift(metric, delta, "created_at")
            for audit_log in audit_logs:
                self._shift(audit_log, delta, "occurred_at")

        print(
            f"Run {run_id}: backfilled về {target_date.isoformat()} "
            f"({delta.total_seconds() / 86400:g} ngày)."
        )

    @staticmethod
    def _aware(value: datetime) -> datetime:
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)

    @staticmethod
    def _shift(model: object | None, delta: timedelta, *fields: str) -> None:
        if model is None:
            return
        for field in fields:
            value = getattr(model, field, None)
            if value is not None:
                setattr(model, field, value + delta)


class BenchmarkScenarioRunner:
    """Điều phối các API để mỗi scenario tạo đủ run, task và evaluation."""

    def __init__(
        self,
        client: ApiClient,
        backfiller: BenchmarkTimestampBackfiller,
        config: RunnerConfig,
    ) -> None:
        self._client = client
        self._backfiller = backfiller
        self._config = config

    def run(self) -> int:
        """Chạy các scenario được chọn và trả exit code cho cron/CI."""

        # Bước 1: Đăng nhập và xử lý mọi cleanup còn treo trước khi tiêm fault mới.
        self._client.login(self._config.email, self._config.password)
        self._recover_pending_cleanups()
        # Bước 2: Lọc scenario active và bỏ qua kết quả đã hoàn thành trong ngày.
        scenarios = self._get_selected_scenarios()
        completed_scenario_ids = self._get_completed_scenario_ids_for_date()
        pending = [
            scenario
            for scenario in scenarios
            if self._config.force or scenario["id"] not in completed_scenario_ids
        ]
        skipped = len(scenarios) - len(pending)
        print(
            f"Ngày {self._config.run_date.isoformat()}: "
            f"{len(pending)} scenario cần chạy, {skipped} scenario đã bỏ qua."
        )

        failures = 0
        attempted = 0
        aborted = False
        # Bước 3: Chạy tuần tự để các fault không chồng chéo trên cùng topology.
        for index, scenario in enumerate(pending, start=1):
            attempted += 1
            print(f"\n[{index}/{len(pending)}] {scenario['name']} ({scenario['id']})")
            try:
                self._run_scenario(scenario)
            except CleanupError as exc:
                # Bước 4: Dừng toàn bộ nếu không chứng minh được lab đã phục hồi.
                failures += 1
                aborted = True
                print(f"ABORTED: {exc}", file=sys.stderr)
            except Exception as exc:
                failures += 1
                print(f"FAILED: {exc}", file=sys.stderr)
            finally:
                # Bước 5: Cooldown giúp console/protocol hội tụ trước scenario sau.
                if (
                    not aborted
                    and index < len(pending)
                    and self._config.cooldown_seconds > 0
                ):
                    print(
                        f"Cooldown {self._config.cooldown_seconds:g}s "
                        "trước scenario tiếp theo..."
                    )
                    time.sleep(self._config.cooldown_seconds)
            if aborted:
                break

        # Bước 6: Báo riêng số đã chạy, thất bại, bỏ qua và chưa chạy.
        print(
            f"\nHoàn tất: {attempted - failures} thành công, "
            f"{failures} thất bại, {skipped} bỏ qua, "
            f"{len(pending) - attempted} chưa chạy."
        )
        return 1 if failures else 0

    def _get_selected_scenarios(self) -> list[dict[str, Any]]:
        scenarios = self._client.request("GET", "/api/v1/benchmarks/scenarios")
        selected = [
            scenario
            for scenario in scenarios
            if scenario.get("is_active", True)
            and (
                not self._config.scenario_ids
                or scenario.get("id") in self._config.scenario_ids
            )
        ]
        found_ids = {scenario["id"] for scenario in selected}
        missing_ids = self._config.scenario_ids - found_ids
        if missing_ids:
            raise RunnerError(
                "Không tìm thấy scenario active: " + ", ".join(sorted(missing_ids))
            )
        return selected

    def _get_completed_scenario_ids_for_date(self) -> set[str]:
        runs = self._get_all_runs()
        return {
            run["scenario_id"]
            for run in runs
            if self._date_of(run.get("started_at")) == self._config.run_date
            and self._is_successful_run(run)
        }

    def _get_all_runs(self) -> list[dict[str, Any]]:
        """Đọc toàn bộ lịch sử run theo trang, không bỏ sót sau bản ghi thứ 100."""

        page = 1
        runs: list[dict[str, Any]] = []
        while True:
            result = self._client.request(
                "GET",
                "/api/v1/benchmarks/runs/page",
                query={"page": page, "page_size": 100},
            )
            runs.extend(result.get("items", []))
            if page >= int(result.get("total_pages", 0)):
                return runs
            page += 1

    def _date_of(self, raw_value: object) -> date | None:
        if not isinstance(raw_value, str):
            return None
        timestamp = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
        return timestamp.astimezone(self._config.timezone).date()

    def _run_scenario(self, scenario: dict[str, Any]) -> None:
        # Bước 1: Tạo Run; API thực hiện precondition, injection và fault verification.
        run = self._client.request(
            "POST",
            "/api/v1/benchmarks/runs",
            {"scenario_id": scenario["id"]},
        )
        run_id = run["id"]
        try:
            print(f"Run {run_id}: {run['status']}")
            if run["status"] != "READY":
                raise RunnerError(
                    run.get("error_message") or "Fault injection thất bại"
                )
            # Bước 2: Gửi initial_message qua đúng luồng Chat của ứng dụng.
            self._client.request(
                "POST",
                "/api/v1/conversations/messages",
                {
                    "message": run["initial_message"],
                    "benchmark_run_id": run_id,
                },
            )
            # Bước 3: Poll tiến trình và tự phê duyệt WRITE khi được cho phép.
            run = self._wait_for_terminal_run(run_id)
            task_id = run.get("task_id") or self._find_task_id(
                run.get("source_message_id")
            )
            if not self._is_successful_run(run):
                raise RunnerError(
                    run.get("error_message") or "Benchmark workflow thất bại"
                )
            if not task_id:
                raise RunnerError("Run hoàn tất nhưng không có Task liên kết")

            # Bước 4: Xác nhận đủ Conversation, Task, Execution và Evaluation.
            self._verify_related_records(run, task_id)
            result = run.get("evaluation_result") or "UNKNOWN"
            print(f"Run {run_id}: COMPLETED, evaluation={result}, task={task_id}")
        finally:
            # Bước 5: Luôn cleanup, kể cả workflow hoặc bước xác minh bị lỗi.
            latest_run = self._client.request(
                "GET",
                f"/api/v1/benchmarks/runs/{run_id}",
            )
            try:
                self._cleanup_if_needed(latest_run)
            finally:
                # Bước 6: Chỉ sau cleanup mới backfill đồng bộ timestamp.
                self._backfiller.shift_to_date(run_id, self._config.run_date)

    @staticmethod
    def _is_successful_run(run: dict[str, Any]) -> bool:
        """Phân biệt run hoàn tất thật với run lỗi đã được Cleanup."""

        return run.get("status") == "COMPLETED" or (
            run.get("status") == "CLEANED" and bool(run.get("evaluation_id"))
        )

    def _wait_for_terminal_run(self, run_id: str) -> dict[str, Any]:
        # Bước 1: Giới hạn thời gian chờ để cron không treo vô hạn.
        deadline = time.monotonic() + self._config.timeout_seconds
        approved_ids: set[str] = set()
        while time.monotonic() < deadline:
            run = self._client.request("GET", f"/api/v1/benchmarks/runs/{run_id}")
            # Bước 2: Trả về ngay khi run đã COMPLETED, FAILED hoặc CLEANED.
            if run["status"] in TERMINAL_RUN_STATUSES:
                return run
            task_id = run.get("task_id") or self._find_task_id(
                run.get("source_message_id")
            )
            # Bước 3: Xử lý approval đang chờ rồi tiếp tục polling.
            if task_id:
                self._approve_pending_requests(task_id, approved_ids)
            time.sleep(self._config.poll_seconds)
        raise RunnerError(
            f"Run {run_id} quá thời gian chờ {self._config.timeout_seconds:g}s"
        )

    def _find_task_id(self, source_message_id: object) -> str | None:
        if not isinstance(source_message_id, str) or not source_message_id:
            return None
        tasks = self._client.request("GET", "/api/v1/tasks/")
        task = next(
            (item for item in tasks if item.get("source_message_id") == source_message_id),
            None,
        )
        return task.get("id") if task else None

    def _approve_pending_requests(
        self,
        task_id: str,
        approved_ids: set[str],
    ) -> None:
        records = self._client.request("GET", f"/api/v1/tasks/{task_id}/records")
        pending = [
            approval
            for approval in records.get("approvals", [])
            if approval.get("approval_status") == "PENDING"
            and approval.get("id") not in approved_ids
        ]
        if pending and not self._config.approve_writes:
            raise RunnerError(
                "Workflow cần approval. Chạy lại với --approve-writes trong lab."
            )
        for approval in pending:
            self._client.request(
                "POST",
                f"/api/v1/operation-device-approvals/{approval['id']}/decision",
                {"decision": "APPROVED"},
            )
            approved_ids.add(approval["id"])
            print(f"Approval {approval['id']}: APPROVED")

    def _verify_related_records(self, run: dict[str, Any], task_id: str) -> None:
        conversation_id = run.get("conversation_id")
        if not conversation_id:
            raise RunnerError("Run không có Conversation liên kết")
        conversation = self._client.request(
            "GET",
            f"/api/v1/conversations/{conversation_id}",
        )
        messages = conversation.get("messages", [])
        if not messages:
            raise RunnerError("Conversation không có Message")
        if not any(
            message.get("message_type") == "FINAL_RESPONSE" for message in messages
        ):
            raise RunnerError("Conversation chưa có FINAL_RESPONSE")
        records = self._client.request("GET", f"/api/v1/tasks/{task_id}/records")
        if not records.get("task") or not records["task"].get("operations"):
            raise RunnerError("Task chưa có execution plan/operations")
        if not records.get("operation_devices"):
            raise RunnerError("Task chưa có operation-device mappings")
        if not records.get("executions"):
            raise RunnerError("Task chưa có Agent execution records")
        if not records.get("activity_events"):
            raise RunnerError("Task chưa có activity timeline")
        evaluation = self._client.request(
            "GET",
            f"/api/v1/evaluations/tasks/{task_id}",
        )
        if not evaluation or not evaluation.get("metrics"):
            raise RunnerError("Task chưa có Evaluation hoặc Evaluation Metrics")

    def _cleanup_if_needed(self, run: dict[str, Any]) -> None:
        # Bước 1: Không gọi API dư thừa nếu run đã được cleanup.
        if not run.get("cleanup_required"):
            return
        last_error: Exception | None = None
        attempts = self._config.cleanup_retries + 1
        for attempt in range(1, attempts + 1):
            try:
                # Bước 2: Backend tự WRITE/retry/READ-verify trạng thái thiết bị.
                cleaned = self._client.request(
                    "POST",
                    f"/api/v1/benchmarks/runs/{run['id']}/cleanup",
                )
                if cleaned.get("cleanup_required"):
                    raise RunnerError("API vẫn báo cleanup_required=true")
                print(f"Run {run['id']}: {cleaned['status']}")
                return
            except Exception as error:
                # Bước 3: Retry request để vượt qua lỗi HTTP/console tạm thời.
                last_error = error
                if attempt < attempts:
                    print(
                        f"Cleanup {run['id']} thất bại lần {attempt}/{attempts}; "
                        "sẽ thử lại bằng request mới...",
                        file=sys.stderr,
                    )
                    time.sleep(self._config.cleanup_retry_delay_seconds)
        # Bước 4: Hết retry phải abort runner, không chạy scenario kế tiếp.
        raise CleanupError(
            f"Run {run['id']} không cleanup được sau {attempts} lần; "
            "dừng runner để bảo vệ trạng thái lab: "
            f"{last_error}"
        ) from last_error

    def _recover_pending_cleanups(self) -> None:
        """Khôi phục cleanup còn treo trước khi tiêm fault mới vào topology."""

        # Bước 1: Đọc các run gần nhất để tìm fault chưa được hoàn nguyên.
        runs = self._get_all_runs()
        pending = [run for run in runs if run.get("cleanup_required")]
        # Bước 2: Cleanup lần lượt; bất kỳ lỗi nào cũng chặn phiên benchmark mới.
        for run in pending:
            print(f"Phát hiện cleanup còn treo của run {run['id']}; đang khôi phục...")
            self._cleanup_if_needed(run)


def parse_args() -> RunnerConfig:
    parser = argparse.ArgumentParser(
        description="Chạy Benchmark Scenario qua API và lưu dữ liệu thống kê đầy đủ.",
    )
    parser.add_argument("--date", required=True, help="Ngày chạy YYYY-MM-DD.")
    parser.add_argument(
        "--api-url",
        default=os.getenv("BENCHMARK_API_URL", "http://localhost:8000"),
    )
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL") or get_settings().database_url,
        help="Database dùng để backfill toàn bộ timestamp liên quan.",
    )
    parser.add_argument("--email", default=os.getenv("BENCHMARK_EMAIL"))
    parser.add_argument("--password", default=os.getenv("BENCHMARK_PASSWORD"))
    parser.add_argument(
        "--timezone",
        default=os.getenv("BENCHMARK_TIMEZONE", DEFAULT_TIMEZONE),
    )
    parser.add_argument(
        "--scenario",
        action="append",
        default=[],
        help="Scenario ID cần chạy; có thể truyền nhiều lần. Mặc định chạy tất cả active.",
    )
    parser.add_argument(
        "--approve-writes",
        action="store_true",
        help="Tự phê duyệt WRITE của Task thuộc run hiện tại. Chỉ dùng trong lab.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Chạy lại dù scenario đã có kết quả thành công trong ngày.",
    )
    parser.add_argument("--poll-seconds", type=float, default=3.0)
    parser.add_argument("--timeout-seconds", type=float, default=900.0)
    parser.add_argument("--request-timeout-seconds", type=float, default=180.0)
    parser.add_argument("--cooldown-seconds", type=float, default=15.0)
    parser.add_argument("--cleanup-retries", type=int, default=2)
    parser.add_argument("--cleanup-retry-delay-seconds", type=float, default=3.0)
    args = parser.parse_args()
    if not args.email or not args.password:
        parser.error("Cần --email/--password hoặc BENCHMARK_EMAIL/BENCHMARK_PASSWORD")
    try:
        run_date = date.fromisoformat(args.date)
        timezone = ZoneInfo(args.timezone)
    except (ValueError, KeyError) as exc:
        parser.error(str(exc))
    today = datetime.now(timezone).date()
    if run_date > today:
        parser.error("--date không được nằm trong tương lai")
    if (
        args.poll_seconds <= 0
        or args.timeout_seconds <= 0
        or args.request_timeout_seconds <= 0
        or args.cooldown_seconds < 0
        or args.cleanup_retries < 0
        or args.cleanup_retry_delay_seconds < 0
    ):
        parser.error(
            "Các giá trị timeout/poll phải lớn hơn 0 và cooldown không được âm"
        )
    return RunnerConfig(
        api_url=args.api_url,
        email=args.email,
        password=args.password,
        run_date=run_date,
        timezone=timezone,
        scenario_ids=frozenset(args.scenario),
        approve_writes=args.approve_writes,
        force=args.force,
        poll_seconds=args.poll_seconds,
        timeout_seconds=args.timeout_seconds,
        request_timeout_seconds=args.request_timeout_seconds,
        cooldown_seconds=args.cooldown_seconds,
        cleanup_retries=args.cleanup_retries,
        cleanup_retry_delay_seconds=args.cleanup_retry_delay_seconds,
        database_url=args.database_url,
    )


def main() -> int:
    try:
        config = parse_args()
        client = ApiClient(config.api_url, config.request_timeout_seconds)
        backfiller = BenchmarkTimestampBackfiller(
            config.database_url,
            config.timezone,
        )
        return BenchmarkScenarioRunner(client, backfiller, config).run()
    except (RunnerError, KeyboardInterrupt) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
