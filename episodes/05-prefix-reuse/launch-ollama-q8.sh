#!/bin/bash
# Separate Q8/FP16-KV experiment, NOT equivalent to NVFP4.
set -eu
: "${ARTIFACT_DIR:?Set directory containing gguf and ollama-q8-config}"
: "${STOP_MARKER:?Set audited watchdog stop-marker path}"
R=$ARTIFACT_DIR
systemctl is-active --quiet bench.slice bench-memguard earlyoom
test ! -e "$STOP_MARKER"
# Separate common-Q8 arm: no claim of equivalence to the NVFP4 checkpoint.
awk '/^MemTotal:/{t=$2} /^MemAvailable:/{a=$2} END{peak=(t-a)+78*1048576; limit=.85*t-20*1048576; print "common-Q8 startup estimate GiB",peak/1048576,"limit-minus-headroom",limit/1048576; exit(peak>limit)}' /proc/meminfo
printf '2bb22714289826d7b9e0ba376c3ce47d08bce39abe598745857c44d88c09bdbf  %s\n' "$R/gguf/qwen3.8-27b-q8_0.gguf" | sha256sum -c
mkdir -p "$R/ollama-q8-config"
printf 'FROM /gguf/qwen3.8-27b-q8_0.gguf
PARAMETER num_ctx 8192
' > "$R/ollama-q8-config/Modelfile"
docker run -d --name bench-prefix-ollama-q8 --network none --read-only --cap-drop ALL --security-opt no-new-privileges --cgroup-parent bench.slice --memory 80g --memory-swap 80g --oom-score-adj 900 --cpus 8 --gpus all --tmpfs /tmp:rw,size=2g -e OLLAMA_HOST=127.0.0.1:11434 -e OLLAMA_NO_CLOUD=1 -e OLLAMA_DEBUG=1 -e OLLAMA_NUM_PARALLEL=1 -e OLLAMA_CONTEXT_LENGTH=8192 -e OLLAMA_MAX_LOADED_MODELS=1 -e OLLAMA_FLASH_ATTENTION=1 -e OLLAMA_KV_CACHE_TYPE=f16 -v bench-prefix-ollama-q8-store:/root/.ollama -v "$R/gguf:/gguf:ro" -v "$R/ollama-q8-config:/config:ro" ollama/ollama@sha256:55d6d58fce77338d8b626abbbbec63b79deeb24db3fd67b8a99951a84083552f serve
sleep 3
docker exec bench-prefix-ollama-q8 ollama create prefix-local -f /config/Modelfile > "$R/ollama-q8-import.txt" 2>&1
