#!/usr/bin/env bash
# One-command repro for the Sandcastle 0.14.0 local-model run.
#
# Default (Series C): use an already-running local OpenAI-compatible /v1
# endpoint. This script never starts, restarts, or removes that server
# (including any existing vLLM container).
#
#   export OPENCODE_BASE_URL=http://<LLM_HOST>:8000/v1
#   ./repro.sh
#   ./repro.sh --series c
#
# OPENCODE_BASE_URL has no default and is not baked into this kit. Replace
# <LLM_HOST> with the address where that server already listens, as reached
# from a default-bridge sandbox. OPENCODE_MODEL defaults to qwen/qwen3.8-27b-nvfp4.
#
# Series B starts a pinned llama-server (Qwen2.5-Coder-7B Q4_K_M) bound only
# to the default-bridge gateway, then runs the same task. Stop it with
# scripts/stop-llm.sh when you are done.
#
#   ./repro.sh --series b
#
# Series A is the read-only OpenCode config mount (the agent never starts):
#
#   ./repro.sh --series a
#
# Optional flags: --trials N  (default 3)
#                 --skip-setup   skip npm install, image build, git init
#                 --skip-probes
#                 --cap-drop LIST   e.g. ALL (passed to docker() capDrop)
#                 --help
#
# The script does not push anything. It does not print OPENCODE_BASE_URL
# or host addresses.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$ROOT/scripts/env.sh"

SERIES="c"
TRIALS=3
SKIP_SETUP=0
SKIP_PROBES=0
CAP_DROP_ARG=""

usage() { sed -n '2,40p' "$0" | sed 's/^# \?//'; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --series) SERIES="${2:-}"; shift 2 ;;
    --series=*) SERIES="${1#--series=}"; shift ;;
    --trials) TRIALS="${2:-}"; shift 2 ;;
    --trials=*) TRIALS="${1#--trials=}"; shift ;;
    --skip-setup) SKIP_SETUP=1; shift ;;
    --skip-probes) SKIP_PROBES=1; shift ;;
    --cap-drop) CAP_DROP_ARG="${2:-}"; shift 2 ;;
    --cap-drop=*) CAP_DROP_ARG="${1#--cap-drop=}"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $1 (try --help)" >&2; exit 2 ;;
  esac
done
SERIES="$(printf '%s' "$SERIES" | tr '[:upper:]' '[:lower:]')"
case "$SERIES" in
  a|b|c) ;;
  *) echo "unknown --series $SERIES (expected a, b, or c)" >&2; exit 2 ;;
esac
if ! [[ "$TRIALS" =~ ^[1-9][0-9]*$ ]]; then
  echo "--trials must be a positive integer" >&2
  exit 2
fi

log() { printf '%s %s\n' "$(date -Is)" "$*"; }
mkdir -p "$ROOT/logs" "$ROOT/runs"

STARTED_LLAMA=0
unset READONLY_OPENCODE_CONFIG || true

case "$SERIES" in
  c)
    if [[ -z "${OPENCODE_BASE_URL:-}" ]]; then
      cat <<'EOF' >&2
Series C (the default) uses an already-running local OpenAI-compatible /v1 endpoint.

Set OPENCODE_BASE_URL first. This kit does not bake in a host-specific value,
and this script will not start, restart, or remove that server (including any
existing vLLM container).

  export OPENCODE_BASE_URL=http://<LLM_HOST>:8000/v1
  export OPENCODE_MODEL=qwen/qwen3.8-27b-nvfp4   # optional; this is the Series C default
  ./repro.sh

Replace <LLM_HOST> with the address where that server already listens, as
reached from a default-bridge sandbox.
EOF
      exit 2
    fi
    export OPENCODE_MODEL="${OPENCODE_MODEL:-qwen/qwen3.8-27b-nvfp4}"
    log "series C: using $OPENCODE_MODEL at the already-running local /v1 endpoint (OPENCODE_BASE_URL is set; value not printed)"
    ;;
  b)
    export OPENCODE_MODEL="${OPENCODE_MODEL:-llama/qwen2.5-coder-7b-instruct}"
    if [[ -z "${OPENCODE_BASE_URL:-}" ]]; then
      gw="$(detect_bridge_gateway)"
      export OPENCODE_BASE_URL="http://${gw}:18765/v1"
    fi
    log "series B: starting pinned llama-server for $OPENCODE_MODEL on the default-bridge gateway"
    "$ROOT/scripts/start-llm.sh"
    STARTED_LLAMA=1
    ;;
  a)
    export OPENCODE_MODEL="${OPENCODE_MODEL:-llama/qwen2.5-coder-7b-instruct}"
    export READONLY_OPENCODE_CONFIG=1
    if [[ -z "${OPENCODE_BASE_URL:-}" ]]; then
      gw="$(detect_bridge_gateway)"
      export OPENCODE_BASE_URL="http://${gw}:18765/v1"
    fi
    log "series A: read-only OpenCode config mount (agent is expected to fail at startup)"
    log "series A: starting pinned llama-server on the default-bridge gateway (needed only so the provider exists)"
    "$ROOT/scripts/start-llm.sh"
    STARTED_LLAMA=1
    ;;
