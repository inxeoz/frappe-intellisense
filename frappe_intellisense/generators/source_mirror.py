from __future__ import annotations

import shutil
from pathlib import Path

EXTENSIONS = {".py", ".pyi", ".js", ".ts", ".json", ".md"}
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "dist", "build"}


def mirror_source(source: str | Path, output: str | Path) -> int:
    root = Path(source).expanduser().resolve()
    destination = Path(output).expanduser().resolve()
    count = 0
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in EXTENSIONS:
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        target = destination / path.relative_to(root)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        count += 1
    return count
