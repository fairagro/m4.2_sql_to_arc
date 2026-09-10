# AGENTS.md - Instructions for AI Assistants

This file contains critical context about the FAIRagro SQL-to-ARC Converter project for AI assistants (GitHub Copilot, Cursor, Claude, etc.).

## Tech Stack

| Component | Version | Details |
| --------- | ------- | ------- |
| Python | 3.12.14 | Primary language |
| PostgreSQL | 15.15 | Database |
| Docker | Latest | Containerization |
| Git LFS | 3.3.0+ | Large file storage |
| uv | Latest | Python package manager |
| arctrl | Latest | ARC manipulation library |
| OpenSpec | Latest | Spec-driven development (`openspec/` + `/opsx-*`) |

## Project Structure

```text
.agents/
└── skills/                # Agent Skills (agentskills.io standard)
    ├── arctrl/            # Shared first-party arctrl reference (synced from Devinfra)
    ├── config-wrapper/    # ConfigWrapper / ConfigBase pattern (local)
    ├── create-issue/      # `/create-issue` (synced)
    ├── issue-fixer/       # `/issue-fixer` (synced)
    ├── review-fixer/      # `/review-fixer` (synced)
    ├── gh/, docker/, hadolint/, uv/  # Vendor pins (`gh skill`; do not hand-edit)

.cursor/                   # Cursor OpenSpec commands + skills (opsx-*) + fixer commands
.cursor/BUGBOT.md          # Bugbot entry → docs/ai_review_policy.md
.github/
├── prompts/               # GitHub Copilot OpenSpec + fixer prompts
├── copilot-instructions.md  # Copilot → principles.global + review policy
└── skills/                # GitHub Copilot OpenSpec skills

docs/
├── ai_workflow.md         # AI agent workflow documentation
├── ai_review_policy.md    # Copilot/Bugbot policy (synced)
├── surface-quality-bar.global.md  # Default path→surface map (synced)
├── surface-quality-bar.md # Product path rows (local)
├── synced-paths.yaml      # Devinfra sync allowlist (synced — do not hand-edit)
├── git-lfs.md             # Product Git LFS overlay (install + Wave B compose)
├── quality.md / sync.md / devcontainer.md  # Synced Devinfra DX docs
└── sql_to_arc_database_views.md  # Authoritative DB view / schema contract

openspec/                  # OpenSpec source of truth + changes
├── principles.global.md   # Shared foundation (synced — do not hand-edit)
├── principles.md          # Product overlay (stack, modules, converter constraints)
├── config.yaml            # Project context for OpenSpec artifacts
├── specs/                 # Current behavior by domain
│   ├── principles/        # Behavioral RFC 2119 foundation (domain spec)
│   ├── configuration/
│   ├── demo-environment/
│   ├── tooling-consistency/
│   ├── sql-to-arc-conversion/
│   ├── arc-building/
│   ├── database-access/
│   └── api-upload/
└── changes/               # Active change proposals (delta specs)

middleware/
└── sql_to_arc/            # SQL to ARC converter (Core logic)
    ├── src/middleware/sql_to_arc/
    │   ├── main.py        # Entry point
    │   ├── mapper.py      # Database to ARC mapping logic
    │   └── config.py      # Configuration model
    └── tests/
        ├── unit/          # Unit tests for mapper and business logic
        └── integration/   # Integration tests with database

scripts/
├── ai/                            # m42-ai (synced): uv run --project scripts/ai m42-ai …
├── bin/gh, bin/git                # PATH wrappers + personal tokens (synced)
├── load-env.sh                    # Per-shell env (PATH, aliases, SOPS); product-local
├── load-versions-env.sh           # Synced versions.env loader
├── uv-sync-dev.sh                 # Product: uv sync --dev --all-packages
├── install-dev-hooks.sh           # Product: pre-commit + setup-git-hooks + setup-git-lfs
├── setup-git-hooks.sh             # Synced quality pre-push installer (no LFS)
├── setup-git-lfs.sh               # Product Git LFS overlay
├── devcontainer-post-create.sh    # Synced shared postCreate
├── import-public-gpg-keys.sh      # Product: public_gpg_keys/*.asc
├── quality-*.sh / CST runner      # Synced quality scripts
├── git-hooks/                     # Synced quality pre-push only (verbatim)
├── git-lfs-hooks/                 # Product: combined LFS+quality pre-push; LFS post-*

stubs/                             # Product-local arctrl/fable stubs until Devinfra #67

dev_environment/
├── start-demo.sh         # Start full local demo (DB + Converter + Mock API)
├── start-dev.sh          # Start with local DB, external API (needs sops)
├── compose.demo.yaml     # Docker services for demo
├── compose.dev.yaml      # Docker services for dev
└── config.dev.yaml       # Development configuration for the converter
```

