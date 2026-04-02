#!/usr/bin/env bash
#
# Start sql_to_arc locally with a local DB, but connecting to an EXTERNAL Middleware API.
#
# Usage:
#   ./start-external.sh              # Start services
#   ./start-external.sh --build      # Build images and start
#

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$script_dir"

# Parse arguments
BUILD_FLAG=""
if [[ "${1:-}" == "--build" ]]; then
  BUILD_FLAG="--build"
fi

echo "==> Starting SQL-to-ARC with EXTERNAL API..."
echo "    - Local PostgreSQL will be started"
echo "    - Database will be initialized with Edaphobase dump"
echo "    - SQL-to-ARC will connect to the API configured in config.dev.yaml"
echo "    - Using client certificates: client.crt, secrets.enc.yaml"
echo ""

if [[ ! -f "secrets.enc.yaml" ]]; then
  echo "ERROR: secrets.enc.yaml not found. Please provide your secrets file."
  exit 1
fi

# Use sops exec-env to pass the decrypted secrets as environment variables
# without writing them to physical disk files.
sops exec-env "${script_dir}/secrets.enc.yaml" \
  "docker compose -f compose.dev.yaml up $BUILD_FLAG"

echo ""
echo "==> Services finished!"
echo "    - View logs: docker compose -f compose.dev.yaml logs"
echo "    - Clean up: docker compose -f compose.dev.yaml down"
