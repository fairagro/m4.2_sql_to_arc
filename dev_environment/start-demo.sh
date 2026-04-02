#!/usr/bin/env bash
#
# Start a full local demo environment (SQL DB + Converter + Mock API)
# This setup DOES NOT require mTLS or secret decryption.
#
# Usage:
#   ./start-demo.sh              # Start services
#   ./start-demo.sh --build      # Build images and start
#

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$script_dir"

# Parse arguments
BUILD_FLAG=""
if [[ "${1:-}" == "--build" ]]; then
  BUILD_FLAG="--build"
fi

echo "==> Starting FULL LOCAL DEMO..."
echo "    - PostgreSQL will be started"
echo "    - Database will be initialized with LOCAL demo.sql (10 records)"
echo "    - Local Middleware API Mock will be started (no mTLS required)"
echo "    - SQL-to-ARC will connect to local mock"
echo "    - ARCs will be deserialized and saved as ISA folders"
echo ""

# Export environment variables for compose.dev.yaml (usually from secrets, but hardcoded here for demo)
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=postgres
export CONNECTION_STRING="postgresql+psycopg://postgres:postgres@postgres:5432/rdi"
export CLIENT_KEY="not-needed-for-demo"
export LOCAL_UID="$(id -u)"
export LOCAL_GID="$(id -g)"

# Ensure output directory exists for the volume mount
mkdir -p "${script_dir}/demo_output"

# Start services using the base compose file + the demo override
# This now overrides the db-init service to use demo.sql without downloads
docker compose -f compose.dev.yaml -f compose.demo.yaml up $BUILD_FLAG

echo ""
echo "==> Demo finished! You can find the generated ARCs in: dev_environment/demo_output/"
echo "    (Wait a moment for files to appear if they are being processed...)"
echo "    - View logs: docker compose -f compose.dev.yaml -f compose.demo.yaml logs"
echo "    - Clean up: docker compose -f compose.dev.yaml -f compose.demo.yaml down -v"
