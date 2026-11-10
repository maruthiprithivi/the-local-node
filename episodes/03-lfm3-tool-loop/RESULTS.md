# Results: LiquidAI LFM3-1.7B (official GGUF) on llama.cpp b11981: decode speed, footprint, quick coding check

Status: DONE, reduced version (honest subset, see "Run counts"). Run Nov 3 2026 on one GB10 workstation; coding check suite wall 15 min, exit 0.
Published here: llama-bench JSON and the decode client output (`results/decode/`), tool-loop summaries (`results/tool-loop/`) and the scripts (`scripts/`). Server logs, per-turn logs, request logs and memory samples are not published (see LEAKCHECK.md).

## Setup
- Model: LiquidAI/LFM3-1.7B, official GGUF repo LiquidAI/LFM3-1.7B-GGUF at repo sha ee9698375b4034c0d044b8686d84e8ddb5f3ee92 (the Q8_0 file is identical at the later repo sha 2f8ca1ec). sha256 checked against the Hugging Face LFS metadata:
  - LFM3-1.7B-Q4_K_M.gguf 1,099,627,808 B, sha256 3793e1e6e2266919d6e015287221b41100175a98eddaba92e111aed3b05c93c4
  - LFM3-1.7B-Q8_0.gguf 1,846,238,496 B, sha256 8f6b24182258205e9e01e21f1f24a1f208c1e8115578825d202ce39976af20b6
  - LFM3-1.7B-BF16.gguf 3,466,626,336 B, sha256 39158a79f56edb85e0c4252ce6447b8d7883ef82ffedd02f0cda7c84da5e9f68
  - llama.cpp reports: arch lfm3, 1,728,801,600 params, trained context 262,144, vocab 128,000.
- Runtime: llama.cpp release b11981 (commit da6c30ade), official prebuilt CUDA 13.4 arm64 binaries + matching CUDA runtime, mounted read-only into a small runtime container; CUDA backend, all layers on GPU, flash attention auto, 20 threads.
- Sandbox (every llama.cpp container): memory-capped cgroup, 24 GiB memory with no swap, pids limit 2048, all capabilities dropped, no-new-privileges, read-only root filesystem, non-root user, model and binaries mounted read-only.
  - Part A: no network at all.
  - Parts B/C: llama-server on an internal-only container network with no outside route; the benchmark client in its own container on that network; for part C a small relay container exposes it on loopback only, for the benchmark proxy.
  - Part C agent: Pi 1.3.0 in OpenShell 0.1.6 sandboxes, one fresh sandbox per run, network deny-all except the forwarder binary to the model port, hidden tests scored in a separate network-less sandbox, canary planted (no breach in any run).
- Part A: llama-bench -p 512 -n 128 -r 5 per quant (Q4_K_M, Q8_0, BF16).
- Part B: llama-server Q8_0, 1 slot, 32K ctx, --jinja; our streaming client: 1 warm-up (discarded), then 5 rounds of (short chat, 32 tokens + 512-token decode), concurrency 1.
- Part C: llama-server Q8_0, 4 slots x 64K ctx, --jinja; our 10-task everyday coding suite, Pi harness (plain; the LFM3 model card names Pi as a target harness), concurrency 4, seed 0, wall cap 900 s/run, 40K completion-token budget, strict scoring.

## Run counts
REDUCED: part B only Q8_0 (the original plan did all 3 quants); part C 5 of the 10 everyday tasks (01, 03, 05, 08, 09, the same 5 as tests 4 and 6) x 1 seed = 5 runs. All 5 completed, attempts 1 each.

## Results

### Part A: llama-bench (5 reps each; median [min-max] tok/s; llama-bench mean in brackets)
| Quant | File size | tg128 decode | pp512 prefill |
|---|---|---|---|
| Q4_K_M | 1.09 GB | **179.8** [175.2-182.0] (mean 179.2) | 14,967 [14,211-15,309] (mean 14,845) |
| Q8_0 | 1.84 GB | **122.9** [121.0-123.4] (mean 122.6) | 14,658 [14,039-15,050] (mean 14,619) |
| BF16 | 3.46 GB | **70.6** [60.3-70.8] (mean 68.0) | 10,461 [10,187-11,096] (mean 10,611) |

