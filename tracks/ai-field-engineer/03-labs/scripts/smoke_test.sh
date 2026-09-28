#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Runs every lesson that works offline against the mock server, in course order.
# Use it (a) to check your setup before a study session, (b) in CI.
#     bash scripts/smoke_test.sh
# ~2 minutes. Writes to results/ (git-ignored).
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
cd "$(dirname "$0")/.."
export TARGET=mock

if ! curl -sf localhost:9000/health >/dev/null; then
  python -m felab.mock_server >/tmp/felab-mock.log 2>&1 &
  MOCK=$!; trap 'kill $MOCK 2>/dev/null' EXIT
  for _ in $(seq 20); do curl -sf localhost:9000/health >/dev/null && break; sleep 0.3; done
fi

step() { printf "\n\033[1;36m━━ %s\033[0m\n" "$*"; }
step "data";         python data/make_tickets.py
step "00 check";     python lessons/00-setup/check_env.py
step "01 latency";   python lessons/01-latency-harness/bench_ttft.py --runs 3
                     python lessons/01-latency-harness/bench_ttft.py --runs 3 --prompt-tokens 4000
step "03 sweep";     python lessons/03-concurrency-sweep/sweep.py --levels 1,4,8,16 --slo-ms 500 --min-requests 8
                     python lessons/03-concurrency-sweep/plot_sweep.py
step "04 ceiling";   python lessons/04-quantization/ceiling_check.py --demo
step "04 quality";   python lessons/04-quantization/quality_check.py --label mock
step "05 kv";        python lessons/05-kv-cache/kv_calc.py --ctx 32768 --free-gb 20
step "06 prefix";    python lessons/06-prefix-caching/prefix_bench.py
                     python lessons/06-prefix-caching/prefix_bench.py --order variable-first --usage
step "07 schema";    python lessons/07-structured-output/structured_output.py --n 30
step "08 batch";     python lessons/08-batch-api/make_batch.py && python lessons/08-batch-api/score_batch.py --simulate
step "09 eval";      python lessons/09-eval-harness/evaluate.py mock:mock-8b "mock:mock-8b-lora@0.07/0.30" --n 30 --judge mock
step "11 qlora";     python lessons/11-lora-local-mlx/qlora_memory.py
step "12 moe";       python lessons/12-moe-vs-dense/moe_probe.py --demo
step "13 spec";      python lessons/13-speculative-decoding/spec_math.py && python lessons/13-speculative-decoding/spec_bench.py --label mock
step "16 toy FT";     python lessons/16-training-toy/toy_finetune.py --n-train 200 --steps 1500
step "16 toy align";  python lessons/16-training-toy/toy_alignment.py | tail -12
step "17 data+peft";  python lessons/17-full-vs-peft-mlx/sft_data_check.py && python lessons/17-full-vs-peft-mlx/peft_params.py --model 8b
step "18 pairs+eval"; python lessons/18-preference-dpo/make_pairs.py && python lessons/18-preference-dpo/pref_eval.py --label mock
step "15 memo";      python lessons/15-capstone/build_memo.py >/dev/null && echo "results/SIZING_MEMO.md written"
step "shell syntax"; for f in lessons/*/*.sh scripts/*.sh; do bash -n "$f"; done && echo "all .sh parse"
printf "\n\033[1;32m✓ smoke test passed\033[0m\n"
