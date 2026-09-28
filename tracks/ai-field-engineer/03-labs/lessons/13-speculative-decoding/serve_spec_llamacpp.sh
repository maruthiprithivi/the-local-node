#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Lesson 13 · step 2 — llama.cpp with a draft model, on your Mac.
#
# Target: Llama-3.1-8B Q4.  Draft: Llama-3.2-1B Q4 (same tokenizer family — REQUIRED:
# the target verifies the draft's token ids, so both must share a vocabulary).
#
#   -hfd REPO:QUANT   draft model from Hugging Face  (--hf-repo-draft)
#   --draft-max 8     up to k=8 guesses per step
#   --draft-min 1
#   -ngld 99          draft on the GPU too
#
# Usage:  bash serve_spec_llamacpp.sh          # with speculation   → :8080
#         bash serve_spec_llamacpp.sh off      # same target, no draft (the baseline)
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
TARGET=${LLAMACPP_REPO:-bartowski/Meta-Llama-3.1-8B-Instruct-GGUF}:Q4_K_M
DRAFT=${DRAFT_REPO:-bartowski/Llama-3.2-1B-Instruct-GGUF}:Q4_K_M

if [[ "${1:-on}" == "off" ]]; then
  echo "▸ baseline (no draft) on :8080"
  exec llama-server -hf "$TARGET" -c 8192 -ngl 99 --port 8080
fi
echo "▸ speculative: target $TARGET + draft $DRAFT on :8080"
exec llama-server -hf "$TARGET" -hfd "$DRAFT" -c 8192 -ngl 99 -ngld 99 \
  --draft-max 8 --draft-min 1 --port 8080
