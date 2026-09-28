#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Lesson 05 · step 2 — climb the context ladder and read the KV size from the log.
#
# For each (context, cache type) we start llama-server, wait for it to load,
# grep the line where llama.cpp reports how much KV cache it allocated, then stop it.
# Compare every number with kv_calc.py — they should match within a few %.
#
#   f16  : the default. 131k context on an 8B model ≈ 17 GB of cache alone.
#   q8_0 : --cache-type-k q8_0 --cache-type-v q8_0 → roughly half.
#
# If the server refuses a quantized V cache, your build needs flash attention on:
#   add  -fa on   (newer builds)   or   -fa   (older builds)  to EXTRA below.
# On a 16–24 GB Mac the 131072/f16 rung may fail to load. That IS the lesson.
# ─────────────────────────────────────────────────────────────────────────────
set -uo pipefail
cd "$(dirname "$0")"
REPO=${LLAMACPP_REPO:-bartowski/Meta-Llama-3.1-8B-Instruct-GGUF}:Q4_K_M
EXTRA=${EXTRA:-}
PORT=8090
mkdir -p logs

printf "%-8s %-6s %s\n" ctx cache "what llama.cpp allocated"
for ctx in 4096 32768 131072; do
  for kv in f16 q8_0; do
    log="logs/ctx${ctx}_${kv}.log"
    llama-server -hf "$REPO" -c "$ctx" -ngl 99 --parallel 1 --port $PORT \
      --cache-type-k "$kv" --cache-type-v "$kv" $EXTRA >"$log" 2>&1 &
    pid=$!
    # wait until the server says it is listening, or dies (e.g. out of memory)
    for _ in $(seq 1 120); do
      grep -q "listening" "$log" && break
      kill -0 $pid 2>/dev/null || break
      sleep 1
    done
    size=$(grep -iE "kv.*(size|buffer).*MiB" "$log" | tail -1 | sed 's/^.*: *//')
    [[ -z "$size" ]] && size="✗ failed to start — see $log"
    printf "%-8s %-6s %s\n" "$ctx" "$kv" "$size"
    kill $pid 2>/dev/null; wait $pid 2>/dev/null
  done
done

echo
echo "Check:  python kv_calc.py --ctx 131072            (f16)"
echo "        python kv_calc.py --ctx 131072 --kv q8_0  (q8)"
