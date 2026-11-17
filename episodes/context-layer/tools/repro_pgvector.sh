#!/usr/bin/env bash
# One command repro of the pgvector baseline: ./tools/repro_pgvector.sh
#   REMOTE=<ssh alias>  run the database container on that host (loopback only, reached through an ssh tunnel);
#                       empty means local docker. N=<runs> (default 5). OUT=<folder> (default evidence/pgvector).
# Pinned image, random throwaway password (never printed), nothing installed on the host, torn down on exit.
# Load guard (remote): refuses to start at >= 85% cpu or memory, aborts at >= 95%.
set -euo pipefail
cd "$(dirname "$0")/.."
IMAGE="pgvector/pgvector:0.8.0-pg17"
N="${N:-5}"; REMOTE="${REMOTE:-}"; OUT="${OUT:-evidence/pgvector}"; PORT="${PORT:-55432}"
BATCH="pgvector-$(date -u +%Y%m%dT%H%M%SZ)"; NAME="ctxlayer-pgv-${BATCH##*-}"
dock() { if [ -n "$REMOTE" ]; then ssh -o BatchMode=yes "$REMOTE" "docker $(printf "%q " "$@")"; else docker "$@"; fi; }
load_pct() {  # max(cpu load1/cores, memory used) as an integer percent
  local cmd='awk -v c=$(nproc) "{printf \"%d\", 100*\$1/c}" /proc/loadavg; echo " $(free | awk "/Mem:/{printf \"%d\", 100*(\$2-\$7)/\$2}")"'
  local o; if [ -n "$REMOTE" ]; then o=$(ssh -o BatchMode=yes "$REMOTE" "$cmd"); else o=$(bash -c "$cmd"); fi
  set -- $o; echo $(( $1 > $2 ? $1 : $2 ))
}
guard() { local p; p=$(load_pct); echo "load check ($1): ${p}%"; echo "$p" >> "$OUT/$BATCH.load"; if [ "$p" -ge "$2" ]; then echo "load ${p}% >= $2%, stopping"; exit 3; fi; }
mkdir -p "$OUT" runs
TUN=""; PULLED=0
cleanup() {
  set +e
  [ -n "$TUN" ] && kill "$TUN" 2>/dev/null
  dock rm -f "$NAME" >/dev/null 2>&1
  [ "$PULLED" = 1 ] && dock rmi "$IMAGE" >/dev/null 2>&1
  echo "torn down: container removed$([ "$PULLED" = 1 ] && echo ', image we pulled removed')"
}
trap cleanup EXIT
guard "before start" 85
dock image inspect "$IMAGE" >/dev/null 2>&1 || { PULLED=1; dock pull -q "$IMAGE" >/dev/null; }
PW=$(head -c 24 /dev/urandom | base64 | tr -dc A-Za-z0-9)
printf 'POSTGRES_PASSWORD=%s\nPOSTGRES_DB=ctxlayer\n' "$PW" | dock run -d --name "$NAME" --env-file /dev/stdin \
  --memory 2g --cpus 2 --pids-limit 256 -p "127.0.0.1:$PORT:5432" "$IMAGE" >/dev/null
if [ -n "$REMOTE" ]; then
  ssh -o BatchMode=yes -o ExitOnForwardFailure=yes -N -L "127.0.0.1:$PORT:127.0.0.1:$PORT" "$REMOTE" & TUN=$!
fi
for i in $(seq 1 60); do dock exec "$NAME" pg_isready -U postgres -d ctxlayer -q 2>/dev/null && break; sleep 1; done
sleep 2
export CTXLAYER_PG_DSN="postgresql://postgres:${PW}@127.0.0.1:${PORT}/ctxlayer"
PY=".venv/bin/python"; [ -x "$PY" ] || { python3 -m venv .venv; .venv/bin/pip install -q -e . matplotlib==3.9.2; }
{ echo "image: $IMAGE"; echo "digest: $(dock image inspect "$IMAGE" --format '{{index .RepoDigests 0}}')"
  echo "arch: $(dock image inspect "$IMAGE" --format '{{.Architecture}}')"
  echo "postgres: $(dock exec "$NAME" psql -U postgres -d ctxlayer -Atc 'show server_version')"
  echo "memory_cap: 2g  cpus: 2  bind: 127.0.0.1 only"; echo "batch: $BATCH  runs: $N"; } > "$OUT/$BATCH.meta.txt"
for n in $(seq 1 "$N"); do
  guard "before run $n" 95
  RID="${BATCH}-seed7-$(git rev-parse --short HEAD 2>/dev/null || echo nogit)-r$n"
  "$PY" -m ctxlayer run --backend pgvector --out runs --run-id "$RID" >/dev/null
  echo "run $n done: $RID"
done
dock exec "$NAME" psql -U postgres -d ctxlayer -Atc "select extversion from pg_extension where extname='vector'" | sed 's/^/pgvector extension: /' >> "$OUT/$BATCH.meta.txt"
"$PY" tools/report.py runs "$OUT/$BATCH" pgvector "$BATCH" >/dev/null
cp runs/${BATCH}-*.jsonl "$OUT/$BATCH/" 2>/dev/null || true
echo "evidence: $OUT/$BATCH (summary.md, CSVs, charts); raw: runs/${BATCH}-*.jsonl"
