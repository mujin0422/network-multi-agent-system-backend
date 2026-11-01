"""Kiểm tra quy ước đặt tên và tài liệu của repository/service."""

import ast
from pathlib import Path


DOMAINS_ROOT = Path(__file__).parents[2] / "src" / "app" / "domains"
WRITE_METHOD_PREFIXES = (
    "add",
    "create",
    "decide",
    "delete",
    "expire",
    "replace",
    "revoke",
    "rotate",
    "save",
    "update",
)


def _layer_files(layer: str) -> list[Path]:
    """Lấy toàn bộ file Python thuộc một tầng trong các domain."""

    return sorted(DOMAINS_ROOT.glob(f"*/{layer}/*.py"))


def _class_methods(path: Path) -> list[tuple[str, ast.FunctionDef | ast.AsyncFunctionDef]]:
    """Phân tích và trả các method được khai báo trực tiếp trong từng class."""

    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [
        (class_node.name, method)
        for class_node in ast.walk(tree)
        if isinstance(class_node, ast.ClassDef)
        for method in class_node.body
        if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]


def test_repository_read_methods_start_with_get() -> None:
    """Bảo đảm method public của repository là truy vấn get hoặc thao tác ghi."""

    invalid: list[str] = []
    for path in _layer_files("repositories"):
        for class_name, method in _class_methods(path):
            if method.name.startswith("_"):
                continue
            if method.name.startswith("get"):
                continue
            if method.name.startswith(WRITE_METHOD_PREFIXES):
                continue
            invalid.append(f"{path}:{method.lineno} {class_name}.{method.name}")

    assert invalid == [], "Method repository chưa đúng quy ước:\n" + "\n".join(
        invalid
    )


def test_repository_and_service_methods_have_docstrings() -> None:
    """Bảo đảm mọi method trong repository và service đều có chú thích chức năng."""

    missing: list[str] = []
    for layer in ("repositories", "services"):
        for path in _layer_files(layer):
            for class_name, method in _class_methods(path):
                if ast.get_docstring(method, clean=False) is None:
                    missing.append(
                        f"{path}:{method.lineno} {class_name}.{method.name}"
                    )

    assert missing == [], "Method còn thiếu docstring:\n" + "\n".join(missing)
