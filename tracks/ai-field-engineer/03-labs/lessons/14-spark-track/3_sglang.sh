#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Lesson 14 · step 3 — SGLang: same model, different engine, RadixAttention prefix cache.
# Stops vLLM first (one engine at a time on one GPU). Serves on :30000.
#
# Image: SGLang publishes Spark/arm64 builds — check https://hub.docker.com/r/lmsysorg/sglang/tags
# for the current Spark tag and override with SGLANG_IMAGE.
#   --mem-fraction-static 0.75   share of memory for weights + KV pool
#   --enable-cache-report        adds cached_tokens to usage → proves prefix hits
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
MODEL=${1:-Qwen/Qwen3-8B}
IMAGE=${SGLANG_IMAGE:-lmsysorg/sglang:spark}

docker rm -f vllm sglang 2>/dev/null || true
docker run -d --name sglang --gpus all --ipc host -p 30000:30000 \
  -e HF_TOKEN="${HF_TOKEN:-}" -v ~/.cache/huggingface:/root/.cache/huggingface \
  "$IMAGE" python3 -m sglang.launch_server --model-path "$MODEL" --host 0.0.0.0 --port 30000 \
  --mem-fraction-static 0.75 --enable-cache-report

until curl -sf localhost:30000/health >/dev/null; do sleep 5; echo -n "."; done
echo " ready. From the Mac:"
echo "  SPARK_URL=http://$(hostname -I | awk '{print $1}'):30000/v1 SPARK_MODEL=$MODEL \\"
echo "    python ../06-prefix-caching/prefix_bench.py --target spark --usage"
