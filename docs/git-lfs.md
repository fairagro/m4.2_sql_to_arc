# Git LFS (product overlay)

This repo tracks large `*.sql` files with **Git LFS** (see `.gitattributes`). Shared Devinfra does **not** ship an LFS
layer; Wave B’s `scripts/setup-git-hooks.sh` installs only a quality `pre-push` and **removes** legacy LFS `post-*`
hooks. This product therefore owns an LFS overlay that must stay in place before and after Wave B.

## Who installs what

| Step                                  | Owner                    | Script / hook                                                         |
| ------------------------------------- | ------------------------ | --------------------------------------------------------------------- |
| One-time Dev Container / clone setup  | Product                  | `scripts/install-dev-hooks.sh` (`postCreateCommand`)                  |
| `pre-commit` commit-stage hook        | Product (via pre-commit) | `pre-commit install --hook-type pre-commit`                           |
| Git LFS local init + LFS hooks        | Product                  | `scripts/setup-git-lfs.sh`                                            |
| Quality `pre-push` (synced, verbatim) | Devinfra                 | `scripts/git-hooks/pre-push`                                          |
| Combined `pre-push` + LFS `post-*`    | Product                  | `scripts/git-lfs-hooks/*` — **outside** synced `scripts/git-hooks/**` |

Shell init is **bashrc-free** (`remoteEnv.PATH` + optional `.devcontainer/product.env`). It does **not** install Git
LFS. After a Dev Container rebuild, remove any leftover `source …/scripts/load-env.sh` line from `~/.bashrc` if present.

Manual re-install after clone (or if hooks were overwritten):

```bash
./scripts/install-dev-hooks.sh
# or LFS only:
./scripts/setup-git-lfs.sh
```

## Hook ownership (today)

```text
.git/hooks/pre-commit     ← pre-commit (commit stage)
.git/hooks/pre-push       ← scripts/git-lfs-hooks/pre-push
                              (LFS → scripts/git-hooks/pre-push quality)
.git/hooks/post-checkout  ← scripts/git-lfs-hooks/post-checkout (git lfs)
.git/hooks/post-commit    ← scripts/git-lfs-hooks/post-commit (git lfs)
.git/hooks/post-merge     ← scripts/git-lfs-hooks/post-merge (git lfs)
```

## Wave B composition (design lock-in)

When adopting Devinfra shared hooks:

1. **Keep** `scripts/setup-git-lfs.sh` and sources under `scripts/git-lfs-hooks/` as this product’s overlay (other fleet
   repos may not need LFS). Never put LFS hooks under allowlisted `scripts/git-hooks/**`.
2. **Never** run Devinfra `setup-git-hooks.sh` alone and stop. That script explicitly deletes LFS `post-*` hooks. Always
   run `./scripts/setup-git-lfs.sh` **after** any shared hook installer, or fold that order into `install-dev-hooks.sh`.
3. Prefer **compose**, not a fork of the quality `pre-push`:
   - Keep **LFS `git lfs pre-push` first** (required for `*.sql`).
   - Then exec the synced Devinfra `scripts/git-hooks/pre-push` (stdin buffering / `uv run pre-commit` as Wave B ships
     it).
4. Document any Wave B adopt PR with the invariant: _LFS overlay re-applied after shared hook sync_.

Wave B adopt (`install-dev-hooks.sh`) runs `setup-git-hooks.sh` then `setup-git-lfs.sh` so the overlay always wins after
shared hook install.
