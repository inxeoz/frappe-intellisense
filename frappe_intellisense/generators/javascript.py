from __future__ import annotations

import json
import os
from importlib.resources import files
from pathlib import Path

GLOBALS_FILE = "frappe-globals.d.ts"


def globals_source() -> str:
    return (files("frappe_intellisense") / "templates" / GLOBALS_FILE).read_text(encoding="utf-8")


def render_jsconfig(js_roots: list[Path], output: Path) -> str:
    include = [GLOBALS_FILE]
    for root in js_roots:
        pattern = Path(os.path.relpath(root, output)) / "**" / "*.js"
        include.append(pattern.as_posix())
    config = {
        "compilerOptions": {
            "allowJs": True,
            "checkJs": False,
            "target": "ES2022",
            "module": "ESNext",
            "moduleResolution": "Node",
            "noEmit": True,
        },
        "include": include,
    }
    return json.dumps(config, indent=2) + "\n"
