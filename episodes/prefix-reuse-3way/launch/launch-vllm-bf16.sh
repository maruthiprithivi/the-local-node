#!/bin/bash
# Reference: 4B unquantized BF16 vLLM arm, as run on 14 Nov 2026 (one GB10 host).
# Preconditions (not installed by this kit): an audited host watchdog (bench.slice, bench-memguard, earlyoom),
# MODEL_DIR = the BF16 HF tree (see ../provenance/hf-weights.sha256), STOP_MARKER, RESULTS. Checks memory headroom first.
set -eu
: "${MODEL_DIR:?}"
: "${STOP_MARKER:?}"
: "${RESULTS:?}"
systemctl is-active --quiet bench.slice bench-memguard earlyoom
test ! -e "$STOP_MARKER"
python3 - <<'PY'
import sys
d={}
for line in open("/proc/meminfo"):
    k,v=line.split(":",1); d[k]=int(v.split()[0])
used=d["MemTotal"]-d["MemAvailable"]
# 4B BF16 + runtime + 8192 KV headroom ~20 GiB additional
peak=used + 20*1048576
limit=0.85*d["MemTotal"]
print(f"used_gi={used/1048576:.2f} projected_gi={peak/1048576:.2f} limit85_gi={limit/1048576:.2f}")
if used/d["MemTotal"]>=0.85 or peak>limit:
    sys.exit(2)
PY
# confirm port 18000 is free
ss -lnt | awk '$4 ~ /:18000$/ {found=1} END{exit found}'
docker rm -f bench-prefix-vllm-4b 2>/dev/null || true
docker run -d --name bench-prefix-vllm-4b \
  --network none --read-only --cap-drop ALL --security-opt no-new-privileges \
  --cgroup-parent bench.slice --memory 28g --memory-swap 28g --oom-score-adj 900 \
  --cpus 8 --gpus all --shm-size 2g --tmpfs /tmp:rw,size=16g \
  -v bench-prefix-vllm-4b-jit:/cache \
  -e TMPDIR=/cache/tmp -e HOME=/cache/home \
  -e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1 -e HF_HOME=/cache/hf \
  -e XDG_CACHE_HOME=/cache/xdg -e TRITON_CACHE_DIR=/cache/triton \
  -e VLLM_SERVER_DEV_MODE=1 -e VLLM_NO_USAGE_STATS=1 \
  -v "${MODEL_DIR}:/models:ro" \
  -v "${RESULTS}:/out" \
  --entrypoint /bin/bash \
  eugr/spark-vllm-b12x@sha256:03a956544e9f9b4b7ba91690469fbe7848bdbef29a7d2e0f5788368467bb3595 \
  -c 'mkdir -p /cache/tmp /cache/home; exec python3 -m vllm.entrypoints.openai.api_server --model /models --served-model-name prefix-local --host 127.0.0.1 --port 18000 --dtype bfloat16 --enable-prefix-caching --enable-chunked-prefill --max-model-len 8192 --max-num-seqs 1 --max-num-batched-tokens 2048 --gpu-memory-utilization 0.15 --seed 0 --generation-config vllm --enable-prompt-tokens-details --enforce-eager'
echo "started bench-prefix-vllm-4b"
