## Why

Devinfra [#58](https://github.com/fairagro/m4.2_middleware_devinfra/issues/58) replaced per-shell `load-env.sh` / bashrc mutation with `remoteEnv.PATH`, synced `scripts/bin/{k,d}`, and shared postCreate decrypt (file only). sql_to_arc still ships a product `scripts/load-env.sh` and leftover bashrc sourcing, which duplicates the shared contract and fights verbatim Dev Container sync.

## What Changes

- **Delete** product `scripts/load-env.sh` (no thin fork).
- Add product-owned `.devcontainer/product.env` with `MYPYPATH` and `CST_*` overlays (Compose `env_file`; not synced).
- Update product docs (`AGENTS.md`, `docs/git-lfs.md`) to point at remoteEnv + `product.env` / wrappers; drop load-env / bashrc guidance.
- Document removing any leftover `~/.bashrc` `source …/load-env.sh` after rebuild (manual; do not reintroduce bashrc patches from repo scripts).
- **BREAKING** (local DX only): interactive shells no longer auto-`source` decrypted `.env` / `.env.shell`; aliases/`ggshield` banner from load-env go away (use `k`/`d` wrappers and existing auth paths).

## Capabilities

### New Capabilities

_None — `skip_specs: true` (tooling / DX only; no domain-spec contract change)._

### Modified Capabilities

_None._

## Impact

- Product files: `scripts/load-env.sh` (removed), `.devcontainer/product.env` (added), `AGENTS.md`, `docs/git-lfs.md`; comment-only touch on `scripts/install-dev-hooks.sh` if needed.
- Already on `main` via sync (unchanged here): `remoteEnv.PATH`, optional Compose `product.env`, `scripts/bin/{k,d}`, shared postCreate SOPS decrypt.
- Do **not** hand-edit synced paths (`docs/synced-paths.yaml`).
- Related: product [#129](https://github.com/fairagro/m4.2_sql_to_arc/issues/129) (verbatim DC / `product.env`); this change supplies the env overlay slice.

## Non-goals

- Re-opening Devinfra sync PRs or editing synced `devcontainer.json` / Compose / `docs/devcontainer.md`.
- Auto-sourcing `.env` into every shell; bashrc token loading; restoring kubectl/docker shell aliases.
- Expanding shared postCreate to call product LFS install (tracked separately / Devinfra follow-ups).
