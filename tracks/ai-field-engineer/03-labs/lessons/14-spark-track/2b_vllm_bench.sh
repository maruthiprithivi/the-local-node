#!/usr/bin/env bash
# Lesson 14 · step 2b — vLLM's built-in load generator, run inside the container (on the Spark).
# Random 512-in / 128-out prompts at rising request rates; read "Output token throughput"
# and "P99 TTFT" and compare with your own sweep.py numbers — they should tell the same story.
set -euo pipefail
MODEL=$(curl -s localhost:8000/v1/models | python3 -c "import sys,json;print(json.load(sys.stdin)['data'][0]['id'])")
for rate in 1 4 16 inf; do
  echo "▸ request rate $rate"
  docker exec vllm vllm bench serve --model "$MODEL" --dataset-name random \
    --random-input-len 512 --random-output-len 128 --num-prompts 64 --request-rate $rate 2>&1 \
    | grep -E "Output token throughput|Mean TTFT|P99 TTFT|Mean ITL"
done
