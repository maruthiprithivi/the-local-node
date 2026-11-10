# Qwen Code system-prompt trimming

Follow-along kit in [The Local Node](https://github.com/maruthiprithivi/the-local-node).

Does a coding agent need its full ~19K-character system prompt? We ran [Qwen Code](https://github.com/QwenLM/qwen-code) 0.26.1 on a local Qwen3.8-27B (NVFP4, vLLM, prefix caching on) at four prompt levels: full, ~60 %, ~24 % and a 235-character minimal prompt. The runs used 5 everyday coding tasks x 2 seeds (40 runs) on one NVIDIA GB10 workstation (Nov 3 2026).

**Headline:**

- Pass rates were 10/10, 10/10 and 10/10 down to ~24 %, and 9/10 at the minimal prompt. The one miss, a PR review, is within seed noise.
- Trimming to minimal saves ~3,865 prompt tokens on every request (-32 % on the first request).
- Time to first token barely moves (median 1.49-1.64 s per request at every level), because prefix caching already serves the fixed prompt and tools from cache.

Full tables are in [RESULTS.md](RESULTS.md).

## What is in here

| Path | What it is |
|---|---|
| `RESULTS.md` | The public write-up with every measured number |
| `METHOD.md` | Setup, how the prompt levels were cut, scoring, and how to reproduce |
| `prompts/t4-p100.md` | Qwen Code 0.26.1's built-in main-session prompt, used as the reference for the cuts. The p100 runs used the stock harness with no flag. |
| `prompts/t4-p60.md`, `t4-p30.md`, `t4-pmin.md` | The trimmed prompts passed with `--system-prompt` |
| `config/qwen-settings.json.tmpl` | The Qwen Code `settings.json` template (local OpenAI-compatible endpoint, sampling 0.6 / 0.95 / 20, telemetry off) |
| `config/matrix.yaml` | The run matrix: levels, tasks, seeds, concurrency, model arm |
| `scripts/qwen_trim_adapter.py` | How the prompt file was passed to Qwen Code (excerpt of the adapter used) |
| `scripts/analyze_runs.py` | Per-run and per-level table (pass rates, prompt tokens, TTFT, wall, completion tokens) |
| `scripts/pooled.py` | Pooled per-request stats (median prompt tokens, TTFT median and p95, uncached tokens, cached share) |
| `results/per-run-and-level.json` | Output of `analyze_runs.py` on the original run (40 runs) |
| `results/pooled-requests.json` | Output of `pooled.py` on the original run |
| `LEAKCHECK.md` | What was scanned before publishing and what was left out |
| `MANIFEST.sha256` | Checksums of every file in this folder |

## Reproduce the prompt levels

Run Qwen Code headless against your own OpenAI-compatible server, once per level:

```bash
# ~/.qwen/settings.json from config/qwen-settings.json.tmpl, with __MODEL_ID__ replaced and baseUrl pointing at your server
export QWEN_STREAM_MAX_LIFETIME_MS=0
qwen --approval-mode yolo --auth-type openai --model <model-id> "<task prompt>"                                     # p100 (stock)
qwen --approval-mode yolo --auth-type openai --model <model-id> --system-prompt "$(cat prompts/t4-p60.md)" "<task prompt>"   # p60
```

Use a fresh sandbox and a fresh copy of the task repo per run, with network limited to the model server. `--approval-mode yolo` lets the agent run tools without asking, so do not run it on your own machine outside a sandbox. Score each run with tests the agent never sees.

To get the same statistics, put a logging proxy between Qwen Code and the server. It should write one JSON line per request with `status`, `ttft_s` and the server's `response.usage` (including `prompt_tokens_details.cached_tokens`). Then run `scripts/analyze_runs.py` and `scripts/pooled.py` (see METHOD.md for the expected layout).

## What this kit does not include

The 10-task everyday coding suite (task repos and hidden tests) and the benchmark harness that ran the sandboxes and proxy are not published yet. So the prompt files, settings and scripts are here, but the exact pass/fail numbers need your own tasks or those suites. Bring your own small coding tasks with hidden tests, and compare levels on the same tasks and seeds.

## What this test cannot show

The test used 5 easy-to-medium tasks and 2 seeds, which cannot separate the levels statistically on pass rate. It does not cover harder or longer work, other harnesses, or deployments without a warm prompt cache, where a shorter prompt would cut real prefill. It also does not test safety behaviour: the removed "Security and Safety" and "Executing actions with care" sections are not exercised by these tasks.

## License

This folder is part of The Local Node repository. `prompts/t4-p100.md` is Qwen Code 0.26.1's built-in prompt, and the other three prompts are cut from it. Qwen Code is Apache-2.0 licensed by its authors.
