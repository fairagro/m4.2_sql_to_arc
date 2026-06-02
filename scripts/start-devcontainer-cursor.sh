#!/usr/bin/env bash
#
# Open this repository in a Dev Container via DevPod + Cursor.
#
# Cursor has no built-in "Reopen in Container" (unlike VS Code). DevPod builds
# the devcontainer and connects Cursor over SSH — equivalent to VS Code's flow,
# where load-env.sh runs inside the container after it starts (via postCreateCommand).
#
# Usage:
#   ./scripts/start-devcontainer-cursor.sh
#   ./scripts/start-devcontainer-cursor.sh --recreate
#   ./scripts/start-devcontainer-cursor.sh --reset
#

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"
devcontainer_path=".devcontainer/cursor/devcontainer.json"

extra_args=()
for arg in "$@"; do
    case "$arg" in
        --recreate | --reset)
            extra_args+=("$arg")
            ;;
        -h | --help)
            sed -n '2,14p' "$0" | sed 's/^# \?//'
            exit 0
            ;;
        *)
            echo "ERROR: Unknown argument: $arg" >&2
            echo "Run with --help for usage." >&2
            exit 1
            ;;
    esac
done

if ! command -v devpod &>/dev/null; then
    echo "ERROR: devpod not found in PATH. Install DevPod: https://devpod.sh/docs/getting-started/install" >&2
    exit 1
fi

if ! docker info &>/dev/null; then
    echo "ERROR: Docker is not running or not reachable." >&2
    exit 1
fi

echo "==> Configuring DevPod IDE: cursor"
devpod ide use cursor

echo "==> Starting DevPod workspace (devcontainer: ${devcontainer_path})"
devpod up "${repo_root}" \
    --devcontainer-path "${devcontainer_path}" \
    --ide cursor \
    "${extra_args[@]}"

echo ""
echo "==> Done. Cursor should open the workspace in the Dev Container."
echo "    Environment setup (hooks, uv sync, secrets) runs via scripts/load-env.sh inside the container."
