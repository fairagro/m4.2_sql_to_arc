# Adopt Devinfra Wave B — Proposal

## Why

Issue [#94](https://github.com/fairagro/m4.2_sql_to_arc/issues/94): adopt shared
Devinfra **Wave B** (Dev DX — scripts, hooks, Dev Container, quality fragments)
after Wave A. Devinfra #7–#10 / #28 / #39 are closed. Harvester pilot lock-ins
([#168](https://github.com/fairagro/m4.2_middleware_harvester/issues/168) /
[#180](https://github.com/fairagro/m4.2_middleware_harvester/pull/180)) apply
here. This repo still needs a **product-local Git LFS** overlay for `*.sql`
(Devinfra removed shared LFS — #39; docs in `docs/git-lfs.md` from #97).

**Pinned Devinfra SHA:** `a9740d119d0fbe96a813650121db2fab7b2e6136` (main at
lock-in).

## What Changes

- Sync Wave B allowlisted paths from the pin (`docs/synced-paths.yaml` allow
  list): quality scripts/CST, `setup-git-hooks.sh`, `scripts/bin/git`,
  `load-versions-env.sh`, `devcontainer-post-create.sh`, `versions.env`,
  shared Dockerfile, quality fragments (`ruff.toml`, `mypy.ini`, `.pylintrc`,
  `.bandit`, markdown/prettier, `.vscode/settings.json`), sync/quality docs,
  Renovate artifacts if not already present, refresh Wave A surfaces as needed.
- **Product overlays:** thin `.devcontainer/devcontainer.json`; product-owned
  `.pre-commit-config.yaml` (header + path overlays per #63 lock-in);
  `install-dev-hooks.sh` / `uv-sync-dev.sh` / `load-env.sh`; **Git LFS**
  (`setup-git-lfs.sh`, LFS `post-*`, combined `pre-push`: LFS then shared
  quality); `import-public-gpg-keys.sh`; keep `update-apk-dependencies.sh`
  until Devinfra #52/#68.
- Align root `pyproject.toml` with fragment-based quality (drop duplicate
  tool tables where docs require).
- Add product `stubs/` (`arctrl` / `fable_library`, plus Table.composite_cell)
  and wire `MYPYPATH` / `pyrightconfig.json` `stubPath` (harvester #180 parity;
  Devinfra #67 later).
- Add product `docker-bake.hcl` for CST (Bake-only shared runner); host
  `package.json` / lock mirroring markdown pins.
- Verify quality-check / hooks smoke in Dev Container assumptions.

### Non-goals

- Wave C (reusable CI `uses:`).
- Hand-editing synced paths after adopt.
- Patching synced `devcontainer-post-create.sh` for `--all-packages` (track
  #56; product wrapper only).
- Moving APK updater or shared `load-env` into Devinfra (upstream issues).

## Capabilities

### New Capabilities

- _none — `skip_specs: true`._ Tooling/DX adoption; converter domain behaviour
  unchanged.

### Modified Capabilities

- _none._

## Impact

- **Synced:** Devinfra Wave B allowlist @ pin.
- **Local:** LFS overlay, thin DC overlay, pre-commit ownership, product
  install wrappers, AGENTS/`docs/git-lfs.md`.
- **Fleet:** same lock-ins as harvester pilot; OpenSpec change required
  (user override of issue-fixer no-opsx rule; see Devinfra #54).
