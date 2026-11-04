"""Kiểm thử structured output và retry của Analyst Agent."""

import asyncio
from types import SimpleNamespace

import pytest

from app.agents.analyst import AnalystAgent
from app.agents.analyst.prompts import ANALYST_SYSTEM_PROMPT
from app.agents.analyst.schemas import AnalysisResult
from app.agents.network import NetworkExecutionResult, NetworkExecutionStatus
from app.agents.orchestrator import AnalysisOrchestrator
from app.domains.execution.schemas import AccessMode
from app.tools import CommandResult


class StubChatModel:
    def __init__(self, contents: list[str]) -> None:
        self._contents = iter(contents)
        self.calls: list[list] = []

    async def ainvoke(self, messages: list) -> SimpleNamespace:
        self.calls.append(messages.copy())
        return SimpleNamespace(content=next(self._contents), additional_kwargs={})


class StubDeviceService:
    def list_available_devices(self):
        return [
            SimpleNamespace(id="devc-221026-00000001", hostname="P1"),
            SimpleNamespace(id="devc-221026-00000002", hostname="P2"),
        ]


def test_analyst_prompt_interprets_bad_mask_and_avoids_rejected_command() -> None:
    assert 'Bad mask /N for address X' in ANALYST_SYSTEM_PROMPT
    assert "không gọi netmask hợp lệ" in ANALYST_SYSTEM_PROMPT
    assert "Không đề xuất chạy lại nguyên văn command" in ANALYST_SYSTEM_PROMPT


def test_analyst_recreates_truncated_json_on_retry() -> None:
    model = StubChatModel(
        [
            '{"summary":"JSON bị cắt',
            (
                '{"summary":"P1 và P2 hoạt động bình thường.",'
                '"findings":["OSPF đã hội tụ"],'
                '"likely_causes":[],"recommendations":[],'
                '"requires_more_data":false,'
                '"confidence":1,"evidence_gaps":[],"suggested_checks":[],'
                '"is_anomaly":false,"root_causes":[]}'
            ),
        ]
    )

    result = asyncio.run(AnalystAgent(model).analyze([{"status": "SUCCESS"}]))

    assert result.summary == "P1 và P2 hoạt động bình thường."
    assert result.findings == ["OSPF đã hội tụ"]
    assert len(model.calls) == 2
    assert "tạo lại một JSON MỚI" in model.calls[1][-1].content


def test_analyst_validation_retries_can_be_disabled() -> None:
    model = StubChatModel(['{"summary":"JSON bị cắt'])

    with pytest.raises(ValueError, match="không đúng AnalysisResult"):
        asyncio.run(
            AnalystAgent(model, max_validation_retries=0).analyze(
                [{"status": "SUCCESS"}]
            )
        )

    assert len(model.calls) == 1


def test_analyst_repairs_unquoted_schema_key_and_trailing_comma() -> None:
    model = StubChatModel(
        [
            (
                'Phân tích:\n```json\n{"summary":"OSPF đã hội tụ",'
                '"findings":["P1 và P2 có route OSPF"],'
                'likely_causes:[],"recommendations":[],'
                'requires_more_data:false,confidence:1,evidence_gaps:[],'
                'suggested_checks:[],is_anomaly:false,root_causes:[],}\n```'
            )
        ]
    )

    result = asyncio.run(AnalystAgent(model).analyze([{"status": "SUCCESS"}]))

    assert result.summary == "OSPF đã hội tụ"
    assert result.requires_more_data is False
    assert len(model.calls) == 1


def test_analysis_response_is_formatted_as_readable_sections() -> None:
    content = AnalysisOrchestrator._format_analysis(
        AnalysisResult(
            summary="OSPF đã hội tụ nhưng chưa có default route.",
            findings=["P1: Gateway of last resort is not set"],
            likely_causes=["Router biên chưa quảng bá default route vào OSPF"],
            recommendations=["Kiểm tra show ip ospf neighbor trên router biên"],
            requires_more_data=True,
        )
    )

    assert content == (
        "Tóm tắt\n"
        "OSPF đã hội tụ nhưng chưa có default route.\n\n"
        "Phát hiện chính\n"
        "• P1: Gateway of last resort is not set\n\n"
        "Nguyên nhân có khả năng\n"
        "• Router biên chưa quảng bá default route vào OSPF\n\n"
        "Hành động đề xuất\n"
        "• Kiểm tra show ip ospf neighbor trên router biên\n\n"
        "Trạng thái dữ liệu\n"
        "Cần thu thập thêm dữ liệu trước khi kết luận nguyên nhân gốc."
    )


def test_analysis_input_replaces_internal_device_id_with_hostname() -> None:
    orchestrator = AnalysisOrchestrator(
        analyst=None,
        execution_service=None,
        conversation_service=None,
        device_service=StubDeviceService(),
    )
    results = [
        NetworkExecutionResult(
            operation_id="oper-internal",
            operation_device_id="opdv-internal",
            device_id="devc-221026-00000001",
            access_mode=AccessMode.READ,
            status=NetworkExecutionStatus.SUCCESS,
            results=[CommandResult(command="show ip route", output="O 10.0.0.0/8")],
        )
    ]

    payload = orchestrator._build_analysis_inputs(results)

    assert payload == [
        {
            "device": "P1",
            "access_mode": "READ",
            "status": "SUCCESS",
            "command_results": [
                {"command": "show ip route", "output": "O 10.0.0.0/8"}
            ],
            "error_message": None,
        }
    ]
    assert "devc-" not in str(payload)


def test_analysis_fallback_uses_device_names_without_guessing_root_cause() -> None:
    result = AnalysisOrchestrator._build_fallback_analysis(
        [
            {"device": "P1", "status": "SUCCESS", "command_results": [{}, {}]},
            {"device": "P2", "status": "FAILED", "command_results": []},
        ]
    )

    assert "P1, P2" in result.summary
    assert result.findings == [
        "P1: đã thực thi thành công 2 lệnh kiểm tra.",
        "P2: quá trình thực thi có trạng thái FAILED.",
    ]
    assert result.likely_causes == []
    assert result.requires_more_data is True


def test_analyst_retries_until_structured_submission_is_present() -> None:
    model = StubChatModel([
        '{"summary":"P1 interface down","findings":[],"likely_causes":[],"recommendations":[],"requires_more_data":false}',
        '{"summary":"P1 interface down","findings":[],"likely_causes":["P1 FastEthernet0/0 shutdown"],'
        '"recommendations":[],"requires_more_data":false,"confidence":0.95,'
        '"evidence_gaps":[],"suggested_checks":[],"is_anomaly":true,'
        '"root_causes":[{"device":"P1","interface":"FastEthernet0/0","fault_type":"link_down"}]}',
    ])

    result = asyncio.run(AnalystAgent(model).analyze([{"status": "SUCCESS"}]))

    assert len(model.calls) == 2
    assert result.is_anomaly is True
    assert result.root_causes[0].device == "P1"
    assert result.root_causes[0].interface == "FastEthernet0/0"
    assert result.root_causes[0].fault_type == "link_down"
