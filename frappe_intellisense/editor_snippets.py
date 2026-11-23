SNIPPETS = {
    "vscode": """VS Code: install Python and Pylance. The generated pyrightconfig.json and jsconfig.json are read automatically.

Recommended .vscode/extensions.json:
{"recommendations": ["ms-python.python", "ms-python.vscode-pylance"]}""",
    "neovim": """Neovim with nvim-lspconfig:

require("lspconfig").pyright.setup{}
require("lspconfig").ts_ls.setup{}

Keep the generated config files in your project root.""",
    "emacs": """Emacs with lsp-mode:

(lsp-deferred)
(setq lsp-pyright-multi-root nil)

Keep the generated config files in your project root.""",
    "sublime": """Sublime Text: install LSP, LSP-pyright and LSP-typescript from Package Control.

Keep the generated config files in your project root.""",
    "jetbrains": """PyCharm / WebStorm: mark the bench apps directory as a Python source root, and enable TypeScript language service for JavaScript files.

The generated jsconfig.json is read by WebStorm.""",
}
