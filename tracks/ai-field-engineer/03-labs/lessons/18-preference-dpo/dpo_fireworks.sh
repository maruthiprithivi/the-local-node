#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Lesson 18 · step 3 — the same DPO job on Fireworks.  ⏱ PAID (training + a deployment)
#
#   firectl dpo-job create --loss-method DPO   (or ORPO with --orpo-lambda; see video 18)
#
# The base model must be one the Fireworks model library marks as DPO-enabled. Override
# with BASE_MODEL=… Training is billed per token (cents for 800 short pairs). Evaluating
# needs a dedicated deployment (⏱ per hour), which a trap deletes on exit, even on Ctrl-C.
# Flags follow the Fireworks docs at time of writing; `firectl dpo-job create --help` wins.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
cd "$(dirname "$0")"
BASE_MODEL=${BASE_MODEL:-accounts/fireworks/models/qwen2p5-7b-instruct}
ACCOUNT=${FIREWORKS_ACCOUNT_ID:-$(firectl whoami 2>/dev/null | grep -oE 'accounts/[a-z0-9-]+' | head -1 | cut -d/ -f2)}
STAMP=$(date +%m%d%H%M)
DATASET="triage-dpo-$STAMP"; OUT="triage-dpo-$STAMP"

[[ -f data/fireworks/train.jsonl ]] || python make_pairs.py
firectl dataset create "$DATASET" data/fireworks/train.jsonl
out=$(firectl dpo-job create --loss-method DPO --base-model "$BASE_MODEL" \
        --dataset "accounts/$ACCOUNT/datasets/$DATASET" --output-model "$OUT")
echo "$out"
JOB=$(echo "$out" | grep -oE 'dpoJobs/[A-Za-z0-9-]+' | head -1 | cut -d/ -f2)
echo "▸ job $JOB — polling every 60 s (Ctrl-C is safe; the job keeps running)"
until firectl dpo-job get "$JOB" | grep -qE "COMPLETED"; do
  firectl dpo-job get "$JOB" | grep -qE "FAILED|CANCELLED" && { firectl dpo-job get "$JOB"; exit 1; }
  sleep 60; echo -n "."
done
echo " trained: accounts/$ACCOUNT/models/$OUT"

read -r -p "Deploy for evaluation now? This starts per-hour billing. [y/N] " yn
[[ "$yn" =~ ^[Yy]$ ]] || { echo "Skipped. Deploy later with lesson 10's 3_deploy.sh pattern."; exit 0; }
dep=$(firectl deployment create "accounts/$ACCOUNT/models/$OUT" --deployment-shape default)
DEP=$(echo "$dep" | grep -oE 'deployments/[A-Za-z0-9-]+' | head -1 | cut -d/ -f2)
trap 'echo "▸ deleting $DEP"; firectl deployment delete "$DEP"; firectl deployment list' EXIT
until firectl deployment get "$DEP" | grep -qiE "state.*READY"; do sleep 20; echo -n "."; done; echo " ready"
python pref_eval.py --target fireworks --model "$BASE_MODEL" --label fw-base
python pref_eval.py --target fireworks --model "accounts/$ACCOUNT/models/$OUT#accounts/$ACCOUNT/deployments/$DEP" --label fw-dpo
