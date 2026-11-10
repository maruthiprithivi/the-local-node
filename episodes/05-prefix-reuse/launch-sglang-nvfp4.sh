#!/bin/bash
# Run only after auditing watchdogs and confirming no active conflicting workload.
set -eu
: "${MODEL_DIR:?Set absolute model directory}"
: "${STOP_MARKER:?Set audited watchdog stop-marker path}"
systemctl is-active --quiet bench.slice bench-memguard earlyoom
test ! -e "$STOP_MARKER"
awk '/^MemTotal:/{t=$2} /^MemAvailable:/{a=$2} END{u=t-a; peak=u+.35*t+31.5*1048576; limit=.85*t-20*1048576; printf "unproven startup projection %.2f GiB, threshold minus 20 GiB %.2f GiB\n",peak/1048576,limit/1048576; exit (u/t>=.85 || peak>limit)}' /proc/meminfo
docker run -d --name bench-prefix-sglang --network none --read-only --cap-drop ALL --security-opt no-new-privileges --cgroup-parent bench.slice --memory 80g --memory-swap 80g --oom-score-adj 900 --cpus 8 --gpus all --shm-size 2g --tmpfs /tmp:rw,size=16g -v bench-prefix-sglang-jit:/cache -e TMPDIR=/cache/tmp -e HOME=/cache/home -e XDG_CACHE_HOME=/cache/xdg -e TORCHINDUCTOR_CACHE_DIR=/cache/torch -e TRITON_CACHE_DIR=/cache/triton -e HF_HOME=/cache/hf -e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1 -v "${MODEL_DIR}:/models:ro" --entrypoint /bin/bash lmsysorg/sglang@sha256:7f132b890eb6d55f6a8ded87f85e359434878d0fb7f6758582cf759ffb35b5d8 -c 'mkdir -p /cache/tmp /cache/home; exec python3 -m sglang.launch_server --model-path /models --served-model-name prefix-local --host 127.0.0.1 --port 30000 --context-length 8192 --mem-fraction-static .35 --max-running-requests 1 --max-total-tokens 8192 --max-mamba-cache-size 5 --chunked-prefill-size 2048 --disable-cuda-graph --attention-backend flashinfer --kv-cache-dtype fp8_e4m3 --mamba-ssm-dtype float32 --mamba-radix-cache-strategy extra_buffer --enable-metrics'
