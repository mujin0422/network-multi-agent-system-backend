"""Điều phối kết quả thực thi thành phản hồi cuối trong conversation."""

import re
from datetime import UTC, datetime

from app.agents.analyst import AnalystAgent, AnalysisResult
from app.agents.network import NetworkExecutionResult
from app.diagnostics import (
    DiagnosticEvidence,
    EvidenceCoverage,
    EvidenceSource,
    EvidenceType,
    PlaybookTarget,
    evaluate_evidence_coverage,
    get_playbook,
    parse_command_output,
)
from app.domains.conversation.schemas import (
    Message,
    MessageCreate,
    MessageSender,
    MessageType,
)
from app.domains.conversation.services import ConversationService
from app.domains.execution.schemas import (
    ActivityActorType,
    ActivityEventStatus,
    ActivityEventType,
    AccessMode,
    DeviceRole,
    ExecutionPlanCreate,
    PlannedDevice,
    PlannedOperation,
    TaskDetail,
    TaskStatus,
    TaskType,
)
from app.domains.execution.services import ExecutionService
from app.domains.inventory.providers import GNS3Provider
from app.domains.inventory.services import DeviceService


class AnalysisOrchestrator:
    """Gọi Analyst Agent, lưu timeline và message AGENT/FINAL_RESPONSE."""

    def __init__(
        self,
        analyst: AnalystAgent,
        execution_service: ExecutionService,
        conversation_service: ConversationService,
        device_service: DeviceService,
        gns3_provider: GNS3Provider | None = None,
    ) -> None:
        """Khởi tạo Analyst Agent và các service lưu kết quả phân tích."""

        self._analyst = analyst
        self._execution_service = execution_service
        self._conversation_service = conversation_service
        self._device_service = device_service
        self._gns3_provider = gns3_provider

    async def analyze(
        self,
        task: TaskDetail,
        execution_results: list[NetworkExecutionResult],
        evidence_coverage: EvidenceCoverage | None = None,
    ) -> AnalysisResult | None:
        """Phân tích evidence nhưng chưa tạo phản hồi cuối cho conversation."""

        # Bước 1: Không phân tích khi Task vẫn đang chạy hoặc chờ approval.
        current_task = self._execution_service.get_task(task.id)
        if current_task.task_status == TaskStatus.RUNNING:
            return None

        # Bước 2: Ghi mốc ANALYSIS_STARTED để giao diện theo dõi tiến trình.
        analysis_started_at = datetime.now(UTC)
        self._execution_service.record_activity(
            task.id,
            ActivityActorType.ANALYST,
            ActivityEventType.ANALYSIS_STARTED,
            ActivityEventStatus.RUNNING,
            started_at=analysis_started_at,
        )
        # Bước 3: Chuẩn hóa output kỹ thuật và bổ sung topology context.
        analysis_inputs = self._build_analysis_inputs(execution_results)
        if evidence_coverage is not None:
            analysis_inputs.append(
                {
                    "context_type": "DIAGNOSTIC EVIDENCE COVERAGE",
                    **evidence_coverage.model_dump(mode="json"),
                }
            )
        fallback_error: str | None = None
        try:
            # Bước 4: Gọi Analyst; lỗi model/schema sẽ chuyển sang fallback an toàn.
            analysis = await self._analyst.analyze(analysis_inputs)
        except Exception as exc:
            fallback_error = str(exc)
            analysis = self._build_fallback_analysis(analysis_inputs)

        # Bước 5: Lưu structured diagnosis trước khi evaluator đọc kết quả.
        self._execution_service.record_activity(
            task.id,
            ActivityActorType.ANALYST,
            ActivityEventType.ANALYSIS_COMPLETED,
            event_data={
                "requires_more_data": analysis.requires_more_data,
                "confidence": analysis.confidence,
                "evidence_gaps": analysis.evidence_gaps,
                "suggested_check_count": len(analysis.suggested_checks),
                "evidence_coverage": (
                    evidence_coverage.model_dump(mode="json")
                    if evidence_coverage is not None
                    else None
                ),
                "used_fallback": fallback_error is not None,
                "diagnosis_submission": {
                    "is_anomaly": analysis.is_anomaly,
                    "root_causes": [
                        cause.model_dump(mode="json") for cause in analysis.root_causes
                    ],
                },
                **({"fallback_reason": fallback_error} if fallback_error else {}),
            },
            started_at=analysis_started_at,
            completed_at=datetime.now(UTC),
        )
        return analysis

    async def analyze_and_respond(
        self,
        task: TaskDetail,
        execution_results: list[NetworkExecutionResult],
    ) -> Message | None:
        """Phân tích kết quả thực thi, lưu timeline và tạo phản hồi cuối."""

        current_task = self._execution_service.get_task(task.id)
        analysis = await self.analyze(task, execution_results)
        if analysis is None:
            return self._save_waiting_response(current_task)
        return self.finalize_response(current_task, analysis)

    def finalize_response(
        self,
        task: TaskDetail,
        analysis: AnalysisResult | None,
    ) -> Message:
        """Tạo duy nhất một phản hồi sau khi vòng điều tra đã kết thúc."""

        # Bước 1: Nếu Task chưa sẵn sàng, chỉ tạo thông báo chờ phê duyệt.
        if analysis is None:
            return self._save_waiting_response(task)
        # Bước 2: Chuyển AnalysisResult thành FINAL_RESPONSE dễ đọc cho người dùng.
        message = self._conversation_service.create_message(
            task.conversation_id,
            MessageCreate(
                sender_by=MessageSender.AGENT,
                reply_to_message_id=task.source_message_id,
                message_type=MessageType.FINAL_RESPONSE,
                message=self._format_analysis(analysis),
            ),
        )
        # Bước 3: Ghi message ID vào timeline để Benchmark liên kết chính xác.
        self._execution_service.record_activity(
            task.id,
            ActivityActorType.ANALYST,
            ActivityEventType.FINAL_RESPONSE_CREATED,
            event_data={"message_id": message.id},
        )
        return message

    def record_evidence_gate(
        self,
        task_id: str,
        coverage: EvidenceCoverage,
        investigation_round: int,
        stop_reason: str,
    ) -> None:
        """Lưu quyết định cuối của evidence gate vào timeline để đánh giá."""

        self._execution_service.record_activity(
            task_id,
            ActivityActorType.ORCHESTRATOR,
            ActivityEventType.EVIDENCE_COVERAGE_EVALUATED,
            event_data={
                **coverage.model_dump(mode="json"),
                "investigation_round": investigation_round,
                "stop_reason": stop_reason,
            },
        )

    def build_investigation_plan(
        self,
        analysis: AnalysisResult,
        *,
        playbook_keys: list[str] | None = None,
        missing_evidence: list[EvidenceType] | None = None,
        execution_results: list[NetworkExecutionResult] | None = None,
    ) -> ExecutionPlanCreate | None:
        """Ưu tiên check thiếu từ playbook rồi bổ sung đề nghị hợp lệ của Analyst."""

        # Bước 1: Chỉ ánh xạ hostname mà Inventory hiện đang quản lý.
        devices = self._device_service.list_available_devices()
        by_hostname = {device.hostname.casefold(): device.id for device in devices}
        hostname_by_id = {device.id: device.hostname for device in devices}
        execution_results = execution_results or []
        commands_by_host = self._playbook_missing_commands(
            playbook_keys or [],
            set(missing_evidence or []),
            execution_results,
            hostname_by_id,
        )
        executed = {
            (
                hostname_by_id.get(result.device_id, result.device_id).casefold(),
                item.command.strip().casefold(),
            )
            for result in execution_results
            for item in result.results
        }
        for check in analysis.suggested_checks:
            hostname = check.device.casefold()
            if hostname not in by_hostname:
                continue
            commands_by_host.setdefault(hostname, [])
            commands_by_host[hostname].extend(
                command
                for command in check.commands
                if (hostname, command.strip().casefold()) not in executed
            )

        operations: list[PlannedOperation] = []
        for hostname, commands in commands_by_host.items():
            unique_commands = list(dict.fromkeys(commands))
            device_id = by_hostname.get(hostname)
            if device_id is None or not unique_commands:
                continue
            operations.append(
                PlannedOperation(
                    operation_intent="COLLECT_ADDITIONAL_DIAGNOSTIC_EVIDENCE",
                    operation_parameters={
                        "commands": unique_commands,
                        "reason": "Thu thập evidence bắt buộc còn thiếu theo diagnostic playbook.",
                    },
                    devices=[
                        PlannedDevice(
                            device_id=device_id,
                            device_role=DeviceRole.CONTEXT,
                            access_mode=AccessMode.READ,
                        )
                    ],
                )
            )
        # Bước 3: Không tạo vòng điều tra rỗng khi không ánh xạ được thiết bị.
        if not operations:
            return None
        return ExecutionPlanCreate(task_type=TaskType.DIAGNOSIS, operations=operations)

    def evaluate_evidence_coverage(
        self,
        execution_results: list[NetworkExecutionResult],
        playbook_keys: list[str],
    ) -> EvidenceCoverage:
        """Parse toàn bộ output và tính coverage cho các playbook đang áp dụng."""

        hostnames = {
            device.id: device.hostname
            for device in self._device_service.list_available_devices()
        }
        evidence = self._parse_evidence(execution_results, hostnames)
        return evaluate_evidence_coverage(playbook_keys, evidence)

    def _playbook_missing_commands(
        self,
        playbook_keys: list[str],
        missing: set[EvidenceType],
        execution_results: list[NetworkExecutionResult],
        hostname_by_id: dict[str, str],
    ) -> dict[str, list[str]]:
        """Vật hóa command template còn thiếu trên primary/neighbor hợp lệ."""

        executed: dict[str, set[str]] = {}
        interfaces: dict[str, list[str]] = {}
        for result in execution_results:
            hostname = hostname_by_id.get(result.device_id, result.device_id).casefold()
            executed.setdefault(hostname, set())
            interfaces.setdefault(hostname, [])
            for item in result.results:
                executed[hostname].add(item.command.strip().casefold())
                match = re.search(r"\binterfaces?\s+(\S+)", item.command, re.IGNORECASE)
                if match and match.group(1).casefold() not in {"brief", "status"}:
                    interfaces[hostname].append(match.group(1))

        topology = {}
        if self._gns3_provider is not None:
            try:
                topology = self._gns3_provider.list_topology_neighbors()
            except Exception:
                topology = {}
        topology_by_hostname = {
            hostname.casefold(): neighbors for hostname, neighbors in topology.items()
        }

        planned: dict[str, list[str]] = {}
        primary_hosts = list(executed)
        for key in playbook_keys:
            playbook = get_playbook(key)
            if playbook is None:
                continue
            for command_spec in playbook.commands:
                if not missing.intersection(command_spec.produces):
                    continue
                targets: list[tuple[str, str | None]] = []
                if command_spec.target == PlaybookTarget.PRIMARY:
                    targets = [
                        (hostname, (interfaces.get(hostname) or [None])[0])
                        for hostname in primary_hosts
                    ]
                else:
                    for hostname in primary_hosts:
                        for neighbor in topology_by_hostname.get(hostname, []):
                            targets.append(
                                (
                                    str(neighbor.get("device", "")).casefold(),
                                    neighbor.get("peer_interface"),
                                )
                            )
                for hostname, interface in targets:
                    if not hostname:
                        continue
                    command = command_spec.command_template
                    if "{interface}" in command or "{peer_interface}" in command:
                        if not interface:
                            continue
                        command = command.replace("{interface}", interface).replace(
                            "{peer_interface}", interface
                        )
                    if command.strip().casefold() in executed.get(hostname, set()):
                        continue
                    planned.setdefault(hostname, []).append(command)
        return planned

    def _build_analysis_inputs(
        self,
        execution_results: list[NetworkExecutionResult],
    ) -> list[dict]:
        """Chuyển kết quả sang dữ liệu có hostname dễ đọc trước khi gọi LLM."""

        hostnames = {
            device.id: device.hostname
            for device in self._device_service.list_available_devices()
        }
        evidence = self._parse_evidence(execution_results, hostnames)
        evidence_by_execution: dict[str, list[dict]] = {}
        for item in evidence:
            evidence_by_execution.setdefault(item.source.execution_id, []).append(
                item.model_dump(mode="json", exclude={"source": {"device_id"}})
            )
        inputs = []
        for result in execution_results:
            inputs.append(
                {
                    "device": hostnames.get(result.device_id, result.device_id),
                    "access_mode": result.access_mode.value,
                    "status": result.status.value,
                    "command_results": [
                        item.model_dump(mode="json") for item in result.results
                    ],
                    "structured_evidence": evidence_by_execution.get(
                        result.operation_device_id, []
                    ),
                    "error_message": result.error_message,
                }
            )
        if self._gns3_provider is not None:
            try:
                inputs.append(
                    {
                        "context_type": "AVAILABLE TOPOLOGY CONTEXT",
                        "neighbors": self._gns3_provider.list_topology_neighbors(),
                    }
                )
            except Exception:
                # Phân tích evidence đã thu thập vẫn tiếp tục nếu topology API lỗi.
                pass
        return inputs

    @staticmethod
    def _parse_evidence(
        execution_results: list[NetworkExecutionResult],
        hostnames: dict[str, str],
    ) -> list[DiagnosticEvidence]:
        """Chuyển toàn bộ CommandResult thành evidence model để tái sử dụng."""

        evidence: list[DiagnosticEvidence] = []
        for result in execution_results:
            hostname = hostnames.get(result.device_id, result.device_id)
            for item in result.results:
                evidence.extend(
                    parse_command_output(
                        item.command,
                        item.output,
                        EvidenceSource(
                            execution_id=result.operation_device_id,
                            device_id=result.device_id,
                            device_name=hostname,
                            command=item.command,
                        ),
                    )
                )
        return evidence

    @staticmethod
    def _build_fallback_analysis(analysis_inputs: list[dict]) -> AnalysisResult:
        """Tạo phân tích an toàn khi Analyst Agent trả dữ liệu không hợp lệ."""

        findings: list[str] = []
        for item in analysis_inputs[:4]:
            device = str(item.get("device") or "Thiết bị không xác định")
            status = str(item.get("status") or "UNKNOWN")
            command_count = len(item.get("command_results") or [])
            if status == "SUCCESS":
                findings.append(
                    f"{device}: đã thực thi thành công {command_count} lệnh kiểm tra."
                )
            else:
                findings.append(f"{device}: quá trình thực thi có trạng thái {status}.")

        device_names = ", ".join(
            str(item.get("device") or "thiết bị không xác định")
            for item in analysis_inputs[:4]
        )
        if not device_names:
            device_names = "các thiết bị được chọn"
        return AnalysisResult(
            summary=(
                f"Đã thu thập kết quả lệnh từ {device_names}, nhưng hệ thống chưa "
                "thể chuẩn hóa nội dung phân tích từ mô hình ngôn ngữ."
            ),
            findings=findings,
            likely_causes=[],
            recommendations=[
                "Thử gửi lại yêu cầu hoặc kiểm tra output lệnh đã lưu trong chi tiết task."
            ],
            requires_more_data=True,
        )

    def _save_waiting_response(self, task: TaskDetail) -> Message:
        """Lưu message thông báo Task đang tạm dừng để chờ phê duyệt."""

        return self._conversation_service.create_message(
            task.conversation_id,
            MessageCreate(
                sender_by=MessageSender.AGENT,
                reply_to_message_id=task.source_message_id,
                message_type=MessageType.APPROVAL_REQUEST,
                message="Kế hoạch đã được tạo. Một hoặc nhiều thao tác cấu hình đang chờ bạn phê duyệt.",
            ),
        )

    @staticmethod
    def _format_analysis(analysis: AnalysisResult) -> str:
        """Định dạng AnalysisResult thành nội dung tiếng Việt dễ đọc."""

        sections = [f"Tóm tắt\n{analysis.summary.strip()}"]
        for title, values in (
            ("Phát hiện chính", analysis.findings),
            ("Nguyên nhân có khả năng", analysis.likely_causes),
            ("Hành động đề xuất", analysis.recommendations),
        ):
            if values:
                sections.append(
                    f"{title}\n" + "\n".join(f"• {item.strip()}" for item in values)
                )
        if analysis.requires_more_data:
            sections.append(
                "Trạng thái dữ liệu\n"
                "Cần thu thập thêm dữ liệu trước khi kết luận nguyên nhân gốc."
            )
        return "\n\n".join(sections)
