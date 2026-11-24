#!/bin/bash
# Reference: 4B unquantized BF16 SGLang arm, as run on 14 Nov 2026 (one GB10 host).
# Source image lmsysorg/sglang@sha256:7f132b890eb6d55f6a8ded87f85e359434878d0fb7f6758582cf759ffb35b5d8,
# run by its local image Id below (docker save/load dropped the RepoDigest).
# This is the successful attempt-2 command. Attempt 1 at --mem-fraction-static 0.15 with no mamba cap failed
# (hybrid mamba state cache: total_rest_memory=-2.66 GB).
set -eu
: "${MODEL_DIR:?}"
: "${STOP_MARKER:?}"
: "${RESULTS:?}"
systemctl is-active --quiet bench.slice bench-memguard earlyoom
test ! -e "$STOP_MARKER"
ss -lnt | awk '$4 ~ /:30000$/ {found=1} END{exit found}'
docker rm -f bench-prefix-sglang-4b 2>/dev/null || true
IMG=sha256:67510d42555ae5e2d6b070e39ce932cd6c616924c10017a21fc0224a71439e18
docker run -d --name bench-prefix-sglang-4b \
  --network none --read-only --cap-drop ALL --security-opt no-new-privileges \
  --cgroup-parent bench.slice --memory 36g --memory-swap 36g --oom-score-adj 900 \
  --cpus 8 --gpus all --shm-size 2g --tmpfs /tmp:rw,size=16g \
  -v bench-prefix-sglang-4b-jit:/cache \
  -e TMPDIR=/cache/tmp -e HOME=/cache/home \
  -e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1 -e HF_HOME=/cache/hf \
  -e XDG_CACHE_HOME=/cache/xdg -e TRITON_CACHE_DIR=/cache/triton \
  -v "${MODEL_DIR}:/models:ro" \
  -v "${RESULTS}:/out" \
  --entrypoint /bin/bash \
  "$IMG" \
  -c 'mkdir -p /cache/tmp /cache/home; exec python3 -m sglang.launch_server --model-path /models --served-model-name prefix-local --host 127.0.0.1 --port 30000 --dtype bfloat16 --kv-cache-dtype auto --context-length 8192 --mem-fraction-static 0.22 --max-mamba-cache-size 5 --max-running-requests 1 --max-total-tokens 8192 --chunked-prefill-size 2048 --disable-cuda-graph'
echo "started bench-prefix-sglang-4b"