**Principles split:** `openspec/principles.global.md` (synced shared foundation) +
`openspec/principles.md` (product overlay). Domain requirements remain under
`openspec/specs/principles/` — do not confuse the agent overlay with that
behavioral spec.

## Important Commands

### Always use `uv` for Python

```bash
# Run tests for the converter
uv run pytest middleware/sql_to_arc/tests/ -v

# Quality checks (synced: ruff.toml, mypy.ini, .pylintrc — see docs/quality.md)
# Never run quality-check.sh from agents — it runs everything and is too slow.
uv run ruff format --check --config ruff.toml middleware/
uv run ruff check --config ruff.toml middleware/
MYPYPATH=stubs:middleware/sql_to_arc/src \
  uv run mypy --config-file mypy.ini middleware/
uv run pylint --rcfile .pylintrc middleware/sql_to_arc
uv run bandit -r middleware/ -c .bandit -ll

# Install all dependencies (including external shared/api_client via git)
uv sync --dev --all-packages

# m42-ai (not a root uv workspace member)
uv run --project scripts/ai m42-ai --help
uv run --project scripts/ai m42-ai auth-status
```

### OpenSpec

```bash
openspec list --specs          # List domain specs
openspec validate --specs      # Validate main specs
openspec list                  # List active changes
openspec validate <change>     # Validate a change folder
```

In Cursor chat: `/opsx-explore`, `/opsx-propose`, `/opsx-apply`, `/opsx-archive`.
In GitHub Copilot: the matching `opsx-*` prompts under `.github/prompts/`.

### CI (Wave C)

Callers: `.github/workflows/feature-pull-request.yml`, `pre-release.yml`,
`release.yml` → Devinfra reusables (`docs/ci.md`). Temporary
`reusable-check-local.yml` omits Trivy licence scan until Devinfra #74 — do not
hand-edit synced trees. CQ pin SHA until Devinfra #72 merges (`mypy_path`).

Bake: `docker-bake.hcl` targets `sql_to_arc-base` + `sql_to_arc` (synced
`Dockerfile.product-app.base` + thin last stage).

### Dev Container

| IDE | How to open |
| --- | --- |
| **VS Code** | **Reopen in Container** → `.devcontainer/devcontainer.json` |
| **Cursor** | **Dev Containers: Reopen in Container** → `.devcontainer/devcontainer.json` |

Shared image: `.devcontainer/Dockerfile` (synced from Devinfra) + compose overlay.
`devcontainer.json` is product-owned (name / workspaceFolder / volumes). postCreate:
shared `devcontainer-post-create.sh` then product `uv-sync-dev.sh` /
`install-dev-hooks.sh` (hooks + LFS) / `import-public-gpg-keys.sh`. Per-shell:
`scripts/load-env.sh` (bashrc). Toolchain pins: `versions.env`.

### Development Environment

```bash
# Start a full local demo (including mock API, no secrets/mTLS required)
cd dev_environment
./start-demo.sh --build

# Start local database and run converter (requires decryption via sops)
cd dev_environment
./start-dev.sh --build

# View logs
docker compose logs -f

# Cleanup
docker compose down
```

## Architecture & Design

Before generating or modifying code, read the relevant OpenSpec domain under
`openspec/specs/`. Prefer an active change under `openspec/changes/` when one
exists for the work in progress.

**Agent entry / shared foundation:**

