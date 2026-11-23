from __future__ import annotations

import argparse
import glob
import json
import re
import sys
from pathlib import Path

from .detect import resolve
from .editor_snippets import SNIPPETS
from .generators.javascript import GLOBALS_FILE, globals_source, render_jsconfig
from .generators.python import render_mypy_ini, render_pyrightconfig
from .generators.source_mirror import mirror_source
from .generators.stubs import DECORATOR_STUB, merge_document_stub, render_get_doc_stub


def _write(path: Path, text: str, force: bool) -> bool:
    if path.exists() and not force:
        print(f"skip {path} (use --force to overwrite)")
        return False
    path.write_text(text, encoding="utf-8")
    print(f"write {path}")
    return True


def _fix_venv(config: dict, output: Path) -> None:
    if not (output / ".venv").is_dir():
        return
    base = Path(config.get("venvPath", ""))
    venv = config.get("venv", "")
    if base and venv:
        target = base / venv if base.is_absolute() else output / base / venv
        if target.is_dir():
            return
    config["venvPath"] = "."
    config["venv"] = ".venv"


def _write_json(path: Path, text: str, force: bool) -> bool:
    generated = json.loads(text)
    if path.is_file():
        if not force:
            print(f"skip {path} (use --force to merge)")
            return False
        merged = json.loads(path.read_text(encoding="utf-8"))
        for key, value in generated.items():
            if key == "compilerOptions":
                options = dict(merged.get(key, {}))
                for name, setting in value.items():
                    options.setdefault(name, setting)
                merged[key] = options
            elif key in ("include", "extraPaths"):
                merged[key] = list(dict.fromkeys([*merged.get(key, []), *value]))
            else:
                merged.setdefault(key, value)
        merged["useLibraryCodeForTypes"] = True
        _fix_venv(merged, path.parent)
        text = json.dumps(merged, indent=2) + "\n"
    else:
        config = json.loads(text)
        _fix_venv(config, path.parent)
        text = json.dumps(config, indent=2) + "\n"
    return _write(path, text, force)


def _has_js_files(root: Path) -> bool:
    suffixes = {".js", ".jsx", ".ts", ".tsx", ".vue"}
    skip = {".git", ".venv", ".frappe-src", "node_modules", "dist", "build"}
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in suffixes:
            continue
        if any(part in skip for part in path.relative_to(root).parts):
            continue
        return True
    return False


def init(args: argparse.Namespace) -> int:
    output = Path(args.output).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    tree = resolve(args.bench or output, args.frappe)
    if tree.frappe_package is None:
        print("Could not find Frappe. Pass --frappe /path/to/frappe-source.", file=sys.stderr)
        return 1

    source_root = tree.frappe_package
    js_root = tree.js_root
    python_roots = list(tree.python_roots)
    if args.local_source:
        mirror = output / args.local_source
        count = mirror_source(source_root, mirror)
        source_root = mirror
        js_root = mirror / "frappe" / "public" / "js" / "frappe"
        python_roots = [mirror]
        print(f"mirrored {count} source files to {mirror}")

    if not args.no_python and python_roots:
        _write_json(output / "pyrightconfig.json", render_pyrightconfig(python_roots, output), args.force)
        if args.mypy or (output / "mypy.ini").is_file():
            _write(output / "mypy.ini", render_mypy_ini(python_roots, output), args.force)
    if not args.no_js and (args.js or _has_js_files(output)) and js_root is not None and js_root.is_dir():
        _write(output / GLOBALS_FILE, globals_source(), args.force)
        _write_json(output / "jsconfig.json", render_jsconfig([js_root], output), args.force)

    if not args.no_stubs and (output / "typings").is_dir():
        typings = output / "typings" / "frappe"
        (typings / "model" / "utils").mkdir(parents=True, exist_ok=True)
        _write(typings / "model" / "utils" / "__init__.pyi", DECORATOR_STUB, args.force)
        document_stub = typings / "model" / "document.pyi"
        if document_stub.is_file():
            merged = merge_document_stub(
                document_stub.read_text(encoding="utf-8"),
                render_get_doc_stub(source_root),
            )
            _write(document_stub, merged, args.force)

    print(f"Frappe source: {source_root}")
    if tree.bench is not None:
        print(f"Bench: {tree.bench}")
    return 0


