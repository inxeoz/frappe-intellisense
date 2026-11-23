from __future__ import annotations

import ast
import re
from pathlib import Path

DECORATOR_STUB = """from collections.abc import Callable
from typing import TypeVar

F = TypeVar("F", bound=Callable[..., object])

def simple_singledispatch(func: F) -> F: ...
"""


def _signature(node: ast.FunctionDef) -> tuple[str, str]:
    args: list[str] = []
    positional = [*node.args.posonlyargs, *node.args.args]
    default_start = len(positional) - len(node.args.defaults)
    for index, arg in enumerate(positional):
        text = arg.arg
        if arg.annotation is not None:
            text += ": " + ast.unparse(arg.annotation)
        if index >= default_start:
            text += " = ..."
        args.append(text)
    if node.args.posonlyargs:
        args.append("/")
    if node.args.vararg is not None:
        text = "*" + node.args.vararg.arg
        if node.args.vararg.annotation is not None:
            text += ": " + ast.unparse(node.args.vararg.annotation)
        args.append(text)
    elif node.args.kwonlyargs:
        args.append("*")
    for arg, default in zip(node.args.kwonlyargs, node.args.kw_defaults):
        text = arg.arg
        if arg.annotation is not None:
            text += ": " + ast.unparse(arg.annotation)
        if default is not None:
            text += " = ..."
        args.append(text)
    if node.args.kwarg is not None:
        text = "**" + node.args.kwarg.arg
        if node.args.kwarg.annotation is not None:
            text += ": " + ast.unparse(node.args.kwarg.annotation)
        args.append(text)
    returns = ast.unparse(node.returns) if node.returns is not None else "Any"
    return ", ".join(args), returns


def render_get_doc_stub(frappe_root: str | Path) -> str:
    source = Path(frappe_root) / "frappe" / "model" / "document.py"
    text = source.read_text(encoding="utf-8")
    text = re.sub(r"^\s*type\s+\w+(?:\[[^\]]*\])?\s*=.*$", "", text, flags=re.M)
    text = re.sub(r"^(class\s+\w+)\[[^\]]*\]", r"\1", text, flags=re.M)
    text = re.sub(r"^(def\s+\w+)\[[^\]]*\]", r"\1", text, flags=re.M)
    tree = ast.parse(text)
    lines: list[str] = ["_SingleDocument = Document", "_NewDocument = Document", ""]
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef) or node.name != "get_doc":
            continue
        if not any("overload" in ast.unparse(decorator) for decorator in node.decorator_list):
            continue
        params, returns = _signature(node)
        lines.append("@overload")
        lines.append(f"def get_doc({params}) -> {returns}:")
        if docstring := ast.get_docstring(node):
            lines.append('    """')
            lines.extend("    " + text for text in docstring.splitlines())
            lines.append('    """')
        lines.append("    ...")
    lines.append("def get_doc(*args: Any, **kwargs: Any) -> Document: ...")
    return "\n".join(lines) + "\n"


def merge_document_stub(existing: str, generated: str) -> str:
    if re.search(r"^def get_doc\(", existing, re.MULTILINE):
        return existing
    imports = existing.splitlines()
    if "from typing import Any" in existing:
        imports = [
            line.replace("from typing import Any", "from typing import Any, overload")
            if line.startswith("from typing import Any")
            else line
            for line in imports
        ]
    else:
        imports.insert(0, "from typing import Any, overload")
    return "\n".join(imports).rstrip() + "\n\n" + generated
