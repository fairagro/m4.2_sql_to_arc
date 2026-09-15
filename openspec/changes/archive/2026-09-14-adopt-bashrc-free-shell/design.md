## Context

See `proposal.md` for why. On `main` today: synced `devcontainer.json` already sets `remoteEnv.PATH` (`.venv/bin` +
`scripts/bin`); Compose optionally loads `.devcontainer/product.env`; shared `scripts/devcontainer-post-create.sh`
decrypts `.env.integration.enc` → `.env` without bashrc; `scripts/bin/{k,d}` replace aliases. Product still owns
`scripts/load-env.sh` (PATH, MYPYPATH/CST_*, aliases, ggshield banner, SOPS + auto-source). Some Dev Container volumes
retain a leftover `~/.bashrc` `source …/load-env.sh`.

Golden rule: do not hand-edit synced paths.

## Goals / Non-Goals

**Goals:**

- Align product DX with the bashrc-free fleet contract.
- Keep product-only env overlays (`MYPYPATH`, `CST_*`) via `product.env`.
- Clear product docs so agents/humans stop pointing at load-env / bashrc.

**Non-Goals:**

- Changing converter runtime config (`SQL_TO_ARC_*` / ConfigWrapper).
- Editing synced Dev Container JSON/Compose/docs.
- Automating bashrc cleanup inside the image build (volume state is operator-owned).

## Decisions

1. **Delete `scripts/load-env.sh` entirely — not a thin overlay** — reasoning: issue ask prefers delete; synced docs
   deprecate forked blobs; the only remaining deltas fit `product.env` / CI. A stub would invite re-growth.

2. **Product overlays only in `.devcontainer/product.env`** — reasoning: Compose already has `env_file: product.env`
   (`required: false`); synced contract places `MYPYPATH` / `CST_*` there. Values match former load-env defaults:
   `stubs:middleware/sql_to_arc/src`, `sql_to_arc`, `sql-to-arc:test`, `docker/container-structure-tests`.

3. **No repo script to rewrite `~/.bashrc`** — reasoning: fleet contract forbids bashrc mutation; leftover source lines
   are volume debt. Document one-line removal in product docs after rebuild.

4. **Accept no auto-`source` of `.env` in interactive shells** — reasoning: matches Devinfra postCreate “file only”;
   tokens stay on `scripts/bin` wrappers / `set-dev-tokens.sh`. Integration secrets remain on disk for Docker
   `--env-file` / explicit use.

5. **`skip_specs: true`** — reasoning: no openspec domain REQUIREMENTS change; tooling/DX only.

## Risks / Trade-offs

- **[Risk] Developers expect GITLAB_API_TOKEN in every new shell** → Mitigation: document that `.env` is written by
  postCreate; export/`set -a source` only when needed; prefer wrapper tokens for `gh`/`git`.
- **[Risk] Missing `product.env` after rebuild → CST/mypy path drift** → Mitigation: commit `product.env` in-repo (not
  synced); Compose `required: false` still allows empty absences but this product needs the file.
- **[Risk] Overlap with #129** → Mitigation: this PR only adds env overlay + drops load-env; does not re-litigate
  verbatim JSON sync.

## Migration Plan

1. Land `product.env` + delete load-env + doc updates on issue branch.
2. User commits/pushes; draft PR with `Fixes #126`.
3. After merge: rebuild Dev Container; remove leftover bashrc `source` line if present; confirm `which k d` and
   `echo $MYPYPATH` / CST vars in a new IDE terminal.
4. Rollback: restore `load-env.sh` from git history (not recommended once fleet is bashrc-free).
