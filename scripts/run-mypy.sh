#!/usr/bin/env bash
# Run mypy on workspace packages (see pyproject.toml mypy_path).

set -euo pipefail

cd "$(dirname "$0")/.."

exec uv run mypy -p middleware.sql_to_arc
