#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Lesson 02 — llama.cpp's llama-server: the engine Ollama wraps, with the flags visible.
#
# Every flag here maps to a concept you will be asked about:
#   -hf repo:QUANT     download a GGUF from Hugging Face at that quantization (lesson 04)
#   -c 8192            context window in tokens → sizes the KV cache (lesson 05)
#   -ngl 99            offload all layers to the GPU (Metal). Fewer = CPU offload (video 7)
#   --parallel 4       4 slots = up to 4 sequences batched together (lesson 03)
#                      NOTE: the context is SPLIT across slots → 8192/4 = 2048 each
#   --port 8080        OpenAI-compatible API at http://localhost:8080/v1
#
# Usage:  bash serve_llamacpp.sh [QUANT] [CTX] [SLOTS]
#         bash serve_llamacpp.sh Q4_K_M 8192 4
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
QUANT=${1:-Q4_K_M}
CTX=${2:-8192}
SLOTS=${3:-4}
REPO=${LLAMACPP_REPO:-bartowski/Meta-Llama-3.1-8B-Instruct-GGUF}

echo "▸ llama-server  $REPO:$QUANT  ctx=$CTX  slots=$SLOTS  → http://localhost:8080/v1"
exec llama-server -hf "$REPO:$QUANT" -c "$CTX" -ngl 99 --parallel "$SLOTS" --port 8080 \
  --metrics            # Prometheus metrics at /metrics — handy in lesson 03
