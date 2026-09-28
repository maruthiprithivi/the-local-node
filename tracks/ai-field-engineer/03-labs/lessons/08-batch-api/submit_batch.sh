#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Lesson 08 · step 2 — submit to the Fireworks Batch API (50% off serverless prices).
#
# Batch = "I don't need the answer in 300 ms; I need 100k answers by tomorrow".
# The provider fills idle GPU time with your work, so it is cheaper.
# Evals, back-fills, synthetic data, nightly classification → batch.
#
# 100 short tickets on a small model costs well under a cent even at full price.
# Flags per the docs at time of writing; `firectl batch-inference-job create --help` wins.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
cd "$(dirname "$0")"
MODEL=${1:-accounts/fireworks/models/gpt-oss-20b}
STAMP=$(date +%m%d-%H%M)
IN="triage-batch-in-$STAMP"
JOB="triage-batch-$STAMP"

[[ -f batch_input.jsonl ]] || python make_batch.py

echo "▸ upload input dataset: $IN"
firectl dataset create "$IN" ./batch_input.jsonl

echo "▸ create job: $JOB  (model $MODEL)"
firectl batch-inference-job create --job-id "$JOB" --model "$MODEL" --input-dataset-id "$IN"

echo "▸ poll every 30 s (Ctrl-C is safe — the job keeps running; re-check with the get command)"
while true; do
  state=$(firectl batch-inference-job get "$JOB" | grep -iE "^\s*state" | head -1 || true)
  echo "  $(date +%H:%M:%S)  $state"
  [[ "$state" =~ COMPLETED|FAILED|EXPIRED ]] && break
  sleep 30
done

firectl batch-inference-job get "$JOB"
cat <<EOF

▸ Next: find the output dataset id in the output above, then
    firectl dataset download <OUTPUT_DATASET_ID>
    python score_batch.py <downloaded results .jsonl>
EOF
