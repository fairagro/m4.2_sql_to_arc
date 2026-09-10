# Adopt Devinfra Wave B — Design

## Context

Issue [#94](https://github.com/fairagro/m4.2_sql_to_arc/issues/94); explore
lock-ins (2026-09-10): pin **now** @ `a9740d119d0fbe96a813650121db2fab7b2e6136`;
**full** adopt; **product-local LFS**; **use OpenSpec** (issue-fixer opsx ban
is wrong — Devinfra [#54](https://github.com/fairagro/m4.2_middleware_devinfra/issues/54)).
Pilot comment on #94 = harvester Wave B defaults (do not re-litigate). Parity
target: harvester PR [#180](https://github.com/fairagro/m4.2_middleware_harvester/pull/180).

## Goals / Non-Goals

**Goals:** Dev DX matches Devinfra + harvester Wave B pilot; only documented
overlays remain local (including LFS + stubs). Manual adopt now (not wait for
#13).

**Non-Goals:** Wave C (reusable CI `uses:` / full product-app Bake base
adoption); forking synced files; removing LFS for `*.sql`.

## Decisions

### D1 — Pin and full sync

Copy allowlisted Wave B (+ refreshed Wave A) paths from Devinfra at
`a9740d119d0fbe96a813650121db2fab7b2e6136`. Do not hand-edit after copy.

### D2 — Product-owned vs synced (pilot + golden rule)

Fleet golden rule: **never** edit allowlisted synced files in the product.
Prefer generic Devinfra → else `.global`+local / overlay path → else document
upstream.

| Path | Ownership |
| ---- | --------- |
| `.devcontainer/Dockerfile` | Synced verbatim |
| `.devcontainer/devcontainer.json` | Product thin overlay (#65) |
| `.devcontainer/.env` | Symlink → `../versions.env` |
| `.pre-commit-config.yaml` | **Product-owned last-resort** until Devinfra [#63](https://github.com/fairagro/m4.2_middleware_devinfra/issues/63); ownership header required |
| `scripts/git-hooks/pre-push` | Synced **verbatim** (quality only) |
| `scripts/git-lfs-hooks/*`, `setup-git-lfs.sh` | Product LFS overlay (outside allowlist) |
| `ruff.toml` / `mypy.ini` / `.pylintrc` / `.bandit` | Synced; overlays via hook/CI args (do **not** patch `.pylintrc` for lxml — n/a here) |
| `.vscode/settings.json` | Synced **verbatim**; product paths in `pyrightconfig.json` until [#57](https://github.com/fairagro/m4.2_middleware_devinfra/issues/57) / [#64](https://github.com/fairagro/m4.2_middleware_devinfra/issues/64) |
| `stubs/` | Product-local until Devinfra [#67](https://github.com/fairagro/m4.2_middleware_devinfra/issues/67) (`arctrl`/`fable_library` + Table.composite_cell) |
| `docker-bake.hcl` | Product-local CST Bake target (Wave B parity with harvester; full Bake base = Wave C) |
| `package.json` / `package-lock.json` | Product mirror of markdown toolchain pins (`versions.env`) for host clones |

### D3 — LFS compose

1. `setup-git-hooks.sh` (synced) installs quality `pre-push` and **removes**
   LFS `post-*` if present.
2. Always run `./scripts/setup-git-lfs.sh` **after** shared hook setup
   (installs from `scripts/git-lfs-hooks/`).
3. Combined `pre-push` (product): buffer stdin → `git lfs pre-push` → exec
   synced `scripts/git-hooks/pre-push`.
4. `install-dev-hooks.sh` (product): uv-sync repair → pre-commit install →
   `setup-git-hooks.sh` → `setup-git-lfs.sh`.

### D4 — Dev Container

Adopt compose-based Devinfra layout with product name / workspaceFolder /
volume `source=` / `remoteEnv` PATH / postStart `load-env`. postCreate calls
synced `devcontainer-post-create.sh` then product extras (gpg import, LFS,
`--all-packages` via wrapper — not by editing synced post-create).

### D5 — Stubs + MYPYPATH (harvester parity)

Fleet products that adopt Wave B use a root `stubs/` tree + `MYPYPATH=stubs:…`
in pre-commit and product CI. Incomplete `__getattr__ -> Any` stubs silence
`import-untyped` without editing synced `mypy.ini`. sql_to_arc keeps
`arctrl`/`fable_library` (shared) plus `arctrl.py.Core.Table.composite_cell`
(product import). No `owslib`/`rdflib` stubs (unused here).

### D6 — `skip_specs: true`

Tooling adoption only.

## Risks

- Blind `rsync --delete` of `scripts/git-hooks/` must not touch
  `scripts/git-lfs-hooks/`.
- Shared post-create `uv sync` without `--all-packages` → product wrapper (#56).
- Stale `GH_TOKEN` shadow (#69) — document workaround only.
- Synced `pytestArgs: ["scripts/ai/tests"]` may skew Test Explorer until #57.
- Product `docker-bake.hcl` builds monolith `Dockerfile.sql_to_arc` until Wave C
  product-app base.

## Migration

1. Branch `issue-94-adopt-devinfra-wave-b` from `main`.
2. Sync + overlays + LFS compose (hooks outside allowlist) + stubs + Bake CST.
3. Smoke quality-check / pytest / hook install.
4. Draft PR `Fixes #94`.
