# Adopt Devinfra Wave B — Tasks

Parity checklist vs harvester
[#180](https://github.com/fairagro/m4.2_middleware_harvester/pull/180) / issue
[#94](https://github.com/fairagro/m4.2_sql_to_arc/issues/94). Wave C (#95)
deferred (reusable CI `uses:` / full Bake base).

## 1. Pin and sync

- [x] 1.1 Branch from `main`; pin `a9740d119d0fbe96a813650121db2fab7b2e6136`
- [x] 1.2 Sync Wave B allowlist paths from pin (quality scripts, hooks installer,
      `bin/git`, versions/load-versions, post-create, Dockerfile, fragments,
      docs/sync+quality+devcontainer, synced-paths.yaml, renovate if missing)
- [x] 1.3 Refresh already-synced Wave A paths that changed on pin
- [x] 1.4 Keep product LFS sources **outside** synced `scripts/git-hooks/**`
      (`scripts/git-lfs-hooks/` + `setup-git-lfs.sh`)

## 2. Product overlays (harvester parity)

- [x] 2.1 Thin `.devcontainer/devcontainer.json` + compose; `.env` → symlink
      `versions.env`
- [x] 2.2 Product `.pre-commit-config.yaml` (ownership header; MYPYPATH incl.
      `stubs`; pylint package path; OpenSpec markdownlint globs; CST Bake)
- [x] 2.3 Combined `pre-push` in `scripts/git-lfs-hooks/` (LFS then synced
      quality); `install-dev-hooks` = shared hooks then `setup-git-lfs`
- [x] 2.4 Keep `load-env.sh`, `uv-sync-dev.sh`, `import-public-gpg-keys.sh`,
      `update-apk-dependencies.sh`; postCreate extras without patching synced
      post-create
- [x] 2.5 `.vscode/settings.json` **verbatim**; `pyrightconfig.json` with
      `stubPath` + `extraPaths` (#57 / #64)
- [x] 2.6 `stubs/` (`arctrl` / `fable_library` + Table.composite_cell) +
      `stubs/README.md` until Devinfra #67
- [x] 2.7 Product `docker-bake.hcl` + pre-commit CST env (Wave B; not Wave C)
- [x] 2.8 `package.json` / `package-lock.json` + `.gitignore` `node_modules/` /
      `!.devcontainer/.env`
- [x] 2.9 Align product CI (`python-quality.yml`) MYPYPATH / fragment flags
      (not reusable `uses:` — that is Wave C)
- [x] 2.10 Update `AGENTS.md` / `README.md` / `docs/git-lfs.md` for Wave B +
      LFS + stubs

## 3. Root quality alignment

- [x] 3.1 Align `pyproject.toml` with fragment SoT (remove duplicate tool tables
      per `docs/quality.md` where safe)
- [x] 3.2 CST Bake target wired (monolith Dockerfile until Wave C base)

## 4. Verify

- [x] 4.1 `bash -n` on touched scripts; hook install order smoke
- [x] 4.2 Focused `uv run pytest` unit; `ruff check`; `MYPYPATH=stubs:… mypy`
      (clean)
- [ ] 4.3 Full `quality-check.sh` / Dev Container rebuild / CST bake — user
      after commit
- [x] 4.4 Diff synced paths vs pin (overlays excepted); golden-rule audit +
      harvester #180 gap fill
