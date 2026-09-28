#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Lesson 11 · step 1 — LoRA on your Mac with MLX, on the SAME data as lesson 10.
#
# The base model is already 4-bit, so this is QLoRA: frozen 4-bit weights +
# small 16-bit adapters trained on top. That is why a 7B model trains on a laptop.
#
#   --data DIR         folder with train.jsonl + valid.jsonl (chat "messages" format)
#   --iters 300        optimizer steps. ~800 rows / batch 2 → 300 iters ≈ 0.75 epoch
#   --batch-size 2     lower to 1 if you run out of memory
#   --num-layers 8     adapt only the last 8 layers (fewer = less memory, less capacity)
#   --adapter-path     where the adapter weights (a few MB) are saved
#
# Watch "Val loss" every 50 iters: stop when it stops falling (Ctrl-C keeps the last save).
# Time: ~15–40 min on M-series depending on chip. Memory: ~6–10 GB for 7B.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
cd "$(dirname "$0")"
BASE=${MLX_BASE:-mlx-community/Qwen2.5-7B-Instruct-4bit}   # same family as lesson 10's base
[[ -f ../../data/tickets/train.jsonl ]] || python ../../data/make_tickets.py

mlx_lm.lora --model "$BASE" --train --data ../../data/tickets \
  --iters 300 --batch-size 2 --num-layers 8 \
  --steps-per-eval 50 --adapter-path adapters

echo "▸ adapter saved: $(du -sh adapters | cut -f1) — compare that with the base model's size"
echo "▸ next: bash 2_fuse_and_serve.sh"
