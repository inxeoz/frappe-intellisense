from __future__ import annotations

import os
import shutil
from pathlib import Path

EXTENSIONS = {".py", ".pyi", ".js", ".ts", ".json", ".md"}
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "dist", "build"}


def mirror_source(source: str | Path, output: str | Path) -> int:
    root = Path(source).expanduser().resolve()
    destination = Path(output).expanduser().resolve()
    copied: set[Path] = set()
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in EXTENSIONS:
            continue
        relative = path.relative_to(root)
        if any(part in SKIP_DIRS for part in relative.parts):
            continue
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and not os.access(target, os.W_OK):
            raise PermissionError(f"Cannot overwrite {target}. Run: chmod -R u+w {destination}")
        shutil.copy2(path, target)
        copied.add(relative)
    for path in destination.rglob("*"):
        if path.is_file() and path.relative_to(destination) not in copied:
            path.unlink()
    return len(copied)
