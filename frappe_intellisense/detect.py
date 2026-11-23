from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SourceTree:
    bench: Path | None
    frappe_app: Path | None
    frappe_package: Path | None
    js_root: Path | None
    python_roots: tuple[Path, ...]


def _is_frappe_source(root: Path) -> bool:
    package = root / "frappe"
    return (package / "__init__.py").is_file() and (package / "model" / "document.py").is_file()


def _has_bench_layout(path: Path) -> bool:
    return (path / "apps").is_dir() and (path / "sites").is_dir()


def find_bench(start: Path) -> Path | None:
    current = start.expanduser().resolve()
    for candidate in (current, *current.parents):
        if _has_bench_layout(candidate):
            return candidate
    return None


def find_frappe_app(bench: Path | None) -> Path | None:
    if bench is None:
        return None
    app = bench / "apps" / "frappe"
    if _is_frappe_source(app):
        return app
    return None


def find_installed_frappe() -> Path | None:
    try:
        spec = importlib.util.find_spec("frappe")
    except (ImportError, ValueError):
        spec = None
    candidates: list[Path] = []
    if spec is not None:
        for location in spec.submodule_search_locations or ():
            candidates.append(Path(location).parent)
        if spec.origin and Path(spec.origin).name == "__init__.py":
            candidates.append(Path(spec.origin).parent.parent)
    candidates.extend(Path(entry) for entry in sys.path if entry)
    return next((root for root in candidates if _is_frappe_source(root)), None)


def find_nearby_frappe(start: str | Path) -> Path | None:
    root = Path(start).expanduser().resolve()
    for base in (root, *root.parents)[:4]:
        try:
            children = sorted(child for child in base.iterdir() if child.is_dir())
        except OSError:
            continue
        for child in children:
            if _is_frappe_source(child):
                return child
            app = child / "apps" / "frappe"
            if _is_frappe_source(app):
                return app
    return None


def resolve(start: str | Path, frappe_root: str | Path | None = None) -> SourceTree:
    root = Path(start).expanduser().resolve()
    bench = find_bench(root)
    frappe_app = find_frappe_app(bench)
    explicit = Path(frappe_root).expanduser().resolve() if frappe_root is not None else None
    package = explicit or frappe_app or find_installed_frappe() or find_nearby_frappe(root)
    js_root = None
    if package is not None:
        candidate = package / "frappe" / "public" / "js" / "frappe"
        if candidate.is_dir():
            js_root = candidate
    python_roots: list[Path] = []
    if bench is not None:
        apps_dir = bench / "apps"
        python_roots.extend(
            sorted(
                app
                for app in apps_dir.iterdir()
                if app.is_dir() and (app / app.name / "__init__.py").is_file()
            )
        )
    elif package is not None:
        python_roots.append(package)
    return SourceTree(bench, frappe_app, package, js_root, tuple(python_roots))
