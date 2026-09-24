# Git LFS (product overlay)

This repo tracks large `*.sql` files with **Git LFS** (see `.gitattributes`). Shared Devinfra does **not** ship an LFS
layer. Shared `scripts/setup-git-hooks.sh` installs a **pre-push dispatcher** plus `pre-push.d/50-quality` and leaves
foreign `pre-push.d` fragments and LFS `post-*` hooks alone. This product owns the LFS overlay.

## Who installs what

| Step                                   | Owner                    | Script / hook                                                              |
| -------------------------------------- | ------------------------ | -------------------------------------------------------------------------- |
| Dev Container create/rebuild           | Shared + product drop-in | `devcontainer-post-create.sh` → `devcontainer-post-create.d/50-git-lfs.sh` |
| Host / manual clone (optional glue)    | Product                  | `scripts/install-dev-hooks.sh`                                             |
| `pre-commit` commit-stage hook         | Shared postCreate / glue | `pre-commit install --hook-type pre-commit`                                |
| Dispatcher + `pre-push.d/50-quality`   | Devinfra                 | `scripts/setup-git-hooks.sh` / `scripts/git-hooks/`                        |
| `pre-push.d/10-git-lfs` + LFS `post-*` | Product                  | `scripts/setup-git-lfs.sh` / `scripts/git-lfs-hooks/`                      |

Shell init is **bashrc-free** (`remoteEnv.PATH` + optional `.devcontainer/product.env`). It does **not** install Git
LFS. After a Dev Container rebuild, remove any leftover `source …/scripts/load-env.sh` line from `~/.bashrc` if present.

Manual re-install after clone (or if hooks were overwritten):

```bash
./scripts/setup-git-lfs.sh
# or full host repair:
./scripts/install-dev-hooks.sh
```

## Hook ownership (today)

```text
.git/hooks/pre-commit              ← pre-commit (commit stage)
.git/hooks/pre-push                ← scripts/git-hooks/pre-push (dispatcher)
.git/hooks/pre-push.d/10-git-lfs   ← scripts/git-lfs-hooks/pre-push.d/10-git-lfs
.git/hooks/pre-push.d/50-quality   ← scripts/git-hooks/pre-push.d/50-quality
.git/hooks/post-checkout           ← scripts/git-lfs-hooks/post-checkout (git lfs)
.git/hooks/post-commit             ← scripts/git-lfs-hooks/post-commit (git lfs)
.git/hooks/post-merge              ← scripts/git-lfs-hooks/post-merge (git lfs)
```

On `git push`, the dispatcher runs `pre-push.d/*` in lexicographic order: **LFS then quality**.

## Product rules

1. Keep LFS sources under `scripts/git-lfs-hooks/` (outside synced `scripts/git-hooks/**`).
2. Register LFS pre-push logic as **`pre-push.d/10-git-lfs`** — never replace the shared dispatcher wholesale.
3. `setup-git-lfs.sh` is idempotent: refreshes only the product fragment and flat LFS `post-*`; after
   `git lfs install --force` it re-runs `setup-git-hooks.sh` so the dispatcher and `50-quality` stay intact.
4. Dev Container restore is the T-late drop-in `scripts/devcontainer-post-create.d/50-git-lfs.sh` (calls
   `setup-git-lfs.sh` only). Do not hard-code product scripts into synced `devcontainer-post-create.sh`.
