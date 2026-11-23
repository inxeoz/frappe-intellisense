# frappe-intellisense

A pip-installable tool that gives Frappe developers completions, hover
documentation and go-to-definition in any editor.

It writes configuration for the language servers you already use: Pyright or
Pylance for Python, and the TypeScript server for JavaScript. It does not
change Frappe and does not install a new language server.

## Install

```sh
pip install .
```

## Use

From your app or bench directory:

```sh
frappe-intellisense init . --bench /path/to/bench
```

This writes `pyrightconfig.json`, `mypy.ini`, `jsconfig.json` and
`frappe-globals.d.ts` into the target directory. It also adds
`typings/frappe/model/utils/__init__.pyi` and, when a local Document stub
exists, adds `get_doc` overloads to it. Use `--force` to overwrite existing
files, `--no-python`, `--no-js` or `--no-stubs` to limit the output. With
`--force`, JSON config files are merged with the existing ones, so custom
rules survive.

If you run it inside a bench, `--bench` is optional. Otherwise the tool looks
for Frappe in the active Python environment and in nearby directories. Pass
`--frappe /path/to/frappe-source` when detection picks the wrong one. A
placeholder `frappe` package from PyPI is never used as the source.

Add `--local-source` to copy Frappe's `.py`, `.pyi`, `.js`, `.ts`, `.json` and
`.md` files into `.frappe-src/` in your project. The generated configs then
point at that copy, so typing, docs and source browsing work offline. The copy
can be made read-only with `chmod -R a-w .frappe-src` and should be ignored by
git.

Other commands:

```sh
frappe-intellisense doctor .
frappe-intellisense editors
frappe-intellisense show get_doc
```

## Use in any project folder

```sh
cd /path/to/any-app
python -m venv .venv                 # skip if the project already has one
.venv/bin/python -m pip install /path/to/frappe-intellisense
.venv/bin/frappe-intellisense init . --frappe /path/to/frappe-source --local-source
.venv/bin/frappe-intellisense doctor .
```

`--frappe` is optional when the project is inside a bench, when Frappe is
installed correctly in the venv, or when a Frappe source folder sits next to
the project. `--local-source` is optional; it makes the setup self-contained
and works offline. The generated paths are relative, so the folder can be
moved as long as `.venv` and `.frappe-src` move with it.

## What each language gets

- Python: Pyright reads Frappe's annotated source and its `TYPE_CHECKING`
  imports. The generated stub for `simple_singledispatch` keeps overloaded
  functions such as `get_doc` typed, and a local Document stub keeps dynamic
  DocType fields from raising errors.
- `frappe-intellisense show get_doc` prints the real source location. Ctrl+click
  lands on a stub when a local Document stub shadows the source module; use
  `show` to jump to the implementation.
- JavaScript: the TypeScript server reads Frappe's desk JS and its JSDoc.
  `frappe-globals.d.ts` describes globals created at runtime, such as
  `frappe`, `cur_frm` and `cur_list`.

Any editor with an LSP client can use these files. VS Code, Neovim, Emacs,
Sublime Text and JetBrains all have clients for Pyright and TypeScript.
Run `frappe-intellisense editors` for the extra client settings.

## Limits

DocType names and field names are not read from a live site. That needs a
site connection and is planned as a separate feature.
