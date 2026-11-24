#!/usr/bin/env bash
# Re-run the analyzer on the committed raw JSONL and diff against the committed summaries.
# Python 3 standard library only. No GPU, no network, no model download.
set -euo pipefail
cd "$(dirname "$0")"
sha256sum -c SHA256SUMS --quiet
out="${OUT_DIR:-$(mktemp -d)}"
python3 analyze_prefix.py vllm   raw/vllm-pairs.jsonl                    > "$out/vllm-summary.json"
python3 analyze_prefix.py sglang raw/sglang-pairs.jsonl                  > "$out/sglang-summary.json"
python3 analyze_prefix.py ollama raw/ollama-pairs.jsonl --require-primer > "$out/ollama-summary.json"
for e in vllm sglang ollama; do
  diff -u "summaries/$e-summary.json" "$out/$e-summary.json"
  echo "$e: analyzer output matches summaries/$e-summary.json"
done
python3 table.py "$out"
