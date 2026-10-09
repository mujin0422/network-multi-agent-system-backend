import json
import re
import textwrap
import yaml
from pathlib import Path
from typing import Any

ANSI_ESCAPE_PATTERN = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
YES_VALUES = {"y", "yes", "ok", "có", "co", "đồng ý", "dong y", "true", "1"}
NO_VALUES = {"n", "no", "không", "khong", "hủy", "huy", "false", "0"}


def loadYamlFile(path: str | Path, default: Any = None) -> Any:
    """Load YAML file and return default when the file is missing or empty."""
    file_path = Path(path)
    if not file_path.exists():
        return default

    with file_path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or default


def safeJsonLoads(value: Any, default: Any = None) -> Any:
    """Parse JSON safely and return default when value is invalid JSON."""
    if not isinstance(value, str):
        return default

    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


def wrapTextLines(text: str, width: int = 120) -> list[str]:
    """Wrap each input line without collapsing existing whitespace."""
    wrapped_lines: list[str] = []

    for line in str(text).splitlines():
        if len(line) > width:
            wrapped_lines.extend(
                textwrap.wrap(line, width=width, replace_whitespace=False)
            )
        else:
            wrapped_lines.append(line)

    return wrapped_lines


def normalizeYesNo(value: Any) -> bool | None:
    """Convert common approval words to True/False, or None when unknown."""
    normalized = str(value).strip().lower()

    if normalized in YES_VALUES:
        return True
    if normalized in NO_VALUES:
        return False
    return None


def stripAnsi(text: Any) -> str:
    """Remove terminal ANSI escape sequences from text."""
    return ANSI_ESCAPE_PATTERN.sub("", str(text))


def formatError(error: Exception | str) -> str:
    """Return a clean string for exceptions or error-like values."""
    return str(error).strip()


def ensureList(value: Any) -> list[Any]:
    """Return value as a list without splitting strings."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple | set):
        return list(value)
    return [value]
