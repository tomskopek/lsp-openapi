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
vim.lsp.enable("openapi_goto_def")
```

The plugin ships `lsp/openapi_goto_def.lua`, which Neovim 0.11+ picks up automatically once the plugin is on the runtimepath. No `setup()` call needed.

### Local development

```lua
{
  dir = "~/dev/lsp-openapi",
  ft = "yaml",
}
```

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
└── lsp/
    └── openapi_goto_def.lua   # Neovim 0.11 LSP config (auto-discovered)
```
