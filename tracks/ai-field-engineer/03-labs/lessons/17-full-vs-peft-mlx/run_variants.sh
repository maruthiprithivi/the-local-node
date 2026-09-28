#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Lesson 17 · step 2 — the same model, same data, three ways (videos 14, 15, 16).
#
#   full   every weight trains                       lr 1e-5 (full FT needs a smaller step)
#   lora   frozen base + low-rank B·A in every layer  lr 1e-4
#   dora   LoRA on direction + a magnitude vector     lr 1e-4
#
# Model: Qwen2.5-0.5B-Instruct in bf16. Small enough that FULL fine-tuning fits on a
# 16 GB Mac (≈0.5B × 16 bytes ≈ 8 GB + activations). QLoRA needs a quantized base; for
# full fine-tuning the base must NOT be quantized, so we use bf16 for all three.
#
#   --mask-prompt       loss on the assistant answer only (video 15)
#   --num-layers -1     all layers, so the three runs are comparable
#   --grad-checkpoint   recompute activations: less memory, a bit slower (video 14)
#
# ~5–15 min per variant on M-series. Logs → logs/<variant>.log, weights → adapters/<variant>/
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
cd "$(dirname "$0")"
MODEL=${MODEL:-mlx-community/Qwen2.5-0.5B-Instruct-bf16}
ITERS=${ITERS:-300}
VARIANTS=(${VARIANTS:-full lora dora})
DATA=../../data/tickets
mkdir -p logs adapters

python sft_data_check.py || { echo "fix the data first"; exit 1; }

for v in "${VARIANTS[@]}"; do
  lr=1e-4; [[ $v == full ]] && lr=1e-5
  echo "▸ $v  (lr $lr, $ITERS iters)"
  start=$SECONDS
  mlx_lm.lora --model "$MODEL" --train --data "$DATA" \
    --fine-tune-type "$v" --num-layers -1 --mask-prompt --grad-checkpoint \
    --batch-size 4 --iters "$ITERS" --learning-rate "$lr" \
    --steps-per-report 20 --steps-per-eval 100 \
    --adapter-path "adapters/$v" 2>&1 | tee "logs/$v.log"
  echo "wall_seconds $(( SECONDS - start ))" >> "logs/$v.log"
done
echo "▸ next: python compare_variants.py"
