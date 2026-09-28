#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Lesson 14 · step 2 — the SAME harnesses from lessons 01/03/06, pointed at the Spark.
# Run this ON YOUR MAC (it talks to the Spark over the network).
# Then, for comparison, vLLM's own benchmark from inside the container (remote.sh 2b_vllm_bench.sh).
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
cd "$(dirname "$0")"
L=..
python $L/01-latency-harness/bench_ttft.py --target spark --runs 5
python $L/03-concurrency-sweep/sweep.py     --target spark --levels 1,2,4,8,16,32,64 --slo-ms 1000
python $L/03-concurrency-sweep/plot_sweep.py                  # Mac and Spark curves on one chart
python $L/06-prefix-caching/prefix_bench.py --target spark
