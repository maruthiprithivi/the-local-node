#!/usr/bin/env bash
# Lesson 10 · step 2 — wait for training. Typically 10–30 min for this size.
set -euo pipefail
cd "$(dirname "$0")"; source _state.sh
while true; do
  state=$(firectl sftj get "$JOB_ID" | grep -iE "^\s*state" | head -1 || true)
  echo "  $(date +%H:%M:%S) $state"
  [[ "$state" =~ COMPLETED ]] && { echo "▸ trained: accounts/$ACCOUNT/models/$OUT_MODEL → bash 3_deploy.sh"; exit 0; }
  [[ "$state" =~ FAILED|CANCELLED ]] && { firectl sftj get "$JOB_ID"; exit 1; }
  sleep 60
done
