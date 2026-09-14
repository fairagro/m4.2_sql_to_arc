## 1. Product env overlay

- [ ] 1.1 Add `.devcontainer/product.env` with `MYPYPATH=stubs:middleware/sql_to_arc/src`, `CST_BAKE_TARGET=sql_to_arc`, `CST_IMAGE_TAG=sql-to-arc:test`, `CST_CONFIG=docker/container-structure-tests`
- [ ] 1.2 Confirm Compose still references optional `product.env` (no synced-file edits)

## 2. Drop load-env

- [ ] 2.1 Delete `scripts/load-env.sh`
- [ ] 2.2 Grep product-owned paths for remaining load-env / bashrc-source instructions; fix comments in `scripts/install-dev-hooks.sh` if needed

## 3. Product docs

- [ ] 3.1 Update `AGENTS.md`: remove load-env from tree / Wave B / Dev Container notes; point PATH and overlays at `remoteEnv` + `product.env` / `scripts/bin`
- [ ] 3.2 Update `docs/git-lfs.md`: drop load-env “not involved” framing; note bashrc-free contract + leftover bashrc cleanup after rebuild
- [ ] 3.3 Do **not** edit synced docs (`docs/devcontainer.md`, `docs/sync.md`, `docs/conventions.md`)

## 4. Validate

- [ ] 4.1 `openspec validate adopt-bashrc-free-shell` (expect pass with `skip_specs`)
- [ ] 4.2 Confirm no accidental edits under `docs/synced-paths.yaml` allowlist trees