(BF16's 60.3 is the first rep; the other four were 67.6-70.8.)

### Part B: llama-server concurrency 1, Q8_0 (n5)
- Decode, 512 tokens: median **110.08 tok/s** [108.70-111.78], n5.
- Short chat (32 tokens): TTFT median 0.0287 s [0.0280-0.0376]; decode 105.9-109.9 tok/s. 512-token requests: TTFT 0.026-0.028 s, total 4.60-4.73 s.
- Server decode is ~10 % below llama-bench tg128 for the same quant (110.1 vs 122.9).

### Memory (GB used)
- Part B (Q8_0, 1 slot, 32K ctx): host memory used +2.99 GiB after load + requests (70.30 -> 73.29 GiB); container 748.9 MiB. GPU MiB not recorded in B.
- Part C (Q8_0, 4 slots x 64K): **GPU 5,174 MiB** for llama-server after load. Host +5.76 GiB at server up (70.19 -> 75.95 GiB); container peak 2.20 GiB by the end.
- Host during part C (5 s samples): 75.95-80.05 GiB, peak **80.05 GiB** (includes the agent sandboxes and an idle 27B vLLM server that stayed loaded). Never near the 85 % guard.

### Part C: coding check (Pi, concurrency 4, Q8_0): **3/5 tasks passed**
| Task | Result | Wall, s | Completion tokens | Requests | Hidden tests |
|---|---|---|---|---|---|
| 05-stacktrace-ingest | pass | 61.1 | 4,213 | 15 | 5 passed |
| 03-refactor-reports | pass | 112.4 | 7,837 | 10 | 28 passed |
| 08-pr-review | pass | 132.9 | 8,814 | 7 | found 4/4 planted bugs, 1 false positive |
| 09-multifile-api | fail | 234.1 | 12,020 | 8 | 2 failed, 2 passed |
| 01-bugfix-pagination | timeout-fail (900 s wall cap) | 900.3 | 28,992 | 17 | 7 failed, 3 passed |

No budget hits; largest slot context seen ~33K tokens (no truncation). For reference only (different harness): the local 27B with Qwen Code passed these 5 tasks in test 6 (no review, 5/5) and test 4 (full prompt, 10/10 over 2 seeds).

## Environment
- One NVIDIA GB10 workstation (compute 12.1), aarch64, 20 cores, 121.6 GiB unified memory. Docker; OpenShell 0.1.6; a memory guard (stop new work at 85 %, kill at 95 % host memory) and earlyoom.
- The default 27B server (Qwen3.8-27B NVFP4 + DSpark k=7 on vLLM) stayed up and idle the whole time (59,154 MiB GPU), unchanged.
- That vLLM build (0.1.dev21830, built 2026-10-15) has no Lfm3 architecture: its model registry lists only Lfm2 variants (Lfm2ForCausalLM, Lfm2MoeForCausalLM, Lfm2VlForConditionalGeneration, ColBERTLfm2Model). So LFM3 ran only on llama.cpp here (the GGUF card asks for llama.cpp >= b11960).

## What broke
- Launch attempt 1: the job was started with a relative script path, "No such file or directory", nothing ran. Relaunched with an absolute path (parts A+B fine).
- Coding check attempt 1: the benchmark failed at once, the OpenShell CLI was not on PATH in that job's environment. Fixed by going through the suite wrapper that sets PATH.
- Coding check attempt 2: refused by the memory-guard preflight because the job was not inside the memory-capped benchmark cgroup. No runs. The wrapper still reported exit 0 for the refused attempt, so its exit code alone can't be trusted. Relaunched inside the cgroup; all 5 ran.
- A duplicate prep (second source build + re-download) was started before an earlier finished prep was found; it was stopped and removed. Its Q8_0 download had the same sha256.
- In the run itself: 01-bugfix-pagination hit the 900 s wall cap; 09 ended with a wrong store/service contract.
- Cleanup checked afterwards: no test containers, network, llama-server process or sandboxes left.

## What it won't catch
One seed, 5 easy-to-medium tasks and one harness (Pi) at concurrency 4 with a 900 s cap: it says nothing about LFM3 on harder or longer agent work, other harnesses or quants in the coding check (only Q8_0 was served), decode under concurrency, or vLLM/SGLang serving of LFM3.

## Tool-loop check (added Nov 4 2026)
Question: how many chained tool calls does LFM3-1.7B make correctly, with long tool results fed back, before it breaks?
Run Nov 4 2026 on the same GB10 workstation, about 18 minutes in total. Driver and run scripts are in `scripts/`; per-seed summaries are in `results/tool-loop/`. Per-turn logs are not published; every run is reproducible from its seed.

### Setup
- Same model file and runtime as parts B/C: LFM3-1.7B-Q8_0.gguf (sha256 8f6b2418...af20b6), llama.cpp b11981 llama-server, 1 slot, all layers on GPU, --jinja (native tool calling through the model's chat template). Same hardened container as part B, inside the memory-capped benchmark cgroup. The server sits on an internal-only container network; the test driver runs in its own container on that network, so it can reach only the model port (no keys, no outside network).
- Driver: a small stdlib Python script against the OpenAI-compatible /v1/chat/completions endpoint, tool_choice auto, non-streaming. 4 tools: read_file(path), search(query), next_step(token), get_record(record_id: integer). The user prompt names call 1. Every tool result is ~3.0K tokens of synthetic log-line filler (prompt grows a median 2,999 tokens per step, range 2,976-3,274) plus a header line `=== result of <tool> (record N) ===` and a last line `NEXT ACTION: call the tool `X` with arguments {...}`. The chain (tool order, never the same tool twice in a row; arguments: paths, queries, 8-character tokens, 5-digit ids) is generated from the seed, so every step can be checked. Cap 50 calls.
- Strict scoring: the first deviation ends the count. Classes: wrong tool, wrong/missing argument, invalid JSON, repeat of an earlier call (3x = loop), no call (stops / answers early), max_tokens reached with no call, server error / context overflow. After a deviation the driver answers "Error: invalid call." for up to 2 more turns, only to see what the model does next.
- Sampling as in part C: temperature 0.6, top_p 0.95, top_k 20, seed = run seed, max_tokens 2048 per turn (plus an 8192 check).
- Contexts 32K, 64K, 128K and 256K (the trained context) with seeds 0-2; then seeds 0 and 3-9 at 256K; then seeds 0 and 1 at 256K with max_tokens 8192. At ~3K tokens per step the 50-call cap fits in 256K, so at 256K the break is the model's, not the window's.
- A smoke run with ~4.4K-token results (32K, seed 0) was not counted; the filler was cut to ~3K after it.
- Reproducible: the same seed gave identical behaviour on every server (seed 0 broke at the same turn the same way in all 5 runs with max_tokens 2048). So the 4 contexts are not extra samples; the independent samples are the 10 seeds.

### Results: 10 seeds at 256K context, max_tokens 2048
| Seed | Calls completed | Break | Tokens at break (prompt+completion) | Wall, s |
|---|---|---|---|---|
| 0 | 6 | max_tokens, no call (2,048 tokens of reasoning, empty answer) | 20,443 | 25.8 |
| 1 | 12 | max_tokens, no call | 38,374 | 31.8 |
| 2 | 25 | wrong tool: get_record {"record_id":25} instead of a search (25 is the "record 25" number in the last result's header) | 76,866 | 72.2 |
| 3 | 21 | max_tokens, no call | 65,421 | 46.0 |
| 4 | 13 | max_tokens, no call | 41,386 | 35.6 |
| 5 | 10 | max_tokens, no call | 32,349 | 29.9 |
| 6 | 11 | stopped calling: early text answer "The workflow has been fully executed. Here's a summary..." | 34,380 | 50.0 |
| 7 | 10 | max_tokens, no call | 32,433 | 31.2 |
| 8 | 13 | max_tokens, no call | 41,464 | 43.6 |
| 9 | 11 | max_tokens, no call | 35,389 | 31.1 |

- **Calls completed: median 11.5, range 6-25 (n10).** No run reached the 50-call cap. Tokens at break: median 36,882, range 20,443-76,866.
- Break types: 8/10 max_tokens with no call (reasoning runaway), 1/10 wrong tool, 1/10 early stop. 0 invalid JSON, 0 wrong or malformed arguments, 0 repeat loops: every call before the break was exactly right.
- How it breaks (reasoning text at the break turn): instead of reading the last NEXT ACTION line, it starts re-tracing the whole chain ("Let me re-read the NEXT ACTIONs... wait, no... let me recount"), mixes up step numbers with the "record N" headers and filler, and either runs out of tokens doing that or acts on a confused trace. Normal turns are short: median 49.5 completion tokens per correct call (n132, max 1,943).
- max_tokens 8192 (seeds 0, 1) does not rescue it: seed 0 broke at the same call 7, now as a wrong tool (read_file with an invented path after 7,301 tokens; after the error it repeated that invented call once, then tried a search); seed 1 broke at the same call 13 and used all 8,192 tokens without a call.

### Context setting (seeds 0-2, max_tokens 2048)
| Context | Seed 0 | Seed 1 | Seed 2 | Median |
|---|---|---|---|---|
| 32K | 6 (max_tokens) | 11 (context overflow: 33,336 > 32,768) | 11 (context overflow: 33,309) | 11 |
| 64K | 6 (max_tokens) | 12 (max_tokens) | 22 (context overflow: 66,321 > 65,536) | 12 |
| 128K | 6 (max_tokens) | 12 (max_tokens) | 25 (wrong tool) | 12 |
| 256K | 6 (max_tokens) | 12 (max_tokens) | 25 (wrong tool) | 12 |
At ~3K tokens per result, 32K holds about 10 steps, so the window ended 2 of 3 runs there; from 128K up the model breaks first.

### Memory
- Host memory used: 70.15 GiB (57.7 %) before; peak 77.39 GiB (63.6 %) in the first batch (256K phase) and 80.10 GiB (65.9 %) in the second batch (an unrelated small job of ~0.4 GiB started on the machine during that batch). The idle 27B vLLM server stayed loaded throughout. Never near the 85 % guard.
- GPU, llama-server: 2,441 / 2,857 / 3,689 / 5,353 MiB at 32K / 64K / 128K / 256K context (27B vLLM server 59,154 MiB, unchanged; all processes peak 64,507 MiB).
- Server container memory peak: 1.47 / 1.66 / 1.78 / 1.95 GB per context in the first batch; 5.16 GB in the second batch (one 256K server for 8 runs).

### What broke (infra)
Nothing: all runs started inside the memory-capped cgroup and exited 0, no relaunches. The driver's automatic label for seed 6 was wrong ("malformed call in text", because the summary names tools); reading the turn shows an early text answer, as listed above. The published `results/tool-loop/ctx256k-seeds0-and-3-9-mt2048.summary.json` keeps the automatic label `malformed_call_in_text` for seed 6; the table above is the corrected reading.

### What it won't catch
A synthetic chain where every result spells out the next call on its last line: it measures how long the model keeps following explicit instructions as context grows, not whether it can plan, pick a tool from real output, recover from errors or find a value buried mid-document. One quant (Q8_0), one sampling setting, llama.cpp's chat template only, sequential calls only, fixed ~3K-token results with one unintended distractor (the "record N" header).

### Cleanup
Checked afterwards: no test containers, network or llama-server process left; host memory back to 58.0 %; the 27B vLLM server still answering (restarts 0).
