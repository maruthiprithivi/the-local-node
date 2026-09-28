#!/usr/bin/env bash
# Lesson 10 · step 5 — stop the clock. Then PROVE it stopped.
set -euo pipefail
cd "$(dirname "$0")"; source _state.sh
firectl deployment delete "$DEPLOYMENT_ID"
mins=$(( ( $(date +%s) - DEPLOY_STARTED ) / 60 ))
echo "▸ deleted after ${mins} min (≈ \$$(python -c "print(round($mins/60*$DEPLOY_RATE,2))") serving + a few cents of training)"
echo "▸ remaining deployments (should be empty):"
firectl deployment list
# The trained model and dataset stay in your account (cheap storage) so you can redeploy later.
rm -f .state