esac

if [[ -n "$CAP_DROP_ARG" ]]; then
  export CAP_DROP="$CAP_DROP_ARG"
  log "docker() capDrop is set (value not printed beyond the flag name ALL or the given list)"
  log "capDrop=$CAP_DROP"
fi

refuse_if_busy start
log "host mem used $(mem_pct)%"

if [[ "$SKIP_SETUP" -eq 0 ]]; then
  log "installing harness npm deps (sandcastle $SANDCASTLE_VERSION)"
  cd "$ROOT/harness"
  npm install --ignore-scripts

  log "building $SANDCASTLE_IMAGE"
  export DOCKER_BUILDKIT=1
  docker build \
    --build-arg AGENT_UID="$(id -u)" \
    --build-arg AGENT_GID="$(id -g)" \
    -t "$SANDCASTLE_IMAGE" \
    -f "$ROOT/harness/Dockerfile" \
    "$ROOT/harness"

  log "initialising task repo git"
  cd "$TASK_REPO"
  if [[ ! -d .git ]]; then
    git init
    git config user.name "sandcastle-repro"
    git config user.email "sandcastle-repro@local"
    git add package.json README.md src/slugify.js test/slugify.test.js
    git commit -m "baseline: failing slugify stub"
  fi
else
  log "skipping setup (image and task repo are assumed to already exist)"
  cd "$ROOT/harness"
fi

set +e
npm test --prefix "$TASK_REPO" > "$ROOT/logs/baseline-npm-test.txt" 2>&1
base=$?
set -e
log "baseline npm test exit $base (expected non-zero)"
if [[ $base -eq 0 ]]; then
  echo "baseline tests unexpectedly passed" >&2
  exit 1
fi

if [[ "$SKIP_PROBES" -eq 0 ]]; then
  log "running enforcement probes"
  cd "$ROOT/harness"
  if gw="$(detect_bridge_gateway 2>/dev/null)"; then
    export LLM_GATEWAY="$gw"
  fi
  PROBE_OUT="$ROOT/runs/probes" TASK_REPO="$TASK_REPO" SANDCASTLE_IMAGE="$SANDCASTLE_IMAGE" \
    npx tsx run-probes.ts | tee "$ROOT/logs/probes-summary.json"
else
  log "skipping enforcement probes"
fi

# Visible trial: tail the agent log with a relative path so a live tty capture
# shows the run end to end (start to commit or to the known failure).
run_visible_trial() {
  local i="$1"
  local prefix="$2"
  local ts run_id log rc tail_pid
  ts="$(date +%Y%m%dT%H%M%S)"
  run_id="${prefix}-${i}-${ts}"
  log="$ROOT/runs/${run_id}/sandcastle-logs/agent.log"
  mkdir -p "$(dirname "$log")"
  : > "$log"
  refuse_if_busy "trial $run_id"
  log "before $run_id host mem used $(mem_pct)%"
  echo "===== START $run_id ====="
  echo "tailing runs/${run_id}/sandcastle-logs/agent.log"
  tail -n +1 -F "$log" &
  tail_pid=$!
  set +e
  RUN_INDEX="$i" RUN_ID="$run_id" TASK_REPO="$TASK_REPO" SANDCASTLE_IMAGE="$SANDCASTLE_IMAGE" \
    npx tsx run-trial.ts
  rc=$?
  set -e
  sleep 0.3
  kill "$tail_pid" 2>/dev/null || true
  wait "$tail_pid" 2>/dev/null || true
  echo "===== END $run_id exit=$rc ====="
  return "$rc"
}

cd "$ROOT/harness"
prefix="trial"
case "$SERIES" in
  a) prefix="trial-a" ;;
  b) prefix="trial-b" ;;
  c) prefix="trial-c" ;;
esac

overall=0
for i in $(seq 1 "$TRIALS"); do
  if ! run_visible_trial "$i" "$prefix"; then
    overall=1
  fi
done

log "writing this invocation's summary to logs/last-run-table.md (does not overwrite logs/results-table.md)"
python3 "$ROOT/scripts/summarize.py" "$ROOT/runs" | tee "$ROOT/logs/last-run-table.md"

if [[ "$STARTED_LLAMA" -eq 1 ]]; then
  log "done. See logs/ and runs/. The Series B llama-server is still up; stop with scripts/stop-llm.sh"
  log "This script does not stop or restart any other model server."
else
  log "done. See logs/ and runs/. No model server was started or stopped."
fi
exit "$overall"