- **[`openspec/principles.global.md`](openspec/principles.global.md)** — Synced shared principles (do not hand-edit).
- **[`openspec/principles.md`](openspec/principles.md)** — Product overlay (stack, modules, converter constraints).
- **[`docs/ai_review_policy.md`](docs/ai_review_policy.md)** — Review policy (synced).
- **[`docs/synced-paths.yaml`](docs/synced-paths.yaml)** — Synced-path allowlist (do not patch in consumers).
- **[`docs/surface-quality-bar.global.md`](docs/surface-quality-bar.global.md)** +
  **[`docs/surface-quality-bar.md`](docs/surface-quality-bar.md)** — path→surface map.

**Cross-cutting domains:**

- **[`openspec/specs/principles/`](openspec/specs/principles/)** — Behavioral foundation contract (RFC 2119; start here for requirements).
- **[`openspec/specs/configuration/`](openspec/specs/configuration/)** — Config loading, env overrides, secrets.
- **[`openspec/specs/demo-environment/`](openspec/specs/demo-environment/)** — Local demo / deployment setup.
- **[`openspec/specs/tooling-consistency/`](openspec/specs/tooling-consistency/)** — VS Code, pre-commit, and CI must report identical results.

**Converter domains** (code under `middleware/sql_to_arc/`):

- **[`openspec/specs/sql-to-arc-conversion/`](openspec/specs/sql-to-arc-conversion/)** — Top-level workflow: workers, stats, CLI.
- **[`openspec/specs/arc-building/`](openspec/specs/arc-building/)** — ARC object construction (`mapper.py` + `builder.py`).
- **[`openspec/specs/database-access/`](openspec/specs/database-access/)** — DB access patterns, row models, SQL views.
- **[`openspec/specs/api-upload/`](openspec/specs/api-upload/)** — Upload to the Middleware API.

Each domain has `spec.md` (behavior). Domains with non-obvious architecture also keep `design.md` (current Key Decisions).

---

## Key Implementation Details

### External Dependencies

This project depends on `shared` and `api_client` libraries, which are hosted in a separate repository (`m4.2_advanced_middleware_api`). They are included via `uv` workspace sources pointing to Git.

### Git LFS Integration

Product overlay (not in Devinfra). See [`docs/git-lfs.md`](docs/git-lfs.md).

**Setup:** `scripts/install-dev-hooks.sh` (Dev Container `postCreate` / after
clone) installs commit-stage pre-commit, shared `setup-git-hooks.sh`, then
`setup-git-lfs.sh`, which copies `scripts/git-lfs-hooks/{pre-push,post-*}`
into `.git/hooks`. `load-env.sh` does **not** install LFS.

**Tracked:** `*.sql` (`.gitattributes`). **Wave B:** always re-apply
`setup-git-lfs.sh` after any shared `setup-git-hooks.sh` (shared installer
removes LFS `post-*` hooks).

## Security Notes

- DB passwords and API secrets should be managed via environment variables or `.env`.
- `client.key` is dynamically handled in container secrets (`tmpfs`).

## Code Quality Standards

Agents are expected to maintain high code quality by addressing issues reported by the project's configured tools: **Ruff, Pylance, MyPy, Pylint, and Bandit**.

- **Automatic Fixes**: Actively check for and fix code smells, warnings, and notices.
- **Real Fixes vs. Suppression**: Issues must be resolved with actual code changes. Using comments to suppress warnings (e.g., `# noqa`, `# type: ignore`, `# pylint: disable`) is an **option of last resort**.
- **When to Suppress**: Only suppress if a fix is technically impossible or would result in unnecessarily complex or unreadable code.
- **Comprehensive Coverage**: Fix all reported issues, including low-severity notices and warnings, not just critical errors.

## File Modifications Pattern

When editing files:

1. **Always check current state** - Use `read_file` to see current content.
2. **Review for quality** - Check the VS Code **Problems** tab (Pylance, Mypy, Ruff run continuously in the background). Only run individual tools (`uv run ruff check .`, `uv run mypy ...`) if the Problems tab is not available. Never run `./scripts/quality-check.sh` — it is too slow.
3. **Never modify `.git/` directly** - Use scripts instead.
4. **Format and test after changes** - Run `uv run ruff format .` to auto-format, then `uv run pytest` to verify.

---

**Last Updated**: 2026-09-08
**Maintainer Notes**: Spec-driven workflow uses OpenSpec (`openspec/`). High-level architecture involves converting SQL views into ARC files. AI review / fixer stack synced from Devinfra Wave A (see issue #93).
