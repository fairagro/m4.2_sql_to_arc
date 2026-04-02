# SQL-to-ARC Middleware Converter

The **SQL-to-ARC Converter** is a high-performance middleware component designed to bridge research data infrastructures (RDIs) and the FAIRagro metadata ecosystem.

## Overview

SQL-to-ARC runs locally at the RDI provider's infrastructure. It connects to the provider's SQL database, extracts metadata from a [pre-defined set of database views](docs/sql_to_arc_database_views.md), and transforms this data into **Annotated Research Context (ARC)** objects using the [ARCtrl Library](https://github.com/nfdi4plants/ARCtrl).

Once an ARC is constructed and validated, the tool uses the [middleware api_client library](https://github.com/fairagro/m4.2_advanced_middleware_api/tree/main/middleware/api_client) to transmit the resulting RO-Crate JSON-LD payloads to the [FAIRagro Middleware API](https://github.com/fairagro/m4.2_advanced_middleware_api).

### Key Features

- **High Throughput:** Parallel processing using a CPU-bound process pool for ARC generation.
- **Memory Efficient:** Streaming database access via server-side cursors and batching.
- **Robust:** Pre-flight schema validation and comprehensive OpenTelemetry tracing.
- **Configurable:** Fully customizable via YAML, Environment Variables, or Docker Secrets.

---

## Configuration

The tool is configured using a YAML file, which can be overridden by Environment Variables.

### YAML Configuration (`config.yaml`)

Example configuration file:

```yaml
connection_string: "postgresql+psycopg://user:password@localhost:5432/edaphobase"
rdi: "edaphobase"
rdi_url: "https://portal.edaphobase.org"
max_concurrent_arc_builds: 4
db_batch_size: 50

api_client:
  api_url: "https://middleware.fairagro.net/api/v1"
  client_cert_path: "/run/secrets/client.crt"
  client_key_path: "/run/secrets/client.key"
  verify_ssl: true
```

| Field | Type | Description | Default |
| :--- | :--- | :--- | :--- |
| `connection_string` | `string` | Database URI (e.g., `postgresql+psycopg://user:pass@host:5432/db`). | **Required** |
| `rdi` | `string` | Unique identifier for your RDI (e.g., `edaphobase`). | **Required** |
| `rdi_url` | `string` | Public URL of your RDI (used for provenance metadata). | **Required** |
| `api_client` | `object` | Configuration for the Middleware API connection (see below). | **Required** |
| `log_level` | `string` | Console logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`). | `INFO` |
| `otel` | `object` | OpenTelemetry configuration (see below). | `defaults` |
| `max_concurrent_arc_builds` | `int` | Number of parallel worker processes in the CPU pool. | `5` |
| `max_concurrent_tasks` | `int` | Max concurrent IO+CPU tasks. | `4 * builds` |
| `db_batch_size` | `int` | Investigations to fetch per DB chunk. | `100` |
| `max_studies` | `int` | Max studies per investigation (safety limit). | `5000` |
| `max_assays` | `int` | Max assays per investigation (safety limit). | `10000` |
| `arc_generation_timeout_minutes` | `int` | Timeout for a single ARC generation process. | `30` |
| `debug_limit` | `int` | (Optional) Limit processing to the first N investigations. | `None` |

#### `api_client` Configuration

The official **[FAIRagro Middleware API](https://middleware.fairagro.net/docs#/)** requires **mTLS (Mutual TLS)** for authentication. This means you must provide both a client certificate and a private key.

To obtain a valid client certificate for your RDI, please contact the FAIRagro middleware team at:
`carsten (dot) scharfenberg (at) zalf (dot) de`

| Field | Type | Description | Default |
| :--- | :--- | :--- | :--- |
| `api_url` | `string` | URL of the Middleware API. | **Required** |
| `client_cert_path` | `string` | Path to the client certificate (PEM). | `None` |
| `client_key_path` | `string` | Path to the client private key (PEM). | `None` |
| `ca_cert_path` | `string` | Path to a custom CA certificate for server verification. | `None` |
| `timeout` | `float` | Request timeout in seconds. | `30.0` |
| `verify_ssl` | `bool` | Whether to verify the API's SSL certificate. | `true` |
| `follow_redirects` | `bool` | Whether to follow HTTP redirects. | `true` |
| `max_concurrency` | `int` | Max concurrent HTTP requests. | `10` |
| `max_retries` | `int` | Max retries for transient HTTP errors. | `3` |
| `retry_backoff_factor` | `float` | Backoff factor for retries. | `2.0` |

#### `otel` Configuration

OpenTelemetry settings for distributed tracing and logging.

| Field | Type | Description | Default |
| :--- | :--- | :--- | :--- |
| `endpoint` | `string` | OTel collector endpoint (e.g., `http://localhost:4318`). | `None` |
| `log_console_spans` | `bool` | Whether to print OTel spans to the console. | `false` |
| `log_level` | `string` | Logging level for OTLP log export. | `INFO` |

### Environment Variables

All configuration fields can be set via environment variables using the prefix **`SQL_TO_ARC_`**.

- **Examples:**
  - `SQL_TO_ARC_CONNECTION_STRING="postgresql://..."`
  - `SQL_TO_ARC_RDI="my-rdi"`
  - `SQL_TO_ARC_DEBUG_LIMIT=10`

### Secrets Handling

In containerized environments, sensitive values like the `connection_string` or `client_key` can be provided via **Docker Secrets**. The tool looks for files in `/run/secrets/` with names matching the lowercase environment variable (e.g., `/run/secrets/sql_to_arc_connection_string`).

---

## Usage

The following examples assume you are in the root of the repository.

### 1. From Source (Development)

Requires [uv](https://github.com/astral-sh/uv) installed.

```bash
# Install dependencies for all workspace members
uv sync --all-packages

# Run the converter using the example config directly
uv run python -m middleware.sql_to_arc.main -c middleware/sql_to_arc/config.example.yaml
```

### 2. Local Docker Image

Build the image from the repository root:

```bash
# Build the converter image
docker build -f docker/Dockerfile.sql_to_arc -t sql-to-arc:local .

# Run using the example config via a volume mount
docker run --rm \
  --env-file .env \
  -v $(pwd)/middleware/sql_to_arc/config.example.yaml:/etc/sql_to_arc/config.yaml:ro \
  sql-to-arc:local
```

### 3. Official Docker Image

Pull the latest official image from Docker Hub (once available):

```bash
docker run --rm \
  --env-file .env \
  -v $(pwd)/middleware/sql_to_arc/config.example.yaml:/etc/sql_to_arc/config.yaml:ro \
  zalf/fairagro-advanced-middleware-sql_to_arc/sql-to-arc:latest
```

---

## CLI Options

| Option | Description |
| :--- | :--- |
| `-c`, `--config` | Path to the YAML configuration file (Default: `config.yaml`). |
| `-v`, `--version` | Show the version and exit. |
| `-h`, `--help` | Show help and exit. |

---

## Documentation Links

- [Architectural Design](docs/ARCHITECTURAL_DESIGN.md)
- [Database View Specification](docs/sql_to_arc_database_views.md)
- [ARCtrl Documentation](https://nfdi4plants.org/ARCtrl/)
- [Middleware API Client](https://github.com/fairagro/m4.2_advanced_middleware_api/tree/main/middleware/api_client)
