# AGENTS.md - Instructions for AI Assistants

This file contains critical context about the FAIRagro SQL-to-ARC Converter project for AI assistants (GitHub Copilot, Claude, etc.).

## 📋 Tech Stack

| Component | Version | Details |
| --------- | ------- | ------- |
| Python | 3.12.12 | Primary language |
| PostgreSQL | 15.15 | Database |
| Docker | Latest | Containerization |
| Git LFS | 3.3.0+ | Large file storage |
| uv | Latest | Python package manager |
| arctrl | Latest | ARC manipulation library |

## 📁 Project Structure

```text
.agents/
└── skills/                # Agent Skills (agentskills.io standard)
    ├── arctrl/            # arctrl Python library reference
    ├── config-wrapper/    # ConfigWrapper / ConfigBase pattern
    └── create-specifica-feature/  # How to create a new Specifica feature

.github/
└── agents/                # VS Code custom agents
    └── spec-to-code.agent.md  # Implements code changes from spec updates

docs/
├── ai_workflow.md         # AI agent workflow documentation
└── sql_to_arc_database_views.md  # Authoritative DB view / schema contract

spec/                      # Project-level architecture & design
├── principles.md          # Project principles and foundation contract
├── configuration/         # Config loading, env overrides, secrets
└── demo-environment/      # Local demo / deployment setup

middleware/
└── sql_to_arc/            # SQL to ARC converter (Core logic)
    ├── spec/              # Component-level architecture & design
    │   ├── sql-to-arc-conversion/ # Top-level workflow feature
    │   ├── arc-building/          # ARC object construction
    │   ├── database-access/       # DB queries and row models
    │   └── api-upload/            # ARC upload to the Middleware API
    ├── src/middleware/sql_to_arc/
    │   ├── main.py        # Entry point
    │   ├── mapper.py      # Database to ARC mapping logic
    │   └── config.py      # Configuration model
    └── tests/
        ├── unit/          # Unit tests for mapper and business logic
        └── integration/   # Integration tests with database

scripts/
├── load-env.sh                    # Environment setup inside dev container (sourced from bashrc)
├── start-devcontainer-cursor.sh   # Cursor: open project via DevPod (host only)
├── setup-git-lfs.sh               # Git LFS installation
├── quality-check.sh      # Run all quality checks (ruff, mypy, pylint, bandit)
├── quality-fix.sh        # Run auto-formatters (ruff)
└── git-hooks/            # Version-controlled hooks
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

## 🔧 Important Commands

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

### Dev Container (Cursor + DevPod)

Cursor has no built-in Dev Containers. On the host, run:

```bash
./scripts/start-devcontainer-cursor.sh
```

This is the Cursor equivalent of VS Code **“Reopen in Container”**. Inside the container, `scripts/load-env.sh` runs automatically (see `postCreateCommand` in `.devcontainer/cursor/devcontainer.json`).

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

Before generating or modifying code, read the relevant spec folders.

**Project-level** (`spec/`) — cross-cutting concerns:

- **[`spec/principles.md`](spec/principles.md)** — Project principles and foundation contract (start here).
- **[`spec/configuration/`](spec/configuration/)** — Config loading, env overrides, secrets, extension rules.
- **[`spec/demo-environment/`](spec/demo-environment/)** — Local demo / deployment setup.
- **[`spec/tooling-consistency/`](spec/tooling-consistency/)** — VS Code, pre-commit, and CI must report identical results from a shared config.

**Component-level** (`middleware/sql_to_arc/spec/`) — sql_to_arc internals:

- **[`middleware/sql_to_arc/spec/sql-to-arc-conversion/`](middleware/sql_to_arc/spec/sql-to-arc-conversion/)** — Top-level workflow: workers, stats, CLI.
- **[`middleware/sql_to_arc/spec/arc-building/`](middleware/sql_to_arc/spec/arc-building/)** — ARC object construction (`mapper.py` + `builder.py`).
- **[`middleware/sql_to_arc/spec/database-access/`](middleware/sql_to_arc/spec/database-access/)** — DB access patterns, row models, SQL views.
- **[`middleware/sql_to_arc/spec/api-upload/`](middleware/sql_to_arc/spec/api-upload/)** — Upload to the Middleware API.

---

## 📝 Key Implementation Details

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

## ✨ Code Quality Standards

Agents are expected to maintain high code quality by addressing issues reported by the project's configured tools: **Ruff, Pylance, MyPy, Pylint, and Bandit**.

- **Automatic Fixes**: Actively check for and fix code smells, warnings, and notices.
- **Real Fixes vs. Suppression**: Issues must be resolved with actual code changes. Using comments to suppress warnings (e.g., `# noqa`, `# type: ignore`, `# pylint: disable`) is an **option of last resort**.
- **When to Suppress**: Only suppress if a fix is technically impossible or would result in unnecessarily complex or unreadable code.
- **Comprehensive Coverage**: Fix all reported issues, including low-severity notices and warnings, not just critical errors.

## 📚 File Modifications Pattern

When editing files:

1. **Always check current state** - Use `read_file` to see current content.
2. **Review for quality** - Check the VS Code **Problems** tab (Pylance, Mypy, Ruff run continuously in the background). Only run individual tools (`uv run ruff check .`, `uv run mypy ...`) if the Problems tab is not available. Never run `./scripts/quality-check.sh` — it is too slow.
3. **Never modify `.git/` directly** - Use scripts instead.
4. **Format and test after changes** - Run `uv run ruff format .` to auto-format, then `uv run pytest` to verify.

---

**Last Updated**: 2026-04-13
**Current Branch**: feature/workflow_fixes
**Maintainer Notes**: This repository is now decoupled from the main Middleware API. High-level architecture involves converting SQL views into ARC files.
