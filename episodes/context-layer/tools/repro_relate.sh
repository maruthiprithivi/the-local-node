#!/usr/bin/env bash
# One command repro of the relate (Neo4j) run: ./tools/repro_relate.sh
#   REMOTE=<ssh alias>  run the database container on that host (loopback only, reached through an ssh tunnel);
#                       empty means local docker. N=<runs> (default 5). OUT=<folder> (default evidence/relate).
# Relate (Neo4j Desktop) wraps a Neo4j DBMS; here that DBMS is a pinned Neo4j Community container (tag + digest),
# file mode (store on the container disk, the Desktop default). Random throwaway password, kept only in a
# gitignored env file (.secrets/relate.env, mode 600, deleted on exit) and never printed. Torn down on exit.
# Load guard (remote): refuses to start at >= 85% cpu or memory, aborts at >= 95%.
set -euo pipefail
cd "$(dirname "$0")/.."
TAG="neo4j:2026.10.2-community"
IMAGE="$TAG@sha256:4a2fd4f41ce384aa7d6a74b399f22c202e154f3966119c28a18ed9a500904f5e"   # index digest, pinned 2026-11-14
N="${N:-5}"; REMOTE="${REMOTE:-}"; OUT="${OUT:-evidence/relate}"; PORT="${PORT:-57687}"
BATCH="relate-$(date -u +%Y%m%dT%H%M%SZ)"; NAME="ctxlayer-relate-${BATCH##*-}"
SECRETS=".secrets/relate.env"
dock() { if [ -n "$REMOTE" ]; then ssh -o BatchMode=yes "$REMOTE" "docker $(printf "%q " "$@")"; else docker "$@"; fi; }
load_pct() {  # max(cpu load1/cores, memory used) as an integer percent
  local cmd='awk -v c=$(nproc) "{printf \"%d\", 100*\$1/c}" /proc/loadavg; echo " $(free | awk "/Mem:/{printf \"%d\", 100*(\$2-\$7)/\$2}")"'
  local o; if [ -n "$REMOTE" ]; then o=$(ssh -o BatchMode=yes "$REMOTE" "$cmd"); else o=$(bash -c "$cmd"); fi
  set -- $o; echo $(( $1 > $2 ? $1 : $2 ))
}
guard() { local p; p=$(load_pct); echo "load check ($1): ${p}%"; echo "$p" >> "$OUT/$BATCH.load"; if [ "$p" -ge "$2" ]; then echo "load ${p}% >= $2%, stopping"; exit 3; fi; }
mkdir -p "$OUT" runs .secrets; chmod 700 .secrets
TUN=""; PULLED=0
cleanup() {
  set +e
  [ -n "$TUN" ] && kill "$TUN" 2>/dev/null
  dock rm -f "$NAME" >/dev/null 2>&1
  [ "$PULLED" = 1 ] && dock rmi "$IMAGE" >/dev/null 2>&1
  rm -f "$SECRETS"
  echo "torn down: container removed, password file deleted$([ "$PULLED" = 1 ] && echo ', image we pulled removed')"
}
trap cleanup EXIT
guard "before start" 85
dock image inspect "$IMAGE" >/dev/null 2>&1 || { PULLED=1; dock pull -q "$IMAGE" >/dev/null; }
( umask 077; printf 'NEO4J_AUTH=neo4j/%s\n' "$(head -c 24 /dev/urandom | base64 | tr -dc A-Za-z0-9)" > "$SECRETS" )
T0=$(date +%s.%N)
{ cat "$SECRETS"; printf 'NEO4J_server_memory_heap_max__size=1g\nNEO4J_server_memory_pagecache_size=256m\n'; } |
  dock run -d --name "$NAME" --env-file /dev/stdin --memory 2g --cpus 2 --pids-limit 512 \
  -p "127.0.0.1:$PORT:7687" "$IMAGE" >/dev/null
if [ -n "$REMOTE" ]; then
  ssh -o BatchMode=yes -o ExitOnForwardFailure=yes -N -L "127.0.0.1:$PORT:127.0.0.1:$PORT" "$REMOTE" & TUN=$!
fi
for i in $(seq 1 120); do dock logs "$NAME" 2>&1 | grep -q 'Started\.' && break; sleep 1; done
T1=$(date +%s.%N)
set -a; . "$SECRETS"; set +a
export CTXLAYER_NEO4J_URI="bolt://127.0.0.1:${PORT}" CTXLAYER_NEO4J_USER=neo4j CTXLAYER_NEO4J_PASSWORD="${NEO4J_AUTH#neo4j/}"
unset NEO4J_AUTH
PY=".venv/bin/python"; [ -x "$PY" ] || { python3 -m venv .venv; .venv/bin/pip install -q -e . matplotlib==3.9.2; }
for i in $(seq 1 30); do "$PY" -c 'import os; from neo4j import GraphDatabase as G; G.driver(os.environ["CTXLAYER_NEO4J_URI"], auth=("neo4j", os.environ["CTXLAYER_NEO4J_PASSWORD"])).verify_connectivity()' 2>/dev/null && break; sleep 1; done
{ echo "image: $TAG"; echo "digest: $(dock image inspect "$IMAGE" --format '{{index .RepoDigests 0}}')"
  echo "arch: $(dock image inspect "$IMAGE" --format '{{.Architecture}}')"
  "$PY" -c 'import os; from neo4j import GraphDatabase as G
d=G.driver(os.environ["CTXLAYER_NEO4J_URI"], auth=("neo4j", os.environ["CTXLAYER_NEO4J_PASSWORD"]))
r=d.execute_query("CALL dbms.components() YIELD name, versions, edition RETURN name, versions[0] AS v, edition").records[0]
print("neo4j:", r[1], r[2]); d.close()'
  echo "driver: neo4j-python $("$PY" -c 'import neo4j; print(neo4j.__version__)')"
  echo "container_start_to_ready_s: $(python3 -c "print(round($T1-$T0,2))")"
  echo "mode: file (store on container disk, Desktop default); in-memory vs file crash durability not measured"
  echo "memory_cap: 2g  cpus: 2  heap: 1g  pagecache: 256m  bind: 127.0.0.1 only"; echo "batch: $BATCH  runs: $N"; } > "$OUT/$BATCH.meta.txt"
for n in $(seq 1 "$N"); do
  guard "before run $n" 95
  RID="${BATCH}-seed7-$(git rev-parse --short HEAD 2>/dev/null || echo nogit)-r$n"
  "$PY" -m ctxlayer run --backend relate --out runs --run-id "$RID" >/dev/null
  echo "run $n done: $RID"
done
"$PY" tools/report.py runs "$OUT/$BATCH" relate "$BATCH" >/dev/null
cp runs/${BATCH}-*.jsonl "$OUT/$BATCH/" 2>/dev/null || true
echo "evidence: $OUT/$BATCH (summary.md, CSVs, charts); raw: runs/${BATCH}-*.jsonl"
