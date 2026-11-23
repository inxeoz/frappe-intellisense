# Design

## Goal

One pip package that makes Frappe's Python and JavaScript APIs navigable from
any editor: completions, signature help, hover docs and go-to-definition.

## Decision

Use the language servers that editors already have instead of writing a new
one. Pyright/Pylance covers Python. The TypeScript server covers JavaScript.
Both speak LSP, so all editors with an LSP client are supported.

The package is a generator. It finds the Frappe source in a bench or an
installed environment and writes editor-neutral config files into the user's
project.

## Python

Frappe already annotates its source and lists lazy module attributes in a
`TYPE_CHECKING` block in `frappe/__init__.py`. Frappe does not ship a
`py.typed` marker, so a strict checker treats the installed package as
untyped. The generated `pyrightconfig.json` sets
`useLibraryCodeForTypes: true` and adds the bench `apps/` directory to
`extraPaths`. The generated `mypy.ini` adds the same directory to
`mypy_path`, which makes Frappe source rather than an installed stub package.
No file inside Frappe is modified.

Frappe's `simple_singledispatch` has no return annotation, so Pyright erases
the types of decorated functions. The generator writes a typed stub for that
decorator which preserves the decorated callable. `get_doc` then resolves to
its five overloads. A local `typings/frappe/model/document.pyi` that models
dynamic DocType fields shadows the real module, so the generator adds the
`get_doc` overloads to that stub too.

## JavaScript

Frappe's desk creates globals at runtime in `provide.js`, `request.js` and
`script_manager.js`. The generated `jsconfig.json` enables `allowJs` and
includes `frappe/public/js/frappe/**/*.js`, so the TypeScript server reads
the real source and its JSDoc. `frappe-globals.d.ts` declares the runtime
globals and the most used methods with hover text.

The curated declarations in `frappe-globals.d.ts` are typed interfaces. A
go-to-definition on one of those methods lands on the declaration in v1. The
next step is to generate declarations with source maps so the jump lands on
the implementation in `frappe/public/js/frappe/`.

## Layout

```
frappe_intellisense/
  cli.py                 init, doctor, editors, show
  detect.py              find bench, frappe app or installed package
  editor_snippets.py     client settings for common editors
  generators/python.py   pyrightconfig.json, mypy.ini
  generators/javascript.py jsconfig.json, globals file
  templates/frappe-globals.d.ts
tests/
```

## Local source mirror

`--local-source` copies only source-text files from Frappe into the project.
This keeps Frappe unchanged, gives the editor a stable source tree, and makes
`show` resolve symbols inside the project. A local Document stub still shadows
`get_doc`, so Ctrl+click lands on the stub; `show get_doc` opens the mirrored
implementation.

## Out of scope for v1

- DocType and field completion from a live site.
- Generating full `.pyi` stubs.
- Modifying Frappe or an app's source.
