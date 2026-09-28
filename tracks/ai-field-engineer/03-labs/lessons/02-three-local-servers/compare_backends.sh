#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Lesson 02 — one harness, three backends, one table.
# Runs lesson 01's bench_ttft.py against every local server that is up.
# Start the servers first (three terminals):
#     ollama serve
#     bash serve_llamacpp.sh
#     bash serve_mlx.sh
# ─────────────────────────────────────────────────────────────────────────────
set -uo pipefail
cd "$(dirname "$0")"
BENCH=../01-latency-harness/bench_ttft.py

for target in ollama llamacpp mlx; do
  url=$(python -c "from felab import TARGETS; print(TARGETS['$target'].base_url)")
  if curl -sf "$url/models" >/dev/null; then
    python "$BENCH" --target "$target" --runs 5 | sed -n '/^target/,/^$/p'
  else
    echo "  ✗ $target is not running at $url — skipped"
  fi
done

echo
echo "Full history: results/01-latency.csv   (compare the tok_per_s column)"
