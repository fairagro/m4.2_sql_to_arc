## 1. Product env overlay

- [x] 1.1 Add `.devcontainer/product.env` with `MYPYPATH=stubs:middleware/sql_to_arc/src`, `CST_BAKE_TARGET=sql_to_arc`,
      `CST_IMAGE_TAG=sql-to-arc:test`, `CST_CONFIG=docker/container-structure-tests`
- [x] 1.2 Confirm Compose still references optional `product.env` (no synced-file edits)

## 2. Drop load-env

- [x] 2.1 Delete `scripts/load-env.sh`
- [x] 2.2 Grep product-owned paths for remaining load-env / bashrc-source instructions; fix comments in
      `scripts/install-dev-hooks.sh` if needed

## 3. Product docs

- [x] 3.1 Update `AGENTS.md`: remove load-env from tree / Wave B / Dev Container notes; point PATH and overlays at
      `remoteEnv` + `product.env` / `scripts/bin`
- [x] 3.2 Update `docs/git-lfs.md`: drop load-env “not involved” framing; note bashrc-free contract + leftover bashrc
      cleanup after rebuild
- [x] 3.3 Do **not** edit synced docs (`docs/devcontainer.md`, `docs/sync.md`, `docs/conventions.md`)

## 4. Validate

- [x] 4.1 `openspec validate adopt-bashrc-free-shell` (expect pass with `skip_specs`)
- [x] 4.2 Confirm no accidental edits under `docs/synced-paths.yaml` allowlist trees