def doctor(args: argparse.Namespace) -> int:
    output = Path(args.output).expanduser().resolve()
    failures = 0
    names = [
        name
        for name in ("pyrightconfig.json", "mypy.ini", "jsconfig.json", GLOBALS_FILE)
        if (output / name).is_file()
    ]
    if not names:
        print(f"no frappe-intellisense config found in {output}")
        return 1
    for name in names:
        path = output / name
        print(f"found {path}")
        if name.endswith(".json"):
            config = json.loads(path.read_text(encoding="utf-8"))
            for key in ("include", "extraPaths"):
                for entry in config.get(key, []):
                    if not glob.glob(str(output / entry), recursive=True):
                        print(f"  no matches for {entry}")
                        failures += 1
            venv_path = config.get("venvPath")
            venv = config.get("venv")
            if venv_path and venv:
                base = Path(venv_path)
                target = base / venv if base.is_absolute() else output / base / venv
                if not target.is_dir():
                    print(f"  venv not found: {target}")
                    failures += 1
    return 1 if failures else 0


def show(args: argparse.Namespace) -> int:
    tree = resolve(args.project, args.frappe)
    if tree.frappe_package is None:
        print("Could not find Frappe. Pass --frappe /path/to/frappe-source.", file=sys.stderr)
        return 1
    pattern = re.compile(rf"^(?:async\s+)?(?:def|class)\s+{re.escape(args.symbol)}\b")
    package = tree.frappe_package / "frappe"
    matches: list[tuple[Path, int, str, bool]] = []
    for path in package.rglob("*.py"):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for number, line in enumerate(lines, 1):
            if pattern.match(line):
                overload = number > 1 and "@overload" in lines[number - 2]
                matches.append((path, number, line, overload))
    if not matches:
        print(f"{args.symbol} not found in {package}")
        return 1
    matches.sort(key=lambda item: (item[3], str(item[0]), item[1]))
    for path, number, line, _ in matches[:10]:
        print(f"{path}:{number}: {line.strip()}")
    return 0


def editors(args: argparse.Namespace) -> int:
    for name in args.editor or SNIPPETS:
        print(f"## {name}")
        print(SNIPPETS[name])
        print()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="frappe-intellisense")
    commands = parser.add_subparsers(dest="command", required=True)

    init_parser = commands.add_parser("init", help="write language server configuration")
    init_parser.add_argument("output", nargs="?", default=".")
    init_parser.add_argument("--bench", default=None)
    init_parser.add_argument("--frappe", default=None, help="path to the Frappe source root")
    init_parser.add_argument("--force", action="store_true")
    init_parser.add_argument("--no-python", action="store_true")
    init_parser.add_argument("--no-js", action="store_true")
    init_parser.add_argument("--no-stubs", action="store_true")
    init_parser.add_argument("--mypy", action="store_true", help="generate mypy.ini even if none exists")
    init_parser.add_argument("--js", action="store_true", help="generate JS config even if no JS files exist")
    init_parser.add_argument("--local-source", nargs="?", const=".frappe-src", default=None,
                             help="mirror Frappe source into the project for offline code viewing")
    init_parser.set_defaults(func=init)

    doctor_parser = commands.add_parser("doctor", help="check generated configuration")
    doctor_parser.add_argument("output", nargs="?", default=".")
    doctor_parser.set_defaults(func=doctor)

    editors_parser = commands.add_parser("editors", help="print editor client settings")
    editors_parser.add_argument("editor", nargs="*", choices=sorted(SNIPPETS))
    editors_parser.set_defaults(func=editors)

    show_parser = commands.add_parser("show", help="locate a Frappe symbol in its source")
    show_parser.add_argument("symbol")
    show_parser.add_argument("project", nargs="?", default=".")
    show_parser.add_argument("--frappe", default=None)
    show_parser.set_defaults(func=show)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
