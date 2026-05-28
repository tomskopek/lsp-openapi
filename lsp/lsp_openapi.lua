-- Auto-discovered by Neovim 0.11+ when this plugin is on the runtimepath.
-- Activate via `vim.lsp.enable("lsp_openapi")` in your config.

local this_file = debug.getinfo(1, "S").source:sub(2)
local plugin_root = vim.fn.fnamemodify(this_file, ":p:h:h")

return {
  cmd = { "python3", plugin_root .. "/server.py" },
  filetypes = { "yaml" },
  root_markers = { ".git" },
}
