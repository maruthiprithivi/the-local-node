#!/bin/bash
# Reference: 4B BF16 Ollama arm, as run on 14 Nov 2026 (one GB10 host).
# Ollama v0.40.13 image. Serves on 127.0.0.1:11435 inside --network none. KV cache is f16 (no bf16 KV option).
# GGUF_PATH = the BF16 GGUF converted from the same HF tree (see ../provenance/gguf.sha256).
set -eu
: "${MODEL_DIR:?}"   # unused for weights; GGUF_PATH is the imported file
: "${GGUF_PATH:?}"
: "${STOP_MARKER:?}"
: "${RESULTS:?}"
systemctl is-active --quiet bench.slice bench-memguard earlyoom
test ! -e "$STOP_MARKER"
ss -lnt | awk '$4 ~ /:11435$/ {found=1} END{exit found}'
docker rm -f bench-prefix-ollama-4b 2>/dev/null || true
docker run -d --name bench-prefix-ollama-4b \
  --network none --read-only --cap-drop ALL --security-opt no-new-privileges \
  --cgroup-parent bench.slice --memory 28g --memory-swap 28g --oom-score-adj 900 \
  --cpus 8 --gpus all \
  -v bench-prefix-ollama-4b-store:/root/.ollama \
  -v "${GGUF_PATH}:/gguf/qwen3.5-4b-bf16.gguf:ro" \
  -v "${RESULTS}:/out" \
  -e OLLAMA_HOST=http://127.0.0.1:11435 \
  -e OLLAMA_KV_CACHE_TYPE=f16 \
  -e OLLAMA_CONTEXT_LENGTH=8192 \
  -e OLLAMA_FLASH_ATTENTION=true \
  -e OLLAMA_NUM_PARALLEL=1 \
  -e OLLAMA_MAX_LOADED_MODELS=1 \
  -e OLLAMA_NO_CLOUD=true \
  -e OLLAMA_DEBUG=DEBUG \
  ollama/ollama@sha256:b2f0122c476bc9fe7ce679d8bb4bd555351e25e2554eefb156f61cb0a89cf429
echo "started bench-prefix-ollama-4b"
echo "Import (from a second exec): ollama create prefix-local -f /out/ollama-bf16-config/Modelfile"
echo "Probe must run in a driver image that has Transformers, with --network container:bench-prefix-ollama-4b"
