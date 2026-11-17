#!/usr/bin/env bash
# One-command repro of the hand-built neo4j (Community server) adapter.
#   N=1 ./tools/repro_neo4j.sh
# Optional: CTXLAYER_SSH_HOST=user@host and CTXLAYER_SSH_OPTS='-o BatchMode=yes ...'
#           to start the CPU-only container on that host (loopback + ssh tunnel).
# Empty means local docker. OUT=evidence/neo4j. PORT=57688 (avoids the relate 57687).
# Random throwaway password in .secrets/neo4j.env (mode 600, deleted on exit), never printed.
# Container is CPU-only (optional cgroup parent via CTXLAYER_CGROUP_PARENT) and is removed on exit. Image is not pulled
# if the pinned digest is already present; this script never starts a GPU container.
set -euo pipefail
cd "$(dirname "$0")/.."
TAG="neo4j:2026.10.2-community"
IMAGE="$TAG@sha256:4a2fd4f41ce384aa7d6a74b399f22c202e154f3966119c28a18ed9a500904f5e"
N="${N:-1}"; OUT="${OUT:-evidence/neo4j}"; PORT="${PORT:-57688}"
BATCH="neo4j-$(date -u +%Y%m%dT%H%M%SZ)"; NAME="ctxlayer-neo4j-${BATCH##*-}"
SECRETS=".secrets/neo4j.env"
CGROUP_PARENT="${CTXLAYER_CGROUP_PARENT:-}"

dock() {
  if [ -n "${CTXLAYER_SSH_HOST:-}" ]; then
    # shellcheck disable=SC2086
    ssh $CTXLAYER_SSH_OPTS "$CTXLAYER_SSH_HOST" "docker $(printf "%q " "$@")"
  else
    docker "$@"
  fi
}

load_pct() {
  local cmd='awk -v c=$(nproc) "{printf \"%d\", 100*\$1/c}" /proc/loadavg; echo " $(free | awk "/Mem:/{printf \"%d\", 100*(\$2-\$7)/\$2}")"'
  local o
  if [ -n "${CTXLAYER_SSH_HOST:-}" ]; then
    # shellcheck disable=SC2086
    o=$(ssh $CTXLAYER_SSH_OPTS "$CTXLAYER_SSH_HOST" "$cmd")
  else
    o=$(bash -c "$cmd")
  fi
  set -- $o
  echo $(( $1 > $2 ? $1 : $2 ))
}
guard() {
  local p; p=$(load_pct)
  echo "load check ($1): ${p}%"
  mkdir -p "$OUT"
  echo "$p" >> "$OUT/$BATCH.load"
  if [ "$p" -ge "$2" ]; then echo "load ${p}% >= $2%, stopping"; exit 3; fi
}

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
# Prefer the pinned index digest. If the host still has the tag but has
# dropped RepoDigests (docker then cannot resolve tag@sha256:...), reuse
# the local tag and record its image id. Never pull.
if dock image inspect "$IMAGE" >/dev/null 2>&1; then
  RUN_IMAGE="$IMAGE"
elif dock image inspect "$TAG" >/dev/null 2>&1; then
  RUN_IMAGE="$TAG"
  echo "warning: pinned digest $IMAGE is not resolvable; using local tag $TAG (no pull)"
else
  echo "pinned image is not present; refusing to pull (no unplanned image fetch)"
  exit 4
fi
# Confirm the container will not request a GPU.
( umask 077; printf 'NEO4J_AUTH=neo4j/%s\n' "$(head -c 24 /dev/urandom | base64 | tr -dc A-Za-z0-9)" > "$SECRETS" )
T0=$(date +%s.%N)
{ cat "$SECRETS"; printf 'NEO4J_server_memory_heap_max__size=1g\nNEO4J_server_memory_pagecache_size=256m\n'; } |
  dock run -d --name "$NAME" ${CGROUP_PARENT:+--cgroup-parent=$CGROUP_PARENT} --env-file /dev/stdin \
  --memory 2g --cpus 2 --pids-limit 512 \
  -p "127.0.0.1:$PORT:7687" "$RUN_IMAGE" >/dev/null
