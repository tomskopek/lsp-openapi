# lsp-openapi

A tiny, zero-dependency LSP server that adds go-to-definition for OpenAPI YAML specs:

- `operationId: foo` -> jumps to the matching `def foo(` controller in the workspace (camelCase -> snake_case).
- `$ref: "./other.yaml#/components/schemas/Foo"` -> jumps to that key in the referenced file.
- `$ref: "#/components/schemas/Foo"` -> same, within the current file.

Written in pure Python over raw JSON-RPC. No pip install needed.

## Requirements

- `python3` on `$PATH`
- `rg` (ripgrep) on `$PATH` — used for the `operationId` search
- Neovim 0.11+ for the bundled config (any LSP client works, see below)

## Install (Neovim, lazy.nvim)

```lua
{
  "tomskopek/lsp-openapi",
  ft = "yaml",
}
```

Then activate it in your LSP config:

```lua
vim.lsp.enable("lsp_openapi")
```

The plugin ships `lsp/lsp_openapi.lua`, which Neovim 0.11+ picks up automatically once the plugin is on the runtimepath. No `setup()` call needed.

### Local development

```lua
{
  dir = "~/dev/lsp-openapi",
  ft = "yaml",
}
```

## Install (Cursor / VS Code)

Grab the latest `.vsix` from GitHub Releases and install it via the CLI:

```sh
curl -L -o /tmp/lsp-openapi.vsix https://github.com/tomskopek/lsp-openapi/releases/latest/download/lsp-openapi.vsix
cursor --install-extension /tmp/lsp-openapi.vsix   # or: code --install-extension
```

Or install through the UI: Cmd+Shift+P → `Extensions: Install from VSIX...` → pick the downloaded file.

Restart the editor (or Cmd+Shift+P → "Developer: Reload Window") and the extension activates on any `.yaml` file.

If `python3` isn't on your PATH under the name `python3`, set it in `settings.json`:

```json
"lspOpenapi.python": "/full/path/to/python3"
```

### Building the .vsix from source

If you need a fresh build (or you're contributing):

```sh
cd vscode
npm install
npm run package
```

That produces `lsp-openapi-<version>.vsix` in the `vscode/` directory.

## Install (other editors)

Point your LSP client at `server.py`:

- Command: `python3 /path/to/lsp-openapi/server.py`
- Filetypes: `yaml`
- Root markers: `.git`

## What gets resolved

### operationId

```yaml
paths:
  /things:
    get:
      operationId: listThings   # gd here -> def list_things(...) in your controllers
```

The server runs `rg --fixed-strings "def <snake_case>("` from the workspace root, excluding `**/generated/**` and `**/.claude/**`.

### $ref

```yaml
paths:
  /things/listThings:
    $ref: "./things-endpoints.yaml#/endpoints/ListThings"
    #     ^ gd anywhere on this line jumps to the key in the target file
```

Supports:

- Cross-file refs: `./other.yaml#/path/to/key`
- Same-file refs: `#/path/to/key`
- Single or double quotes, or unquoted
- JSON-pointer escapes (`~1` -> `/`, `~0` -> `~`)

Limitations: plain mapping keys only — no list-item refs, anchors, or HTTP(S) refs.

## Layout

```
lsp-openapi/
├── README.md
├── server.py                  # the LSP server
├── lsp/
│   └── lsp_openapi.lua        # Neovim 0.11 LSP config (auto-discovered)
└── vscode/
    ├── package.json           # VS Code / Cursor extension manifest
    └── src/extension.ts       # spawns server.py via vscode-languageclient
```
