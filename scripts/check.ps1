# Run the three verification tools this project is built around:
#   uvx ruff check --fix .   (style)
#   uvx ty check             (types)
#   uv run pytest            (tests)
#
# uv keeps its tool and cache directories under %APPDATA% / %LOCALAPPDATA% by
# default, which a workspace-write sandbox cannot write to. Pointing them inside
# the repo keeps the commands exactly as documented while still running sandboxed.

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$env:UV_CACHE_DIR = Join-Path $root '.uv/cache'
$env:UV_TOOL_DIR = Join-Path $root '.uv/tools'
$env:UV_TOOL_BIN_DIR = Join-Path $root '.uv/bin'
New-Item -ItemType Directory -Force -Path $env:UV_CACHE_DIR, $env:UV_TOOL_DIR, $env:UV_TOOL_BIN_DIR | Out-Null

Push-Location $root
try {
    uv sync --quiet
    uvx ruff check --fix .
    uvx ty check
    uv run pytest
}
finally {
    Pop-Location
}
