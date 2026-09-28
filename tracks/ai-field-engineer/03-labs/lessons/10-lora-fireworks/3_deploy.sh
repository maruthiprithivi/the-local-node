#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Lesson 10 · step 3 — serve the LoRA.  ⚠ THE BILLING CLOCK STARTS HERE ⚠
#
# A fine-tuned LoRA is served on a DEDICATED deployment (GPU-hours), not per token.
# That is the real cost of a fine-tune and the conversation to have with a customer:
# one deployment can host MANY LoRAs (multi-LoRA), which is how that cost is shared.
#
# Budget for this step: ~1 hour × $DEPLOY_RATE. Run 4_eval.sh then 5_teardown.sh promptly.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
cd "$(dirname "$0")"; source _state.sh
MODEL="accounts/$ACCOUNT/models/$OUT_MODEL"

out=$(firectl deployment create "$MODEL" --deployment-shape default)
echo "$out"
save DEPLOYMENT_ID "$(echo "$out" | grep -oE 'deployments/[A-Za-z0-9-]+' | head -1 | cut -d/ -f2)"
save DEPLOY_STARTED "$(date +%s)"
echo "▸ deployment $DEPLOYMENT_ID created at $(date +%H:%M) — clock running at ~\$$DEPLOY_RATE/h"

echo "▸ waiting for READY"
until firectl deployment get "$DEPLOYMENT_ID" | grep -qiE "state.*READY"; do sleep 20; echo -n "."; done
echo " ready → bash 4_eval.sh"
