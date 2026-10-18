#!/usr/bin/env bash
# Run the three verification tools this project is built around:
#   uvx ruff check --fix .   (style)
#   uvx ty check             (types)
#   uv run pytest            (tests)
#
# uv keeps its tool and cache directories outside the project by default;
# pointing them inside the repo keeps every run self-contained.

set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export UV_CACHE_DIR="$root/.uv/cache"
export UV_TOOL_DIR="$root/.uv/tools"
export UV_TOOL_BIN_DIR="$root/.uv/bin"
mkdir -p "$UV_CACHE_DIR" "$UV_TOOL_DIR" "$UV_TOOL_BIN_DIR"

cd "$root"
uv sync --quiet
uvx ruff check --fix .
uvx ty check
uv run pytest
