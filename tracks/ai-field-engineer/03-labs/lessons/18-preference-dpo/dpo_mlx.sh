#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Lesson 18 · step 2 — DPO on your Mac with mlx-lm-lora (video 18).
#
# Rule from the video: SFT first, then DPO. If lesson 17's LoRA adapter exists we fuse it
# into an SFT model and run DPO on top of that; otherwise we start from the instruct model.
# The same model is used as the frozen REFERENCE, which is what β measures distance from.
#
#   --train-mode dpo              the DPO loss (also: orpo, cpo, grpo, ppo … see --help)
#   --beta 0.1                    the leash (video 18: start around 0.1)
#   --dpo-cpo-loss-type sigmoid   the original DPO loss: −log σ(β · margin)
#   --reference-model-path        the frozen copy the policy is compared against
#
# Flags follow the mlx-lm-lora README at time of writing; `mlx_lm_lora.train --help` wins.
# ~10–20 min on M-series for 0.5B. Two models in memory (policy + reference).
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
cd "$(dirname "$0")"
BASE=${MODEL:-mlx-community/Qwen2.5-0.5B-Instruct-bf16}
L17=../17-full-vs-peft-mlx/adapters/lora

python -c "import mlx_lm_lora" 2>/dev/null || pip install -U mlx-lm-lora
[[ -f data/mlx/train.jsonl ]] || python make_pairs.py

if [[ -d "$L17" && ! -d sft_model ]]; then
  echo "▸ fusing lesson 17's LoRA into an SFT model (SFT first, then DPO)"
  mlx_lm.fuse --model "$BASE" --adapter-path "$L17" --save-path sft_model
fi
START=$([[ -d sft_model ]] && echo "$(pwd)/sft_model" || echo "$BASE")
echo "▸ DPO starting from: $START"

mlx_lm_lora.train --model "$START" --reference-model-path "$START" \
  --train --train-mode dpo --data data/mlx \
  --beta ${BETA:-0.1} --dpo-cpo-loss-type sigmoid \
  --iters ${ITERS:-200} --batch-size 2 --learning-rate 5e-6 \
  --adapter-path adapters/dpo 2>&1 | tee dpo_train.log

echo "START_MODEL=\"$START\"" > .state
cat <<EOT

▸ serve before and after (two terminals), then compare:
    mlx_lm.server --model "$START" --port 8081
    mlx_lm.server --model "$START" --adapter-path adapters/dpo --port 8082
    MLX_MODEL="$START" python pref_eval.py --label before --target mlx
    MLX_URL=http://localhost:8082/v1 MLX_MODEL="$START" python pref_eval.py --label after-dpo --target mlx
EOT
