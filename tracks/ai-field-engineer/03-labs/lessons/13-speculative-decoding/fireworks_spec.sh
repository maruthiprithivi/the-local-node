#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Lesson 13 · step 4 — speculation on a Fireworks dedicated deployment.  ⏱ PAID
#
# Deploy → measure → DELETE, in one script, with a trap so Ctrl-C still deletes.
# Budget: ~30–45 min of one deployment. Most supported models already ship a
# default drafter; here we set one explicitly so you can see the knobs:
#   --draft-model        a small model with the same tokenizer
#   --draft-token-count  k (start at 4, per the docs)
#   (alternative: --ngram-speculation-length=3 — no draft model; reuses n-grams from the prompt)
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
cd "$(dirname "$0")"
TARGET_MODEL=${TARGET_MODEL:-accounts/fireworks/models/llama-v3p1-8b-instruct}
DRAFT_MODEL=${DRAFT_MODEL:-accounts/fireworks/models/llama-v3p2-1b-instruct}

out=$(firectl deployment create "$TARGET_MODEL" --deployment-shape default \
        --draft-model="$DRAFT_MODEL" --draft-token-count=4)
echo "$out"
DEP=$(echo "$out" | grep -oE 'deployments/[A-Za-z0-9-]+' | head -1 | cut -d/ -f2)
ACCOUNT=$(echo "$out" | grep -oE 'accounts/[a-z0-9-]+/deployments' | head -1 | cut -d/ -f2)
trap 'echo "▸ deleting $DEP"; firectl deployment delete "$DEP"; firectl deployment list' EXIT
echo "▸ $DEP created $(date +%H:%M) — ⏱ clock running"

until firectl deployment get "$DEP" | grep -qiE "state.*READY"; do sleep 20; echo -n "."; done; echo " ready"

python spec_bench.py --target fireworks --model "$TARGET_MODEL#accounts/$ACCOUNT/deployments/$DEP" --label fw-spec
# the trap deletes the deployment on exit
