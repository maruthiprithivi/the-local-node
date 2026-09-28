#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Lesson 01b — the same harness against three Fireworks serverless models.
# Cost: 3 models × 6 requests × ~200 tokens ≈ one cent.
#
# Model ids change as the library changes. Look up current ones at
# https://app.fireworks.ai/models and edit the list below (full "accounts/..." ids).
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
cd "$(dirname "$0")"

MODELS=(
  accounts/fireworks/models/gpt-oss-120b      # large open MoE
  accounts/fireworks/models/gpt-oss-20b       # small MoE
  accounts/fireworks/models/llama-v3p1-8b-instruct  # small dense — may have moved; swap in any 7–8B
)

for m in "${MODELS[@]}"; do
  python bench_ttft.py --target fireworks --model "$m" --runs 5 || echo "  ✗ $m failed — check the id in the model library"
done

echo
echo "Now the long-prompt run on one model — watch TTFT move and ITL stay put:"
python bench_ttft.py --target fireworks --model "${MODELS[0]}" --runs 3 --prompt-tokens 8000

echo
echo "All rows are in results/01-latency.csv"
