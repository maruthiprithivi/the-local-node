#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Lesson 02 — mlx_lm.server: Apple's MLX runtime, usually the fastest path on M-series.
#
# MLX models on Hugging Face live under mlx-community/, already converted and
# quantized (…-4bit, …-8bit). The same library trains LoRA adapters in lesson 11.
#
# The `model` field in API requests must match what you serve here; felab reads
# it from MLX_MODEL in .env so the harness sends the right name.
#
# Usage:  bash serve_mlx.sh [HF_REPO]
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
MODEL=${1:-${MLX_MODEL:-mlx-community/Meta-Llama-3.1-8B-Instruct-4bit}}

echo "▸ mlx_lm.server  $MODEL  → http://localhost:8081/v1"
echo "  (tell the harness:  export MLX_MODEL=$MODEL)"
exec mlx_lm.server --model "$MODEL" --port 8081
