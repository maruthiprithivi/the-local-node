#!/usr/bin/env bash
# Stops only the Series B container started by scripts/start-llm.sh.
# Never restarts or removes any already-running third-party model server.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/scripts/env.sh"
docker rm -f sandcastle-local-llm >/dev/null 2>&1 || true
echo "sandcastle-local-llm removed (if it was present)"
