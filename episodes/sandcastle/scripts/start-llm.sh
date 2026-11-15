#!/usr/bin/env bash
# Start the pinned local llama-server for Series B only.
# Binds only to the default-bridge gateway (detected at runtime), not to LAN or other host addresses.
# Never starts, restarts, or removes any other model server container.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/scripts/env.sh"

if docker ps --format '{{.Names}}' | grep -qx sandcastle-local-llm; then
  echo "sandcastle-local-llm already running"
  exit 0
fi
docker rm -f sandcastle-local-llm >/dev/null 2>&1 || true

if [[ ! -f "$GGUF" ]]; then
  echo "missing GGUF (set GGUF to the pinned Qwen2.5-Coder-7B Q4_K_M file; see versions.txt)" >&2
  exit 1
fi
echo "$GGUF_SHA256  $GGUF" | sha256sum -c -

gw="$(detect_bridge_gateway)"
export BRIDGE_GATEWAY="$gw"

docker run -d --name sandcastle-local-llm \
  --cgroup-parent bench.slice \
  --gpus all \
  --cpus 8 \
  --memory 32g \
  --memory-swap 32g \
  --restart=no \
  -v "$GGUF:/models/model.gguf:ro" \
  -p "${gw}:18765:18765" \
  --entrypoint /usr/local/bin/llama-server \
  "$LLM_IMAGE" \
  -m /models/model.gguf \
  --host 0.0.0.0 \
  --port 18765 \
  -c 16384 \
  -ngl 99 \
  --alias qwen2.5-coder-7b-instruct \
  --jinja >/dev/null

echo "waiting for llama-server on the default-bridge gateway"
for i in $(seq 1 60); do
  if curl -fsS --max-time 2 "http://${gw}:18765/v1/models" >/dev/null 2>&1; then
    echo "llama-server is ready"
    exit 0
  fi
  sleep 2
done
echo "llama-server did not become ready" >&2
docker logs sandcastle-local-llm >&2 || true
exit 1
