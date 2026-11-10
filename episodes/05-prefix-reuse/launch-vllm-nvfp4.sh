#!/bin/bash
# Run only after auditing watchdogs and confirming no active conflicting workload.
set -eu
: "${MODEL_DIR:?Set absolute model directory}"
: "${STOP_MARKER:?Set audited watchdog stop-marker path}"
systemctl is-active --quiet bench.slice bench-memguard earlyoom
test ! -e "$STOP_MARKER"
awk '/^MemTotal:/{t=$2} /^MemAvailable:/{a=$2} END{u=t-a; peak=u+.35*t+31.5*1048576; limit=.85*t-20*1048576; printf "unproven startup projection %.2f GiB, threshold minus 20 GiB %.2f GiB\n",peak/1048576,limit/1048576; exit (u/t>=.85 || peak>limit)}' /proc/meminfo
docker run -d --name bench-prefix-vllm2 --network none --read-only --cap-drop ALL --security-opt no-new-privileges --cgroup-parent bench.slice --memory 80g --memory-swap 80g --oom-score-adj 900 --cpus 8 --gpus all --shm-size 2g --tmpfs /tmp:rw,size=16g -v bench-prefix-vllm-jit:/cache -e TMPDIR=/cache/tmp -e HOME=/cache/home -e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1 -e HF_HOME=/cache/hf -e XDG_CACHE_HOME=/cache/xdg -e TRITON_CACHE_DIR=/cache/triton -e VLLM_SERVER_DEV_MODE=1 -e VLLM_NO_USAGE_STATS=1 -v "${MODEL_DIR}:/models:ro" --entrypoint /bin/bash eugr/spark-vllm-b12x@sha256:03a956544e9f9b4b7ba91690469fbe7848bdbef29a7d2e0f5788368467bb3595 -c 'mkdir -p /cache/tmp /cache/home; exec python3 -m vllm.entrypoints.openai.api_server --model /models --served-model-name prefix-local --host 127.0.0.1 --port 8000 --dtype bfloat16 --kv-cache-dtype fp8 --enable-prefix-caching --enable-chunked-prefill --max-model-len 8192 --max-num-seqs 1 --max-num-batched-tokens 2048 --gpu-memory-utilization .35 --seed 0 --generation-config vllm --enable-prompt-tokens-details --enforce-eager'
