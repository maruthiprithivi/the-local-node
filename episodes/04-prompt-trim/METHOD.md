# Method: Qwen Code system-prompt trimming

## Model and serving

- Qwen3.8-27B NVFP4 with DSpark k=7 speculative decoding (probabilistic draft sampling), served by vLLM on one NVIDIA GB10 workstation (121.6 GiB unified memory, 20 cores).
- vLLM settings: max-model-len 131072, gpu-memory-utilization 0.50, max-num-seqs 8, max-num-batched-tokens 4096, prefix caching on, `--enable-prompt-tokens-details` so the usage object reports cached prompt tokens.
- Sampling: temperature 0.6, top_p 0.95, top_k 20, declared in the Qwen Code settings. A logging proxy checked that every request actually carried these values.

## Harness and prompt levels

- Qwen Code 0.26.1, headless: `qwen --approval-mode yolo --auth-type openai --model <id> "<task prompt>"`, with `QWEN_STREAM_MAX_LIFETIME_MS=0`. `settings.json` comes from `config/qwen-settings.json.tmpl`, with managed auto-memory and auto-dream off.
- p100 is the stock command, with no `--system-prompt` flag. Qwen Code uses its built-in main-session prompt, which is identical to `prompts/t4-p100.md`.
- p60, p30 and pmin pass the file text with `--system-prompt <text>`, which replaces the built-in main-session prompt (`scripts/qwen_trim_adapter.py`).
- The levels were cut by removing whole sections and bullets of the built-in prompt. Nothing was reworded. RESULTS.md lists exactly what each level removes.
- Qwen Code appends ~950-976 characters (environment and context) after the prompt at every level. The sent system-message sizes in RESULTS.md include that text.
- The 10 tool schemas are sent unchanged at every level. They make up ~8.1K of the first request's ~8.3-12.3K prompt tokens.

## Tasks and runs

- Tasks: 5 of our 10 everyday coding tasks: 01-bugfix-pagination, 03-refactor-reports, 05-stacktrace-ingest, 08-pr-review and 09-multifile-api. Each is a small repo with a task prompt and hidden tests. 08 is a PR review scored on planted bugs (pass = at least 3 of 4 found).
- 2 seeds (0, 1) x 4 levels x 5 tasks = 40 runs at concurrency 8. Levels were interleaved so that each saw similar load (`config/matrix.yaml`).
- Each run had a budget of 40,000 completion tokens and a wall cap of 2400 s. Scoring is strict: a run that hits the budget or the wall cap is a fail even if its tests pass.
- Isolation: OpenShell 0.1.6, one fresh sandbox per run, with no network except a forwarder to the model port. Hidden tests run afterwards in a separate network-less sandbox. Everything runs under a memory-capped cgroup.

## Measurements and scripts

The scripts expect this layout:

```
<OUT>/artifacts/<run-name containing __<level>__>/run.json
<OUT>/artifacts/<run-name>/attempt-<n>/log/requests.jsonl
```

- `run.json` fields used: `harness`, `item`, `seed`, `status`, `strict_pass`, `lenient_pass`, `wall_s`, `attempts`, `completion_tokens`, `budget_hit` and `timed_out`.
- Fields used from each `requests.jsonl` line: `status` (HTTP), `ttft_s` (time to first streamed token, measured by the proxy), `request.messages` (the system message is used to count characters sent), and `response.usage` (`prompt_tokens`, plus `prompt_tokens_details.cached_tokens`).
- `scripts/analyze_runs.py OUT results.json` gives the per-level table in RESULTS.md. Each figure is the median [min-max] of 10 per-run values: first-request prompt tokens, the per-run mean of prompt tokens per request, requests per run, the per-run median TTFT, wall time and completion tokens. The script is verbatim from the run, apart from its docstring. Run on the original data, it reproduces `results/per-run-and-level.json` byte for byte.
- `scripts/pooled.py OUT` gives the pooled per-request figures in RESULTS.md: the request count, median prompt tokens per request, TTFT median and p95 (`statistics.quantiles`, default method), median uncached tokens (prompt - cached) and the cached share of all prompt tokens. It was written while packing this kit and checked against the original request logs: every published pooled figure matches (`results/pooled-requests.json`).
- Host memory was sampled every 5 s. It peaked at 73.81 GiB (60.7 %).

## Not included

The everyday task suite and the benchmark harness (sandbox runner, logging proxy and scorer) are not public yet. The run's raw request logs contain full prompts, model outputs, file contents and sandbox paths, so they are not published. Only the aggregates above are.
