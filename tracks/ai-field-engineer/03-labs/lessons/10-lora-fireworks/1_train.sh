#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Lesson 10 · step 1 — upload the dataset and start a LoRA SFT job.
#
# Cost: training is billed per training token. 800 short examples × 2 epochs is
# ~0.3M tokens → cents. Training is NOT the expensive part of this lesson (step 3 is).
#
#   --lora-rank 8      adapter size. Small task, small rank. (16–32 for harder tasks)
#   --epochs 2         passes over the data. More = memorise; watch eval, not loss
#   --learning-rate    leave default unless loss misbehaves
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
cd "$(dirname "$0")"; source _state.sh
STAMP=$(date +%m%d%H%M)
[[ -f ../../data/tickets/train.jsonl ]] || python ../../data/make_tickets.py

save DATASET "triage-train-$STAMP"
save JOB_ID  "triage-sft-$STAMP"
save OUT_MODEL "triage-lora-$STAMP"

firectl dataset create "$DATASET" ../../data/tickets/train.jsonl
firectl sftj create --job-id "$JOB_ID" --base-model "$BASE_MODEL" \
  --dataset "$DATASET" --output-model "$OUT_MODEL" --epochs 2 --lora-rank 8

echo "▸ started $JOB_ID → next: bash 2_wait.sh"
