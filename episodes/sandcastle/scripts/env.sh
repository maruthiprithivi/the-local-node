#!/usr/bin/env bash
# Shared paths and pins. Source from other scripts.
# Do not print secrets. There are no real API keys in this run.
# Do not print host addresses or OPENCODE_BASE_URL.

# Optional Docker API proxy so containers land in bench.slice.
# Set DOCKER_HOST, or BENCH_DOCKER_SOCK to the proxy socket path. Nothing is baked in.
if [[ -z "${DOCKER_HOST:-}" && -n "${BENCH_DOCKER_SOCK:-}" && -S "${BENCH_DOCKER_SOCK}" ]]; then
  export DOCKER_HOST="unix://${BENCH_DOCKER_SOCK}"
fi

export EPISODE_ROOT="${EPISODE_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
# WORK_ROOT / NODE_HOME / GGUF are optional and must be set by the environment when needed.
# This kit does not bake in a host work directory.
if [[ -n "${NODE_HOME:-}" && -d "$NODE_HOME/bin" ]]; then
  export PATH="$NODE_HOME/bin:$PATH"
fi

export GGUF_SHA256="${GGUF_SHA256:-509287f78cb4d4cf6b3843734733b914b2c158e43e22a7f4bf5e963800894d3c}"
export LLM_IMAGE="${LLM_IMAGE:-thinklite-llamacpp:8642541}"
export LLM_IMAGE_ID="${LLM_IMAGE_ID:-sha256:404144a0af3a85522483bca4d397610666773a0d8e4acd9cb81d65f629bdadba}"
export NODE_IMAGE="${NODE_IMAGE:-node:22-bookworm@sha256:e13726ca604184d7a91fcacab1fc09eefd642dc28e79ac34e85540dd93b78cfb}"
export SANDCASTLE_IMAGE="${SANDCASTLE_IMAGE:-sandcastle-opencode:0.14.0-local}"
export SANDCASTLE_VERSION="${SANDCASTLE_VERSION:-0.14.0}"
export OPENCODE_VERSION="${OPENCODE_VERSION:-1.19.5}"
export NODE_VERSION="${NODE_VERSION:-v22.23.5}"
export TASK_REPO="${TASK_REPO:-$EPISODE_ROOT/task-repo}"
if [[ -z "${GGUF:-}" && -n "${WORK_ROOT:-}" ]]; then
  export GGUF="$WORK_ROOT/models/qwen2.5-coder-7b-instruct-q4_k_m.gguf"
fi

# Address of the default-bridge gateway on this machine (detected at runtime, never printed).
# Used only so Series B llama-server can bind where a default-bridge sandbox can reach it.
detect_bridge_gateway() {
  if [[ -n "${BRIDGE_GATEWAY:-}" ]]; then
    printf '%s\n' "$BRIDGE_GATEWAY"
    return 0
  fi
  local addr=""
  if command -v docker >/dev/null 2>&1; then
    addr="$(docker network inspect bridge --format '{{range .IPAM.Config}}{{.Gateway}}{{end}}' 2>/dev/null || true)"
  fi
  if [[ -z "$addr" ]]; then
    echo "could not detect the default-bridge gateway. Set BRIDGE_GATEWAY and retry." >&2
    return 1
  fi
  printf '%s\n' "$addr"
}

mem_pct() { awk '/MemAvailable/{a=$2} /MemTotal/{t=$2} END{printf "%.1f", (t-a)*100/t}' /proc/meminfo; }
refuse_if_busy() {
  python3 "$EPISODE_ROOT/scripts/refuse-if-busy.py" "${1:-start}"
}
