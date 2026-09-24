#!/usr/bin/env bash
# Product postCreate drop-in (T-late): restore Git LFS overlay only.
# Shared postCreate already ran uv sync, pre-commit, and setup-git-hooks.sh.
# Hard-fail if this script is not executable or exits non-zero.
# See docs/git-lfs.md and docs/devcontainer.md (devcontainer-post-create.d).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
exec bash "${REPO_ROOT}/scripts/setup-git-lfs.sh"
