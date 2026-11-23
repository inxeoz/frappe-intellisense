import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from frappe_intellisense.cli import _fix_venv, _write_json
from frappe_intellisense.detect import find_bench, find_installed_frappe, find_nearby_frappe, resolve
from frappe_intellisense.generators.javascript import GLOBALS_FILE, globals_source, render_jsconfig
from frappe_intellisense.generators.python import render_mypy_ini, render_pyrightconfig
from frappe_intellisense.generators.source_mirror import mirror_source
from frappe_intellisense.generators.stubs import merge_document_stub, render_get_doc_stub


class GeneratorTests(unittest.TestCase):
    def test_pyright_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "app"
            output.mkdir()
            apps = Path(tmp) / "bench" / "apps"
            text = render_pyrightconfig([apps], output)
            config = json.loads(text)
            self.assertTrue(config["useLibraryCodeForTypes"])
            self.assertEqual(config["extraPaths"], ["../bench/apps"])

    def test_mypy_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "app"
            output.mkdir()
            text = render_mypy_ini([Path(tmp) / "bench" / "apps"], output)
            self.assertIn("mypy_path = ../bench/apps", text)

    def test_jsconfig(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "app"
            output.mkdir()
            js_root = Path(tmp) / "bench" / "apps" / "frappe" / "frappe" / "public" / "js" / "frappe"
            config = json.loads(render_jsconfig([js_root], output))
            self.assertTrue(config["compilerOptions"]["allowJs"])
            self.assertIn(GLOBALS_FILE, config["include"])
            self.assertIn("../bench/apps/frappe/frappe/public/js/frappe/**/*.js", config["include"])

    def test_fix_venv(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            (output / ".venv").mkdir()
            config = {"venvPath": "../..", "venv": "env"}
            _fix_venv(config, output)
            self.assertEqual(config["venvPath"], ".")
            self.assertEqual(config["venv"], ".venv")

    def test_json_merge_preserves_custom_rules(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pyrightconfig.json"
            path.write_text(
                json.dumps({"extraPaths": [".."], "reportMissingImports": "error"}),
                encoding="utf-8",
            )
            generated = render_pyrightconfig([Path(tmp) / "frappe"], Path(tmp))
            self.assertTrue(_write_json(path, generated, True))
            config = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(config["reportMissingImports"], "error")
            self.assertIn("..", config["extraPaths"])
            self.assertIn("frappe", config["extraPaths"])
            self.assertTrue(config["useLibraryCodeForTypes"])

    def test_mirror_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            (source / "frappe" / "model").mkdir(parents=True)
            (source / "frappe" / "public" / "js" / "frappe").mkdir(parents=True)
            (source / ".git").mkdir()
            (source / "frappe" / "model" / "document.py").touch()
            (source / "frappe" / "public" / "js" / "frappe" / "request.js").touch()
            (source / ".git" / "config").touch()
            (source / "logo.png").touch()
            destination = Path(tmp) / "mirror"
            count = mirror_source(source, destination)
            self.assertEqual(count, 2)
            self.assertTrue((destination / "frappe" / "model" / "document.py").is_file())
            self.assertTrue((destination / "frappe" / "public" / "js" / "frappe" / "request.js").is_file())
            self.assertFalse((destination / ".git").exists())
            self.assertFalse((destination / "logo.png").exists())

    def test_get_doc_stub(self):
        with tempfile.TemporaryDirectory() as tmp:
            module = Path(tmp) / "frappe" / "model"
            module.mkdir(parents=True)
            (module / "document.py").write_text(
                """from typing import overload

@overload
def get_doc(doctype: str, name: str) -> "Document":
    \"\"\"Fetch a document.\"\"\"
    ...

def get_doc(*args, **kwargs):
    pass
""",
                encoding="utf-8",
            )
            generated = render_get_doc_stub(tmp)
            self.assertIn("@overload", generated)
            self.assertIn("doctype: str, name: str", generated)
            self.assertIn("Fetch a document.", generated)
            self.assertIn("_SingleDocument = Document", generated)

    def test_merge_document_stub(self):
        generated = "def get_doc(*args: Any, **kwargs: Any) -> Document: ...\n"
        stub = "from typing import Any\nclass Document: ...\n"
        merged = merge_document_stub(stub, generated)
        self.assertIn("from typing import Any, overload", merged)
        self.assertIn("def get_doc(", merged)
        self.assertEqual(merge_document_stub(merged, generated), merged)

    def test_globals_template(self):
        text = globals_source()
        self.assertIn("declare const frappe", text)
        self.assertIn("cur_frm", text)


class DetectTests(unittest.TestCase):
    def test_find_bench(self):
        with tempfile.TemporaryDirectory() as tmp:
            bench = Path(tmp) / "bench"
            (bench / "apps").mkdir(parents=True)
            (bench / "sites").mkdir()
            app = bench / "apps" / "myapp"
            app.mkdir()
            self.assertEqual(find_bench(app), bench)
            self.assertIsNone(find_bench(Path(tmp)))

    def test_find_installed_frappe_from_spec(self):
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp) / "frappe"
            package.mkdir()
            (package / "__init__.py").touch()
            (package / "model").mkdir()
            (package / "model" / "document.py").touch()
            spec = SimpleNamespace(submodule_search_locations=[str(package)], origin=None)
            with patch("frappe_intellisense.detect.importlib.util.find_spec", return_value=spec):
                self.assertEqual(find_installed_frappe(), Path(tmp))

    def test_placeholder_package_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp) / "frappe"
            package.mkdir()
            (package / "__init__.py").touch()
            spec = SimpleNamespace(submodule_search_locations=[str(package)], origin=None)
            with patch("frappe_intellisense.detect.importlib.util.find_spec", return_value=spec):
                self.assertIsNone(find_installed_frappe())

    def test_find_nearby_frappe(self):
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp) / "frappe-source" / "frappe"
            (package / "model").mkdir(parents=True)
            (package / "__init__.py").touch()
            (package / "model" / "document.py").touch()
            project = Path(tmp) / "app"
            project.mkdir()
            self.assertEqual(find_nearby_frappe(project), package.parent)

    def test_resolve_bench(self):
        with tempfile.TemporaryDirectory() as tmp:
            bench = Path(tmp) / "bench"
            js_root = bench / "apps" / "frappe" / "frappe" / "public" / "js" / "frappe"
            js_root.mkdir(parents=True)
            frappe_app = bench / "apps" / "frappe" / "frappe"
            (frappe_app / "__init__.py").touch()
            (frappe_app / "model").mkdir()
            (frappe_app / "model" / "document.py").touch()
            (bench / "sites").mkdir()
            tree = resolve(bench)
            self.assertEqual(tree.js_root, js_root)
            self.assertEqual(tree.python_roots, (bench / "apps",))


if __name__ == "__main__":
    unittest.main()
