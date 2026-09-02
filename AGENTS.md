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
    ├── arctrl/            # arctrl Python library reference
    └── config-wrapper/    # ConfigWrapper / ConfigBase pattern

.cursor/                   # Cursor OpenSpec commands + skills (opsx-*)
.github/
├── prompts/               # GitHub Copilot OpenSpec prompts (opsx-*)
└── skills/                # GitHub Copilot OpenSpec skills

docs/
├── ai_workflow.md         # AI agent workflow documentation
└── sql_to_arc_database_views.md  # Authoritative DB view / schema contract

openspec/                  # OpenSpec source of truth + changes
├── config.yaml            # Project context for OpenSpec artifacts
├── specs/                 # Current behavior by domain
│   ├── principles/
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
├── load-env.sh                    # Per-shell env (PATH, aliases, SOPS); sourced from bashrc
├── uv-sync-dev.sh                 # One-time uv sync (devcontainer postCreate)
├── install-dev-hooks.sh           # One-time pre-commit + Git LFS hooks
├── import-public-gpg-keys.sh      # Import public_gpg_keys/*.asc (devcontainer / local)
├── setup-git-lfs.sh               # Git LFS hook installation
├── quality-check.sh               # Run all quality checks (pre-commit push stage)
├── quality-fix.sh                 # Run auto-formatters (ruff)
└── git-hooks/                     # Version-controlled hooks
    ├── pre-push          # Combined: Git LFS + pre-commit
    ├── post-checkout
    ├── post-commit
    └── post-merge

dev_environment/
├── start-demo.sh         # Start full local demo (DB + Converter + Mock API)
├── start-dev.sh          # Start with local DB, external API (needs sops)
├── compose.demo.yaml     # Docker services for demo
├── compose.dev.yaml      # Docker services for dev
└── config.dev.yaml       # Development configuration for the converter
```

## Important Commands

### Always use `uv` for Python

```bash
# Run tests for the converter
uv run pytest middleware/sql_to_arc/tests/ -v

# Run individual quality tools (never run quality-check.sh — it runs everything and is too slow)
uv run ruff check .
uv run ruff format .
uv run mypy middleware/sql_to_arc/
uv run pylint middleware/sql_to_arc/
uv run bandit -r middleware/sql_to_arc/src/

# Install all dependencies (including external shared/api_client via git)
uv sync --dev --all-packages
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

### Dev Container

| IDE | How to open |
| --- | --- |
| **VS Code** | **Reopen in Container** → `.devcontainer/devcontainer.json` |
| **Cursor** | **Dev Containers: Reopen in Container** → `.devcontainer/devcontainer.json` |

Shared image: `.devcontainer/Dockerfile` (pinned tools, **linux/amd64 only**) + DinD feature. `devcontainer.json` sets `--platform=linux/amd64`. One-time setup runs in `postCreateCommand` (`uv-sync-dev.sh`, `install-dev-hooks.sh`, `import-public-gpg-keys.sh`). Per-shell: `scripts/load-env.sh` (sourced from `~/.bashrc`).

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

**Cross-cutting domains:**

- **[`openspec/specs/principles/`](openspec/specs/principles/)** — Foundation contract and project values (start here).
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

**Setup Process**:

1. `scripts/load-env.sh` is sourced during development.
2. This script calls `scripts/setup-git-lfs.sh`.
3. Git LFS hooks are installed from `scripts/git-hooks/`.

**Files Tracked by LFS**: `*.sql` (configured in `.gitattributes`).

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

**Last Updated**: 2026-07-30
**Maintainer Notes**: Spec-driven workflow uses OpenSpec (`openspec/`). High-level architecture involves converting SQL views into ARC files.
