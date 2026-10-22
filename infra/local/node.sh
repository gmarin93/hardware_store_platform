#!/bin/sh
# Run npm/npx with the pinned Node LTS image instead of the host Node.
# The host Node (v20) is end-of-life and below the vitest minimum; see ADR 0002.
# Usage: infra/local/node.sh npm ci
#        infra/local/node.sh npm run web:lint
set -eu

NODE_IMAGE="node:24.22.1-alpine3.24@sha256:06d7adf3e0ef61a13f1d28682726366f97a15aa1888c934d3ecec86c33918b53"
ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"

if [ "$#" -eq 0 ]; then
  echo "usage: $0 <command> [args...]" >&2
  exit 64
fi

TTY_FLAG=""
if [ -t 0 ] && [ -t 1 ]; then
  TTY_FLAG="-it"
fi

# shellcheck disable=SC2086
exec docker run --rm $TTY_FLAG \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e npm_config_cache=/tmp/.npm \
  -e npm_config_update_notifier=false \
  -e npm_config_fund=false \
  -e npm_config_audit=false \
  -e NEXT_TELEMETRY_DISABLED=1 \
  -e CI="${CI:-}" \
  -v "$ROOT_DIR":/workspace \
  -w /workspace \
  "$NODE_IMAGE" "$@"
