#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Lesson 14 · step 1 — vLLM in a container on the Spark (the production-grade server).
#
# Image: NVIDIA's NGC vLLM build supports the GB10 (arm64 + Blackwell). Pick the newest
# tag at https://catalog.ngc.nvidia.com (search "vllm"); override with VLLM_IMAGE.
#
#   --gpus all --ipc host          GPU + shared memory for the engine's workers
#   -v ~/.cache/huggingface        keep downloads between runs
#   --max-model-len 8192           caps KV per sequence (lesson 05)
#   --gpu-memory-utilization 0.8   share of the 128 GB vLLM may claim (weights + KV pool)
#   --enable-prefix-caching        automatic prefix caching (lesson 06)
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
MODEL=${1:-nvidia/Llama-3.1-8B-Instruct-FP8}
IMAGE=${VLLM_IMAGE:-nvcr.io/nvidia/vllm:25.09-py3}

docker rm -f vllm 2>/dev/null || true
docker run -d --name vllm --gpus all --ipc host -p 8000:8000 \
  -e HF_TOKEN="${HF_TOKEN:-}" -v ~/.cache/huggingface:/root/.cache/huggingface \
  "$IMAGE" vllm serve "$MODEL" --host 0.0.0.0 --port 8000 \
  --max-model-len 8192 --gpu-memory-utilization 0.8 --enable-prefix-caching

echo "▸ loading $MODEL (first run downloads it) — waiting for /health"
until curl -sf localhost:8000/health >/dev/null; do sleep 5; echo -n "."; done
echo " ready at http://$(hostname -I | awk '{print $1}'):8000/v1"
docker logs vllm 2>&1 | grep -iE "KV cache|maximum concurrency" | tail -3
