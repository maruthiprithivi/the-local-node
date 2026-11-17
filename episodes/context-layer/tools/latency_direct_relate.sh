#!/usr/bin/env bash
# Quotable latency for relate (Neo4j): the harness client runs ON the Docker host, no ssh tunnel in the path.
#   ./tools/latency_direct_relate.sh   REMOTE=<ssh alias> (empty means local docker)  N=<runs> (default 5)  OUT=<folder> (default evidence/relate/latency-direct)
# The committed harness (git archive HEAD) is copied to a scratch dir on the host and run in a pinned python
# container with --network host, so Bolt goes to 127.0.0.1 on the same machine. Same pinned Neo4j image, caps and
# file mode as repro_relate.sh, seed 7, full workload. Only raw JSONL comes back; CSVs and charts are made here with
# tools/report.py. Throwaway password (gitignored .secrets/, mode 600, deleted on exit), never printed; the scratch dir,
# containers and anything we pulled are removed on exit. Load guard: refuse at >= 85%, abort at >= 95%.
set -euo pipefail
cd "$(dirname "$0")/.."
TAG="neo4j:2026.10.2-community"
IMAGE="$TAG@sha256:4a2fd4f41ce384aa7d6a74b399f22c202e154f3966119c28a18ed9a500904f5e"   # index digest, pinned 2026-11-14
PYIMG="python:3.13-slim@sha256:09a17cad02668ae61ece136b4fd36ac3849e14f670ebedb637ea3e15580525bc"   # pinned 2026-11-14
N="${N:-5}"; REMOTE="${REMOTE:-}"; OUT="${OUT:-evidence/relate/latency-direct}"; PORT="${PORT:-57689}"
BATCH="relate-direct-$(date -u +%Y%m%dT%H%M%SZ)"; NAME="ctxlayer-${BATCH}"; SHA=$(git rev-parse --short HEAD)
SECRETS=".secrets/relate-direct.env"; SCR="scratch/ctxlayer-${BATCH}"
r() { ssh -o BatchMode=yes "$REMOTE" "$@"; }
RHOME=$(ssh -n -o BatchMode=yes "$REMOTE" 'echo $HOME'); RUID=$(ssh -n -o BatchMode=yes "$REMOTE" 'echo $(id -u):$(id -g)')
dock() { r "docker $(printf "%q " "$@")"; }
load_pct() {
  local o; o=$(r 'awk -v c=$(nproc) "{printf \"%d\", 100*\$1/c}" /proc/loadavg; echo " $(free | awk "/Mem:/{printf \"%d\", 100*(\$2-\$7)/\$2}")"')
  set -- $o; echo $(( $1 > $2 ? $1 : $2 ))
}
D="$OUT/$BATCH"; mkdir -p "$D" .secrets; chmod 700 .secrets
guard() { local p; p=$(load_pct); echo "load check ($1): ${p}%"; echo "$1 ${p}" >> "$D/load.txt"; if [ "$p" -ge "$2" ]; then echo "load ${p}% >= $2%, stopping"; exit 3; fi; }
PULLED=""
cleanup() {
  set +e; dock rm -f "$NAME" "$NAME-client" >/dev/null 2>&1; r "rm -rf ~/$SCR"
  for i in $PULLED; do dock rmi "$i" >/dev/null 2>&1; done
  rm -f "$SECRETS"; echo "torn down: containers and scratch dir removed, password file deleted${PULLED:+, pulled images removed}"
}
trap cleanup EXIT
guard "before start" 85
for i in "$IMAGE" "$PYIMG"; do dock image inspect "$i" >/dev/null 2>&1 || { PULLED="$PULLED $i"; dock pull -q "$i" >/dev/null; }; done
PW="$(head -c 24 /dev/urandom | base64 | tr -dc A-Za-z0-9)"
( umask 077; printf 'NEO4J_AUTH=neo4j/%s\nCTXLAYER_NEO4J_URI=bolt://127.0.0.1:%s\nCTXLAYER_NEO4J_USER=neo4j\nCTXLAYER_NEO4J_PASSWORD=%s\n' "$PW" "$PORT" "$PW" > "$SECRETS" ); unset PW
r "mkdir -p ~/$SCR"; git archive HEAD | r "tar -x -C ~/$SCR"
{ grep NEO4J_AUTH "$SECRETS"; printf 'NEO4J_server_memory_heap_max__size=1g\nNEO4J_server_memory_pagecache_size=256m\n'; } |
  dock run -d --name "$NAME" --env-file /dev/stdin --memory 2g --cpus 2 --pids-limit 512 -p "127.0.0.1:$PORT:7687" "$IMAGE" >/dev/null
for i in $(seq 1 120); do dock logs "$NAME" 2>&1 | grep -q 'Started\.' && break; sleep 1; done
RUNS=""; for n in $(seq 1 "$N"); do RUNS="$RUNS ${BATCH}-seed7-${SHA}-r$n"; done
# client (runs as the host user, so the scratch dir stays removable): venv with the pinned deps, wait for Bolt, then N full runs with a load check before each (inside the host)
CLIENT='set -e; python -m venv /tmp/v; export PATH=/tmp/v/bin:$PATH; pip install -q --disable-pip-version-check -r requirements.txt >/dev/null && pip install -q --disable-pip-version-check --no-deps -e . >/dev/null
python -c "import neo4j,sys; print(\"driver: neo4j-python\", neo4j.__version__); print(\"python:\", sys.version.split()[0])"
for i in $(seq 1 60); do python -c "import os; from neo4j import GraphDatabase as G; G.driver(os.environ[\"CTXLAYER_NEO4J_URI\"], auth=(\"neo4j\", os.environ[\"CTXLAYER_NEO4J_PASSWORD\"])).verify_connectivity()" 2>/dev/null && break; sleep 1; done
for rid in '"$RUNS"'; do
  l=$(awk -v c=$(nproc) "{printf \"%d\", 100*\$1/c}" /proc/loadavg); echo "load before $rid: cpu ${l}%"; [ "$l" -lt 95 ] || exit 3
  python -m ctxlayer run --backend relate --out runs --run-id "$rid" >/dev/null; echo "done $rid"; done'
grep CTXLAYER "$SECRETS" | dock run --rm --name "$NAME-client" --network host --env-file /dev/stdin --memory 1g --cpus 2 \
  --user "$RUID" -e HOME=/tmp -e PYTHONDONTWRITEBYTECODE=1 -v "$RHOME/$SCR:/h" -w /h "$PYIMG" sh -c "$CLIENT" | tee "$D/client.log"
guard "after runs" 95
r "cd ~/$SCR/runs && tar -c ${BATCH}-*.jsonl" | tar -x -C "$D"   # only this batch (git archive also carries older committed runs)
{ echo "image: $TAG"; echo "digest: $(dock image inspect "$IMAGE" --format '{{index .RepoDigests 0}}')"
  echo "arch: $(dock image inspect "$IMAGE" --format '{{.Architecture}}')"; echo "client image: $PYIMG"
  grep -E '^(driver|python):' "$D/client.log"; echo "commit: $SHA (git archive HEAD copied to the host)"
  echo "path: client container --network host on the Docker host -> 127.0.0.1:$PORT (docker-proxy) -> neo4j container; no ssh tunnel"
  echo "mode: file (container disk); caps: neo4j --memory 2g --cpus 2 heap 1g pagecache 256m; client --memory 1g --cpus 2"
  echo "batch: $BATCH runs: $N seed: 7"; } > "$D/meta.txt"
.venv/bin/python tools/report.py "$D" "$D" relate "$BATCH" >/dev/null
echo "evidence: $D"