T_ID=$(dock inspect "$NAME" --format '{{.HostConfig.CgroupParent}} {{.HostConfig.Memory}} {{json .HostConfig.DeviceRequests}}')
echo "container caps: cgroup=$T_ID (expect ${CGROUP_PARENT} 2147483648 null)"

if [ -n "${CTXLAYER_SSH_HOST:-}" ]; then
  # shellcheck disable=SC2086
  ssh $CTXLAYER_SSH_OPTS -o ExitOnForwardFailure=yes -N -L "127.0.0.1:${PORT}:127.0.0.1:${PORT}" "$CTXLAYER_SSH_HOST" &
  TUN=$!
fi
for i in $(seq 1 120); do dock logs "$NAME" 2>&1 | grep -q 'Started\.' && break; sleep 1; done
T1=$(date +%s.%N)
set -a; . "$SECRETS"; set +a
export CTXLAYER_NEO4J_URI="bolt://127.0.0.1:${PORT}" CTXLAYER_NEO4J_USER=neo4j CTXLAYER_NEO4J_PASSWORD="${NEO4J_AUTH#neo4j/}"
unset NEO4J_AUTH
PY=".venv/bin/python"; [ -x "$PY" ] || { python3 -m venv .venv; .venv/bin/pip install -q -e . matplotlib==3.9.2; }
for i in $(seq 1 30); do
  "$PY" -c 'import os; from neo4j import GraphDatabase as G; G.driver(os.environ["CTXLAYER_NEO4J_URI"], auth=("neo4j", os.environ["CTXLAYER_NEO4J_PASSWORD"])).verify_connectivity()' 2>/dev/null && break
  sleep 1
done
{
  echo "image: $TAG"
  echo "image_id: $(dock image inspect "$RUN_IMAGE" --format '{{.Id}}')"
  echo "digest: $(dock image inspect "$RUN_IMAGE" --format '{{if .RepoDigests}}{{index .RepoDigests 0}}{{else}}(none recorded on host; relate-20261114T122252Z used neo4j@sha256:4a2fd4f41ce384aa7d6a74b399f22c202e154f3966119c28a18ed9a500904f5e){{end}}')"
  echo "arch: $(dock image inspect "$RUN_IMAGE" --format '{{.Architecture}}')"
  echo "run_image: $RUN_IMAGE"
  "$PY" -c 'import os; from neo4j import GraphDatabase as G
d=G.driver(os.environ["CTXLAYER_NEO4J_URI"], auth=("neo4j", os.environ["CTXLAYER_NEO4J_PASSWORD"]))
r=d.execute_query("CALL dbms.components() YIELD name, versions, edition RETURN name, versions[0] AS v, edition").records[0]
print("neo4j:", r[1], r[2]); d.close()'
  echo "driver: neo4j-python $("$PY" -c 'import neo4j; print(neo4j.__version__)')"
  echo "container_start_to_ready_s: $(python3 -c "print(round($T1-$T0,2))")"
  echo "mode: file (store on container disk); CPU-only, cgroup-parent ${CGROUP_PARENT}, memory 2g, cpus 2, heap 1g, pagecache 256m, bind 127.0.0.1 only"
  echo "backend: neo4j (Community server, self-install comparison). This is not the Relate episode."
  echo "batch: $BATCH  runs: $N"
} > "$OUT/$BATCH.meta.txt"
for n in $(seq 1 "$N"); do
  guard "before run $n" 95
  RID="${BATCH}-seed7-$(git rev-parse --short HEAD 2>/dev/null || echo nogit)-r$n"
  "$PY" -m ctxlayer run --backend neo4j --out runs --run-id "$RID"
  echo "run $n done: $RID"
done
"$PY" tools/report.py runs "$OUT/$BATCH" neo4j "$BATCH"
cp runs/${BATCH}-*.jsonl "$OUT/$BATCH/" 2>/dev/null || true
echo "evidence: $OUT/$BATCH (summary.md); raw: runs/${BATCH}-*.jsonl"
