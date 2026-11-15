#!/usr/bin/env bash
set -euo pipefail
export EPISODE_ROOT="${EPISODE_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
# shellcheck disable=SC1091
source "$EPISODE_ROOT/scripts/env.sh"
cd "$EPISODE_ROOT/harness"
mem_pct() { awk '/MemAvailable/{a=$2} /MemTotal/{t=$2} END{printf "%.1f", (t-a)*100/t}' /proc/meminfo; }

run_one() {
  local i="$1"
  local ts run_id rc
  ts=$(date +%Y%m%dT%H%M%S)
  run_id="trial-${i}-${ts}"
  echo "===== START $run_id mem=$(mem_pct)% ====="
  set +e
  RUN_INDEX="$i" RUN_ID="$run_id" TASK_REPO="$TASK_REPO" SANDCASTLE_IMAGE="$SANDCASTLE_IMAGE" \
    npx tsx run-trial.ts | tee "$EPISODE_ROOT/logs/${run_id}-summary.json"
  rc=${PIPESTATUS[0]}
  set -e
  echo "===== END $run_id exit=$rc ====="
}

run_one 1
run_one 2
run_one 3
python3 "$EPISODE_ROOT/scripts/summarize.py" "$EPISODE_ROOT/runs"
echo "mem=$(mem_pct)%"
