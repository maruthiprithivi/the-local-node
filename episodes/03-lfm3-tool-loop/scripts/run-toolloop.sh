#!/bin/bash
# LFM3-1.7B tool-loop check. llama.cpp b11981 llama-server (Q8_0) in a hardened container on an internal-only docker
# network; the driver toolloop.py runs in its own client container on that network, so it can reach only the model port.
# 1 slot per server, ctx 32K / 64K / 128K / 256K, seeds 0 1 2, temperature 0.6 (defaults; override with the env vars below).
#
# Required env:
#   MODEL_DIR     directory holding LFM3-1.7B-Q8_0.gguf (see download-models.sh)
#   LLAMA_DIR     unpacked llama.cpp b11981 release binaries (llama-server, libs)
#   CUDART_DIR    matching CUDA runtime libs for that release
# Optional env:
#   OUT_DIR (default ./runs)  CTXS  SEEDS  FL (filler lines/result, 75 ~= 3K tokens)  MAXT (max_tokens/turn)  TAG (file suffix)
#   IMAGE (default tlnode-runtime:0.1, build from ../docker/Dockerfile)
#   MEM_CGROUP    optional cgroup parent (e.g. a memory-capped systemd slice); empty = docker default
#   STOP_FILE     if this file exists, do not start
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
: "${MODEL_DIR:?set MODEL_DIR}"; : "${LLAMA_DIR:?set LLAMA_DIR}"; : "${CUDART_DIR:?set CUDART_DIR}"
R=${OUT_DIR:-$PWD/runs}; mkdir -p "$R"; R=$(cd "$R" && pwd)
IMAGE=${IMAGE:-tlnode-runtime:0.1}
L=$R/tl.log; NET=tl-toolloop-net; MEM=$R/mem.csv
CTXS=${CTXS:-"32768 65536 131072 262144"}; FL=${FL:-75}; MAXT=${MAXT:-2048}; TAG=${TAG:-}; SEEDS=${SEEDS:-"0 1 2"}
log(){ echo "- $(date '+%F %T %z') $*" | tee -a "$L"; }
memp(){ awk '/MemTotal/{t=$2}/MemAvailable/{a=$2} END{printf "%.1f", 100*(t-a)/t}' /proc/meminfo; }
memg(){ awk '/MemTotal/{t=$2}/MemAvailable/{a=$2} END{printf "%.2f", (t-a)/1048576}' /proc/meminfo; }
[ -n "${STOP_FILE:-}" ] && [ -f "$STOP_FILE" ] && { log "STOP marker"; exit 3; }
u=$(memp); awk -v u=$u 'BEGIN{exit !(u < 75)}' || { log "host mem $u % >= 75: not starting"; exit 3; }
CG=""; [ -n "${MEM_CGROUP:-}" ] && CG="--cgroup-parent $MEM_CGROUP"
SEC="$CG --memory 24g --memory-swap 24g --pids-limit 2048 --cap-drop ALL --security-opt no-new-privileges --read-only -u 1000:1000"
LIBS="-v $LLAMA_DIR:/opt/llama:ro -v $CUDART_DIR:/opt/cudart:ro -e LD_LIBRARY_PATH=/opt/llama:/opt/cudart"
docker network inspect $NET >/dev/null 2>&1 || docker network create --internal $NET >/dev/null
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv > "$R/gpu-before.csv"
log "start: host used $(memg) GiB ($(memp) %)"
# sampler: host + GPU (all compute apps) + server container memory every 5 s; kill test containers at >= 95 %
( echo "ts,host_used_gib,host_pct,gpu_apps_mib,llama_gpu_mib,srv_cgroup_bytes" > "$MEM"
  while [ ! -f "$R/SAMPLER_STOP" ]; do
    g=$(nvidia-smi --query-compute-apps=process_name,used_memory --format=csv,noheader,nounits 2>/dev/null)
    ga=$(echo "$g" | awk -F', ' '{s+=$2} END{print s+0}'); gl=$(echo "$g" | awk -F', ' '/llama/{s+=$2} END{print s+0}')
    cg=$(docker stats --no-stream --format '{{.MemUsage}}' tl-toolloop-srv 2>/dev/null | awk '{print $1}' | numfmt --from=iec-i 2>/dev/null || echo 0)
    p=$(memp); echo "$(date +%T),$(memg),$p,$ga,$gl,${cg:-0}" >> "$MEM"
    awk -v u=$p 'BEGIN{exit !(u >= 95)}' && { echo "KILL at $p %" >> "$L"; docker rm -f tl-toolloop-cli tl-toolloop-srv >/dev/null 2>&1; }
    sleep 5; done ) &
SP=$!
for ctx in $CTXS; do
  u=$(memp); awk -v u=$u 'BEGIN{exit !(u < 80)}' || { log "host mem $u % >= 80 before ctx $ctx: stopping"; break; }
  docker rm -f tl-toolloop-srv >/dev/null 2>&1
  docker run -d --name tl-toolloop-srv $SEC --network $NET --gpus all --tmpfs /tmp:size=1g $LIBS -v "$MODEL_DIR":/models:ro $IMAGE \
    /opt/llama/llama-server -m /models/LFM3-1.7B-Q8_0.gguf --host 0.0.0.0 --port 8080 -np 1 -c $ctx -ngl 999 --jinja --alias lfm3-1.7b --no-webui >/dev/null
  log "ctx $ctx: server started (host $(memp) %)"
  for s in $SEEDS; do
    u=$(memp); awk -v u=$u 'BEGIN{exit !(u < 85)}' || { log "host mem $u % >= 85: skip"; continue; }
    docker rm -f tl-toolloop-cli >/dev/null 2>&1
    timeout 2400 docker run --rm --name tl-toolloop-cli $SEC --memory 2g --network $NET --tmpfs /tmp:size=256m -v "$HERE/toolloop.py":/c/toolloop.py:ro -v "$R":/out $IMAGE \
      python3 -u /c/toolloop.py http://tl-toolloop-srv:8080 lfm3-1.7b $s $ctx /out/run-c$ctx-s$s$TAG.json --filler-lines $FL --max-tokens $MAXT > "$R/run-c$ctx-s$s$TAG.console.txt" 2>&1
    log "ctx $ctx seed $s: rc=$? $(grep RESULT "$R/run-c$ctx-s$s$TAG.console.txt" | cut -c1-400) (host $(memp) %)"
  done
  nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv > "$R/gpu-c$ctx.csv"
  docker logs tl-toolloop-srv > "$R/server-c$ctx.log" 2>&1; docker rm -f tl-toolloop-srv >/dev/null; sleep 5
done
touch "$R/SAMPLER_STOP"; wait $SP
docker rm -f tl-toolloop-cli tl-toolloop-srv >/dev/null 2>&1; docker network rm $NET >/dev/null 2>&1
log "DONE (host $(memp) %)"; touch "$R/TL_DONE"
