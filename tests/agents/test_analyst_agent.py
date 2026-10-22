"""Kiểm thử structured output và retry của Analyst Agent."""

import asyncio
from types import SimpleNamespace

from app.agents.analyst import AnalystAgent


class StubChatModel:
    def __init__(self, contents: list[str]) -> None:
        self._contents = iter(contents)
        self.calls: list[list] = []

    async def ainvoke(self, messages: list) -> SimpleNamespace:
        self.calls.append(messages.copy())
        return SimpleNamespace(content=next(self._contents), additional_kwargs={})


def test_analyst_recreates_truncated_json_on_retry() -> None:
    model = StubChatModel(
        [
            '{"summary":"JSON bị cắt',
            (
                '{"summary":"P1 và P2 hoạt động bình thường.",'
                '"findings":["OSPF đã hội tụ"],'
                '"likely_causes":[],"recommendations":[],'
                '"requires_more_data":false}'
            ),
        ]
    )

    result = asyncio.run(AnalystAgent(model).analyze([{"status": "SUCCESS"}]))

    assert result.summary == "P1 và P2 hoạt động bình thường."
    assert result.findings == ["OSPF đã hội tụ"]
    assert len(model.calls) == 2
    assert "tạo lại một JSON MỚI" in model.calls[1][-1].content
