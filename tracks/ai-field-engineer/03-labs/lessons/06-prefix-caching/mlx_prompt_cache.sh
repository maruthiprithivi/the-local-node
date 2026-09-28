#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Lesson 06 · MLX variant — the same idea, done by hand.
#
# mlx_lm.cache_prompt runs prefill ONCE on the preamble and saves the KV cache
# to disk. mlx_lm.generate then loads that file and only prefills the new question.
# This is literally what a server-side prefix cache does, made visible.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
cd "$(dirname "$0")"
MODEL=${MLX_MODEL:-mlx-community/Meta-Llama-3.1-8B-Instruct-4bit}

# Dump the same preamble prefix_bench.py uses
python -c "from prefix_bench import PREAMBLE; print(PREAMBLE)" > preamble.txt

echo "▸ 1. cold: prefill the ~3k-token preamble + question (watch 'Prompt: … tokens-per-sec')"
time mlx_lm.generate --model "$MODEL" --max-tokens 40 \
  --prompt "$(cat preamble.txt) Question: How do I rotate my API key?"

echo "▸ 2. cache the preamble once"
mlx_lm.cache_prompt --model "$MODEL" --prompt "$(cat preamble.txt)" --prompt-cache-file preamble.safetensors

echo "▸ 3. warm: only the question is prefilled"
time mlx_lm.generate --prompt-cache-file preamble.safetensors --max-tokens 40 \
  --prompt " Question: How do I rotate my API key?"
