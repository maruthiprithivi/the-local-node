#!/usr/bin/env bash
# One command repro of the relate (Neo4j) crash durability test: ./tools/crash_relate.sh
#   REMOTE=<ssh alias> (empty = local docker)  N=<reps per mode> (default 5)
#   TAIL_WAIT=<tail acks before the kill> (default 25)  OUT=<folder> (default evidence/relate/crash)
# Per rep and mode: fresh pinned container, write the full JML change set (people, agents, MCP servers, skills),
# keep appending tail records one transaction each, docker kill -s KILL while that stream runs (right after an
# acknowledged write), docker start on the same store, read everything back, score (python -m ctxlayer.crash).
#   file:      /data on a named docker volume (survives restart), the Neo4j Desktop default
#   in-memory: /data on tmpfs (--tmpfs /data:size=1g), models an in-memory store; tmpfs is empty again after a restart.
#              1g because Neo4j preallocates transaction logs and goes read-only on a 512m tmpfs; tmpfs pages count
#              against the container memory cgroup, so this mode gets --memory 3g (heap and pagecache unchanged).
# Seed 7 (workload/jml.yaml). Throwaway password in gitignored .secrets/ (mode 600, deleted on exit), never printed.
# Load guard (remote): refuse to start at >= 85%, abort at >= 95%.
set -euo pipefail
cd "$(dirname "$0")/.."
TAG="neo4j:2026.10.2-community"
IMAGE="$TAG@sha256:4a2fd4f41ce384aa7d6a74b399f22c202e154f3966119c28a18ed9a500904f5e"   # index digest, pinned 2026-11-14
N="${N:-5}"; REMOTE="${REMOTE:-}"; OUT="${OUT:-evidence/relate/crash}"; PORT="${PORT:-57688}"; TAIL_WAIT="${TAIL_WAIT:-25}"
BATCH="crash-$(date -u +%Y%m%dT%H%M%SZ)"; D="$OUT/$BATCH"; SECRETS=".secrets/relate-crash.env"
dock() { if [ -n "$REMOTE" ]; then ssh -o BatchMode=yes "$REMOTE" "docker $(printf "%q " "$@")"; else docker "$@"; fi; }
load_pct() {
  local cmd='awk -v c=$(nproc) "{printf \"%d\", 100*\$1/c}" /proc/loadavg; echo " $(free | awk "/Mem:/{printf \"%d\", 100*(\$2-\$7)/\$2}")"'
  local o; if [ -n "$REMOTE" ]; then o=$(ssh -o BatchMode=yes "$REMOTE" "$cmd"); else o=$(bash -c "$cmd"); fi
  set -- $o; echo $(( $1 > $2 ? $1 : $2 ))
}
guard() { local p; p=$(load_pct); echo "load check ($1): ${p}%"; echo "$1 ${p}" >> "$D/load.txt"; if [ "$p" -ge "$2" ]; then echo "load ${p}% >= $2%, stopping"; exit 3; fi; }
mkdir -p "$D" .secrets; chmod 700 .secrets
TUN=""; PULLED=0; NAME=""; VOL=""; WPID=""
rmc() { [ -n "$NAME" ] && dock rm -f "$NAME" >/dev/null 2>&1; [ -n "$VOL" ] && dock volume rm "$VOL" >/dev/null 2>&1; NAME=""; VOL=""; true; }
cleanup() {
  set +e
  [ -n "$WPID" ] && kill "$WPID" 2>/dev/null
  [ -n "$TUN" ] && kill "$TUN" 2>/dev/null
  rmc; [ "$PULLED" = 1 ] && dock rmi "$IMAGE" >/dev/null 2>&1
  rm -f "$SECRETS"; echo "torn down: containers and volumes removed, password file deleted$([ "$PULLED" = 1 ] && echo ', pulled image removed')"
}
trap cleanup EXIT
guard "before start" 85
dock image inspect "$IMAGE" >/dev/null 2>&1 || { PULLED=1; dock pull -q "$IMAGE" >/dev/null; }
( umask 077; printf 'NEO4J_AUTH=neo4j/%s\n' "$(head -c 24 /dev/urandom | base64 | tr -dc A-Za-z0-9)" > "$SECRETS" )
PY=".venv/bin/python"; [ -x "$PY" ] || { python3 -m venv .venv; .venv/bin/pip install -q -e .; }
set -a; . "$SECRETS"; set +a
export CTXLAYER_NEO4J_URI="bolt://127.0.0.1:${PORT}" CTXLAYER_NEO4J_USER=neo4j CTXLAYER_NEO4J_PASSWORD="${NEO4J_AUTH#neo4j/}"
unset NEO4J_AUTH
if [ -n "$REMOTE" ]; then ssh -o BatchMode=yes -o ExitOnForwardFailure=yes -N -L "127.0.0.1:$PORT:127.0.0.1:$PORT" "$REMOTE" & TUN=$!; sleep 2; fi
started() { dock logs "$NAME" 2>&1 | grep -c 'Started\.' || true; }
wait_started() { for i in $(seq 1 180); do [ "$(started)" -ge "$1" ] && return 0; sleep 0.5; done; echo "neo4j did not start"; exit 4; }
connect() { for i in $(seq 1 60); do "$PY" -c 'import os; from neo4j import GraphDatabase as G; G.driver(os.environ["CTXLAYER_NEO4J_URI"], auth=("neo4j", os.environ["CTXLAYER_NEO4J_PASSWORD"])).verify_connectivity()' 2>/dev/null && return 0; sleep 0.5; done; echo "no bolt"; exit 4; }
{ echo "image: $TAG"; echo "digest: $(dock image inspect "$IMAGE" --format '{{index .RepoDigests 0}}')"
  echo "arch: $(dock image inspect "$IMAGE" --format '{{.Architecture}}')"; echo "docker: $(dock version --format '{{.Server.Version}}')"
  echo "driver: neo4j-python $("$PY" -c 'import neo4j; print(neo4j.__version__)')"; echo "commit: $(git rev-parse --short HEAD)"
  echo "seed: 7  reps_per_mode: $N  tail_acks_before_kill: >= $TAIL_WAIT  kill: docker kill -s KILL"
  echo "caps: --memory 2g (file) / 3g (in-memory, 1g tmpfs counts against it) --cpus 2 heap 1g pagecache 256m, bind 127.0.0.1 only"; echo "batch: $BATCH"; } > "$D/meta.txt"
