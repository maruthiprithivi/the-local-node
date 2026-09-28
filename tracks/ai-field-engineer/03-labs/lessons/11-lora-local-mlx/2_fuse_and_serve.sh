#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Lesson 11 · step 2 — serve the fine-tune. Two options, same result:
#
#   A) adapter on top of the base at load time   (what multi-LoRA servers do)
#   B) fuse: bake the adapter into the weights    (one self-contained model folder)
#
# We fuse (B) because it is the simplest thing to hand over, then serve on :8081.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
cd "$(dirname "$0")"
BASE=${MLX_BASE:-mlx-community/Qwen2.5-7B-Instruct-4bit}

mlx_lm.fuse --model "$BASE" --adapter-path adapters --save-path fused
echo "▸ fused model in $(pwd)/fused — serving on :8081 (Ctrl-C to stop)"
exec mlx_lm.server --model "$(pwd)/fused" --port 8081
# option A instead:  mlx_lm.server --model "$BASE" --adapter-path adapters --port 8081
