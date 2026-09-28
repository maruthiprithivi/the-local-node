#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Lesson 11 · step 3 — base vs local fine-tune: lesson 09's harness, same 60 tickets.
#
# mlx_lm.server loads whichever model a request names (one at a time), so the server
# from step 2 can answer for both: first the fused fine-tune, then the base (it reloads
# once in between — the first base request is slow, which is fine for an eval).
# If your mlx-lm version refuses, run the base on another port and set
#     MLX_URL=http://localhost:8082/v1  for the second command.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
cd "$(dirname "$0")"
BASE=${MLX_BASE:-mlx-community/Qwen2.5-7B-Instruct-4bit}

python ../09-eval-harness/evaluate.py "mlx:$(pwd)/fused" "mlx:$BASE" --n 60
echo "▸ Compare with lesson 10's Fireworks row in results/09-eval.csv — then fill in COMPARISON.md"
