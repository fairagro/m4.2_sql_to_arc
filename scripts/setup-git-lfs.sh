#!/usr/bin/env bash
# Product Git LFS overlay: local `git lfs install` + product-owned hooks.
#
# Installs / refreshes only:
#   .git/hooks/pre-push.d/10-git-lfs   (from scripts/git-lfs-hooks/pre-push.d/)
#   .git/hooks/post-{checkout,commit,merge}
#
# Does NOT replace the shared pre-push dispatcher or delete pre-push.d/50-quality.
# After `git lfs install --force` (may rewrite .git/hooks/pre-push), re-runs
# setup-git-hooks.sh to restore the dispatcher + 50-quality, then installs the
# LFS fragment again.
#
# Invoked from scripts/devcontainer-post-create.d/50-git-lfs.sh (T-late) and
# manually on host clones after shared setup-git-hooks.sh / uv sync.
# Sources live under scripts/git-lfs-hooks/ (product-owned), NOT under synced
# scripts/git-hooks/**. See docs/git-lfs.md.
#
# Usage (from any cwd):
#   ./scripts/setup-git-lfs.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOOKS_SOURCE_DIR="${REPO_ROOT}/scripts/git-lfs-hooks"
HOOKS_TARGET_DIR="${REPO_ROOT}/.git/hooks"
FRAGMENT_NAME="10-git-lfs"
source_fragment="${HOOKS_SOURCE_DIR}/pre-push.d/${FRAGMENT_NAME}"

echo "Setting up Git LFS hooks for repository..."

if ! command -v git-lfs >/dev/null 2>&1; then
  echo "Git LFS is not installed; attempting install..."
  if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update && sudo apt-get install -y git-lfs
  elif command -v brew >/dev/null 2>&1; then
    brew install git-lfs
  else
    echo "ERROR: could not install Git LFS automatically." >&2
    echo "Install manually: https://git-lfs.github.io/" >&2
    exit 1
  fi
fi

echo "Git LFS available: $(git lfs version)"

if [[ ! -d "${REPO_ROOT}/.git" ]]; then
  echo "ERROR: not a git worktree root: ${REPO_ROOT}" >&2
  exit 1
fi

if [[ ! -f "${source_fragment}" ]]; then
  echo "ERROR: missing ${source_fragment}" >&2
  exit 1
fi

# Repo-local only: Dev Container bind-mounts host ~/.gitconfig read-only.
# --force may overwrite .git/hooks/pre-push with the stock LFS hook — restore
# the shared dispatcher immediately after.
echo "Initializing Git LFS (local config)..."
(cd "${REPO_ROOT}" && git lfs install --local --skip-smudge --force)

echo "Re-ensuring shared pre-push dispatcher + 50-quality..."
bash "${REPO_ROOT}/scripts/setup-git-hooks.sh"

mkdir -p "${HOOKS_TARGET_DIR}/pre-push.d"
echo "Installing pre-push.d/${FRAGMENT_NAME}"
cp "${source_fragment}" "${HOOKS_TARGET_DIR}/pre-push.d/${FRAGMENT_NAME}"
chmod +x "${HOOKS_TARGET_DIR}/pre-push.d/${FRAGMENT_NAME}"

for hook in post-checkout post-commit post-merge; do
  source_hook="${HOOKS_SOURCE_DIR}/${hook}"
  target_hook="${HOOKS_TARGET_DIR}/${hook}"
  [[ -f "${source_hook}" ]] || continue

  if [[ -f "${target_hook}" ]] && cmp -s "${source_hook}" "${target_hook}"; then
    echo "Already up to date: ${hook}"
    continue
  fi

  # Backup only unknown foreign hooks — not our SoT and not stock `git lfs install` hooks.
  if [[ -f "${target_hook}" ]] &&
    ! grep -qE 'version-controlled and should be installed via|git lfs post-' "${target_hook}" 2>/dev/null; then
    echo "Backing up existing ${hook} hook to ${hook}.backup"
    cp "${target_hook}" "${target_hook}.backup"
  else
    echo "Installing ${hook} hook"
  fi

  cp "${source_hook}" "${target_hook}"
  chmod +x "${target_hook}"
done

echo ""
echo "Git LFS hooks setup complete."
echo "Installed:"
ls -la \
  "${HOOKS_TARGET_DIR}/pre-push" \
  "${HOOKS_TARGET_DIR}/pre-push.d/${FRAGMENT_NAME}" \
  "${HOOKS_TARGET_DIR}/pre-push.d/50-quality" \
  "${HOOKS_TARGET_DIR}/post-checkout" \
  "${HOOKS_TARGET_DIR}/post-commit" \
  "${HOOKS_TARGET_DIR}/post-merge" \
  2>/dev/null || true
echo ""
echo "Git LFS tracked files:"
(cd "${REPO_ROOT}" && git lfs ls-files) || true
