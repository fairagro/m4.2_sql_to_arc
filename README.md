# FAIRagro SQL-to-ARC Middleware

This repository contains the **SQL-to-ARC Converter**, a core component of the FAIRagro advanced middleware architecture. It enables Research Data Infrastructure (RDI) providers to transform their relational metadata into standardized Annotated Research Context (ARC) objects and transmit them to the central FAIRagro Middleware API.

## 📁 Repository Structure

| Folder | Description |
| :--- | :--- |
| [middleware/](middleware/) | Source code of the converter component. |
| [docs/](docs/) | Architectural design, database view specifications, and API documentation. |
| [dev_environment/](dev_environment/) | Docker-based local development setup (Postgres, Mock API). |
| [scripts/](scripts/) | Tooling for quality checks, environment setup, and Git LFS. |
| [docker/](docker/) | Dockerfiles and container structure tests. |

## 🌟 Quick Start (Full Local Demo)

For the best **out-of-the-box experience**, you can run a complete local demonstration. This setup starts a PostgreSQL database with demo data, a local Mock Middleware API, and the SQL-to-ARC converter to process and save results locally:

```bash
# Start the full demo stack (requires Docker)
./dev_environment/start-demo.sh --build
```

> **Note:** This demo does not require any secrets or mTLS keys. Generated ARCs will be saved to `dev_environment/demo_output/`.

## 🚀 Getting Started (Development)

The preferred method for working with this repository is using the **Dev Container** (VS Code).

While it is possible to develop without the Dev Container (see next steps below), this approach is not tested and is therefore neither documented nor officially supported.

### 1. Prerequisites (for manual setups only)

- **Python 3.12+**
- **[uv](https://github.com/astral-sh/uv)** (Dependency Management & Workspace Orchestration)
- **Docker & Docker Compose**
- **Git LFS** (installed via `./scripts/setup-git-lfs.sh`)

### 2. Environment Setup

Clone the repository and install all workspace dependencies:

```bash
uv sync --all-packages
```

### 3. Start Local Development Environment

The `dev_environment` folder provides a full stack including a PostgreSQL database pre-filled with edaphobase data.

Please refer to the **[Development Environment README](dev_environment/README.md)** for detailed instructions on prerequisites (like secret management and mTLS keys), setup, and usage.

## 🔧 Component Documentation

Detailed information on how to use, configure, and deploy the specific components can be found in their respective subdirectories:

- **[SQL-to-ARC Converter README](middleware/sql_to_arc/README.md)**: Configuration (YAML/Env), CLI options, and production deployment.
- **[Architectural Design](docs/ARCHITECTURAL_DESIGN.md)**: Deep dive into the concurrency model, memory management, and data flow.
- **[Database View Spec](docs/sql_to_arc_database_views.md)**: The SQL views required for the RDI provider database.

## 🧪 Quality Standards

We maintain high code quality through automated checks:

```bash
# Run all quality checks (Ruff, Mypy, Pylint, Bandit)
./scripts/quality-check.sh

# Run unit and integration tests
uv run pytest middleware/sql_to_arc/tests/
```

---
**Maintained by:** FAIRagro Middleware Team
**License:** [LICENSE](LICENSE)
