#!/usr/bin/env bash
# DevPod sets credsStore=devpod in ~/.docker/config.json. When the host credential
# server (localhost:12049) is not forwarded, docker pull fails even for public images.
# Drop credsStore when the helper is unreachable so DinD can pull from Docker Hub.
set -euo pipefail

config="${HOME}/.docker/config.json"

if [[ ! -f "$config" ]]; then
    exit 0
fi

if ! command -v jq &>/dev/null; then
    exit 0
fi

if ! jq -e '.credsStore == "devpod"' "$config" >/dev/null 2>&1; then
    exit 0
fi

if curl -sf --max-time 2 -o /dev/null \
    -X POST "http://127.0.0.1:12049/docker-credentials" \
    -H "Content-Type: application/json" \
    -d '{"ServerURL":"https://index.docker.io/v1/"}'; then
    exit 0
fi

echo "⚠️  DevPod Docker credential helper unavailable — removing credsStore (public pulls only)" >&2
tmp="$(mktemp)"
jq 'del(.credsStore)' "$config" > "$tmp"
mv "$tmp" "$config"