for mode in file in-memory; do
  for rep in $(seq 1 "$N"); do
    guard "before $mode r$rep" 95
    NAME="ctxlayer-crash-${BATCH##*-}-${mode}-r$rep" ; R="$D/${mode}-r$rep"
    if [ "$mode" = file ]; then VOL="$NAME-data"; dock volume create "$VOL" >/dev/null; STORE=(-v "$VOL:/data"); MEM=2g; else STORE=(--tmpfs /data:rw,size=1g); MEM=3g; fi
    { grep NEO4J_AUTH "$SECRETS"; printf 'NEO4J_server_memory_heap_max__size=1g\nNEO4J_server_memory_pagecache_size=256m\n'; } |
      dock run -d --name "$NAME" --env-file /dev/stdin --memory "$MEM" --cpus 2 --pids-limit 512 "${STORE[@]}" \
      -p "127.0.0.1:$PORT:7687" "$IMAGE" >/dev/null
    wait_started 1; connect
    rm -f "$R.state.json" "$R.state.json.tail"
    "$PY" -m ctxlayer.crash write --state "$R.state.json" > "$R.writer.log" 2>&1 & WPID=$!
    for i in $(seq 1 600); do [ -f "$R.state.json.tail" ] && [ "$(wc -l < "$R.state.json.tail")" -ge "$TAIL_WAIT" ] && break; kill -0 "$WPID" 2>/dev/null || { echo "writer died"; cat "$R.writer.log"; exit 5; }; sleep 0.2; done
    dock kill -s KILL "$NAME" >/dev/null; KILL=$(date +%s.%N)
    kill "$WPID" 2>/dev/null || true; wait "$WPID" 2>/dev/null || true; WPID=""   # the writer may already have exited on the kill
    T0=$(date +%s.%N); dock start "$NAME" >/dev/null; wait_started 2; connect; T1=$(date +%s.%N)
    "$PY" -m ctxlayer.crash verify --state "$R.state.json" --out "$R.verify.json" --mode "$mode" --rep "$rep" \
      --kill-epoch "$KILL" --restart-s "$(python3 -c "print(round($T1-$T0,2))")" | tee "$R.verify.line"
    dock logs "$NAME" 2>&1 | grep -iE 'recover|Started|store' > "$R.neo4j.log" || true
    rmc
  done
done
"$PY" tools/crash_report.py "$D"
echo "evidence: $D (results.csv, summary.md, raw per rep)"
