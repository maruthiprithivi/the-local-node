#!/usr/bin/env bash
# Lesson 10 · step 4 — the delta: base vs fine-tune, same harness as lesson 09.
# The deployed model is addressed as <model>#<deployment>. If your console shows a
# different model string on the deployment's API tab, use that instead.
set -euo pipefail
cd "$(dirname "$0")"; source _state.sh
TUNED="accounts/$ACCOUNT/models/$OUT_MODEL#accounts/$ACCOUNT/deployments/$DEPLOYMENT_ID"

python ../09-eval-harness/evaluate.py \
  "fireworks:$BASE_MODEL" \
  "fireworks:$TUNED" --n 60

mins=$(( ( $(date +%s) - DEPLOY_STARTED ) / 60 ))
echo "▸ deployment has been up ${mins} min ≈ \$$(python -c "print(round($mins/60*$DEPLOY_RATE,2))") → bash 5_teardown.sh NOW"
