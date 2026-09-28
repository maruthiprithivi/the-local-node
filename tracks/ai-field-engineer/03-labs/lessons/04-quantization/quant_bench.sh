#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Lesson 04 · step 1 — the same model at three precisions, benchmarked raw.
#
#   Q8_0    ~8.5 bits/weight   ≈ 8.5 GB for 8B   near-lossless
#   Q4_K_M  ~4.8 bits/weight   ≈ 4.9 GB for 8B   the default everybody ships
#   Q3_K_M  ~3.9 bits/weight   ≈ 4.0 GB for 8B   where quality starts to slip
#
# llama-bench runs WITHOUT a server: pure engine speed.
#   -p 512   prefill 512 tokens  → "pp512" tok/s  (compute-bound)
#   -n 128   generate 128 tokens → "tg128" tok/s  (bandwidth-bound)  ← the one we check
#
# Downloads ~17 GB in total. Delete models/ afterwards if disk is tight.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
cd "$(dirname "$0")"
REPO=${LLAMACPP_REPO:-bartowski/Meta-Llama-3.1-8B-Instruct-GGUF}
QUANTS=(${QUANTS:-Q8_0 Q4_K_M Q3_K_M})
mkdir -p models bench

command -v hf >/dev/null || pip install -q "huggingface_hub[cli]"

for q in "${QUANTS[@]}"; do
  echo "▸ $q — download (skipped if present)"
  hf download "$REPO" --include "*${q}.gguf" --local-dir models >/dev/null
  f=$(ls models/*"${q}".gguf | head -1)
  echo "▸ $q — llama-bench on $(du -h "$f" | cut -f1)"
  llama-bench -m "$f" -p 512 -n 128 -ngl 99 -o json > "bench/${q}.json"
done

echo
python ceiling_check.py
