from __future__ import annotations

import json
import os
from pathlib import Path


def relative(path: Path, output: Path) -> str:
    return Path(os.path.relpath(path, output)).as_posix()


def render_pyrightconfig(roots: list[Path], output: Path) -> str:
    config = {
        "extraPaths": [relative(root, output) for root in roots],
        "useLibraryCodeForTypes": True,
        "reportMissingImports": "warning",
    }
    return json.dumps(config, indent=2) + "\n"


def render_mypy_ini(roots: list[Path], output: Path) -> str:
    paths = ", ".join(relative(root, output) for root in roots)
    return f"[mypy]\nmypy_path = {paths}\nfollow_imports = normal\n"
