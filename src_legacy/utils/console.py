from collections.abc import Iterable, Mapping
from typing import Any

from src.utils.helpers import safeJsonLoads


RAW_DATA_TITLE = "[RAW DATA] KẾT QUẢ THỰC THI TỪ THIẾT BỊ"


def printRawData(
    raw_data: Any,
    *,
    content_width: int = 120,
    title: str = RAW_DATA_TITLE,
    tool_label: str = "Tool",
    output_label: str = "Output:",
    indent: str = "\t",
) -> None:
    """Print raw tool outputs in a terminal frame.

    Accepts common shapes:
    - Mapping: {"tool_name": result}
    - ToolMessage list: objects with .name and .content
    - Dict item list: {"name": "...", "content": "..."} or {"tool": "...", "output": "..."}
    - Tuple item list: ("tool_name", result)
    """
    items = list(_iterRawDataItems(raw_data))
    if not items:
        return

    frame_width = content_width + 4
    cyan = "\033[96m"
    yellow = "\033[93m"
    gray = "\033[90m"
    reset = "\033[0m"

    print(f"\n{indent}{cyan}╔{'═' * (frame_width - 2)}╗{reset}")

    title_line = f"║ {title}"
    print(f"{indent}{cyan}{title_line}{' ' * (frame_width - len(title_line) - 1)}║{reset}")

    for tool_name, content in items:
        print(f"{indent}{cyan}╠{'═' * (frame_width - 2)}╣{reset}")

        display_text = _normalizeRawContent(content)
        tool_line = f"{tool_label}: {tool_name}"

        print(f"{indent}{cyan}║ {yellow}{tool_line.ljust(content_width)} {cyan}║{reset}")
        print(f"{indent}{cyan}║ {gray}{output_label.ljust(content_width)} {cyan}║{reset}")

        for line in str(display_text).split("\n"):
            safe_line = line.replace("\r", "")[:content_width]
            print(f"{indent}{cyan}║ {gray}{safe_line.ljust(content_width)} {cyan}║{reset}")

    print(f"{indent}{cyan}╚{'═' * (frame_width - 2)}╝{reset}\n")


def _iterRawDataItems(raw_data: Any) -> Iterable[tuple[str, Any]]:
    if isinstance(raw_data, Mapping):
        if _looksLikeSingleRawItem(raw_data):
            yield _extractRawItem(raw_data)
            return

        for tool_name, content in raw_data.items():
            yield str(tool_name), content
        return

    if isinstance(raw_data, str) or not isinstance(raw_data, Iterable):
        yield "Unknown Tool", raw_data
        return

    for item in raw_data:
        yield _extractRawItem(item)


def _extractRawItem(item: Any) -> tuple[str, Any]:
    if isinstance(item, Mapping):
        tool_name = (
            item.get("tool_name")
            or item.get("tool")
            or item.get("name")
            or item.get("action")
            or "Unknown Tool"
        )
        content = (
            item.get("content")
            if "content" in item
            else item.get("output", item.get("result", item))
        )
        return str(tool_name), content

    if isinstance(item, tuple) and len(item) == 2:
        return str(item[0]), item[1]

    tool_name = getattr(item, "name", None) or getattr(item, "tool_name", None)
    content = getattr(item, "content", item)
    return str(tool_name or "Unknown Tool"), content


def _looksLikeSingleRawItem(value: Mapping[str, Any]) -> bool:
    item_keys = {"tool_name", "tool", "name", "action", "content", "output", "result"}
    return bool(item_keys.intersection(value.keys()))


def _normalizeRawContent(content: Any) -> str:
    parsed_data = content if isinstance(content, Mapping) else safeJsonLoads(content)

    if not isinstance(parsed_data, Mapping):
        return str(content)

    if parsed_data.get("success") is False:
        return f"LỖI: {parsed_data.get('error', 'Không rõ nguyên nhân')}"

    if "output" in parsed_data:
        return str(parsed_data["output"])

    if "content" in parsed_data:
        return str(parsed_data["content"])

    if "error" in parsed_data:
        return f"LỖI: {parsed_data['error']}"

    return str(content)
