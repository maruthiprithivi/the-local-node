#!/bin/bash
# Parts A and B of the LFM3 test (decode speed and footprint).
# Part A: llama-bench pp512/tg128, 5 reps per quant, container with --network none.
# Part B: llama-server Q8_0 (1 slot, 32K ctx, internal-only network) + client.py: 1 warm-up, 5 rounds of short chat + 512-token decode, concurrency 1.
# Same env as run-toolloop.sh (MODEL_DIR, LLAMA_DIR, CUDART_DIR, optional OUT_DIR, IMAGE, MEM_CGROUP).
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
: "${MODEL_DIR:?set MODEL_DIR}"; : "${LLAMA_DIR:?set LLAMA_DIR}"; : "${CUDART_DIR:?set CUDART_DIR}"
R=${OUT_DIR:-$PWD/runs-decode}; mkdir -p "$R"; R=$(cd "$R" && pwd); IMAGE=${IMAGE:-tlnode-runtime:0.1}
L=$R/decode.log; NET=tl-decode-net
log(){ echo "- $(date '+%F %T %z') $*" | tee -a "$L"; }
memg(){ awk '/MemTotal/{t=$2}/MemAvailable/{a=$2} END{printf "%.2f", (t-a)/1048576}' /proc/meminfo; }
memp(){ awk '/MemTotal/{t=$2}/MemAvailable/{a=$2} END{printf "%.1f", 100*(t-a)/t}' /proc/meminfo; }
u=$(memp); awk -v u=$u 'BEGIN{exit !(u < 75)}' || { log "host mem $u % >= 75: not starting"; exit 3; }
CG=""; [ -n "${MEM_CGROUP:-}" ] && CG="--cgroup-parent $MEM_CGROUP"
SEC="$CG --memory 24g --memory-swap 24g --pids-limit 2048 --cap-drop ALL --security-opt no-new-privileges --read-only -u 1000:1000"
LIBS="-v $LLAMA_DIR:/opt/llama:ro -v $CUDART_DIR:/opt/cudart:ro -e LD_LIBRARY_PATH=/opt/llama:/opt/cudart"
docker network inspect $NET >/dev/null 2>&1 || docker network create --internal $NET >/dev/null
for q in Q4_K_M Q8_0 BF16; do
  log "A $q: llama-bench (host mem $(memp) %)"
  docker run --rm --name tl-bench $SEC --network none --gpus all --tmpfs /tmp:size=1g $LIBS -v "$MODEL_DIR":/models:ro $IMAGE \
    /opt/llama/llama-bench -m /models/LFM3-1.7B-$q.gguf -ngl 99 -p 512 -n 128 -r 5 -o json > "$R/bench-$q.json" 2> "$R/bench-$q.err"; log "A $q rc=$?"
done
q=Q8_0; base=$(memg)
docker rm -f tl-srv >/dev/null 2>&1
docker run -d --name tl-srv $SEC --network $NET --gpus all --tmpfs /tmp:size=1g $LIBS -v "$MODEL_DIR":/models:ro $IMAGE \
  /opt/llama/llama-server -m /models/LFM3-1.7B-$q.gguf --host 0.0.0.0 --port 8080 -np 1 -c 32768 -ngl 999 --jinja --alias lfm3-1.7b --no-webui >/dev/null
docker run --rm --name tl-cli $SEC --memory 2g --network $NET --tmpfs /tmp:size=256m -v "$HERE/client.py":/c/client.py:ro -v "$R":/out $IMAGE \
  python3 -u /c/client.py http://tl-srv:8080 auto lfm3-$q /out/serve-$q.json --rounds-idle 5 --rounds-conc 0 > "$R/serve-$q.console.txt" 2>&1
after=$(memg); st=$(docker stats --no-stream --format '{{.MemUsage}}' tl-srv)
log "B $q: host used before $base GiB, after load+requests $after GiB, container $st"
docker logs tl-srv > "$R/serve-$q.server.log" 2>&1; docker rm -f tl-srv >/dev/null; docker network rm $NET >/dev/null 2>&1
log DONE
