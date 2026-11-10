# Results: Qwen Code system-prompt trimming (full / ~60 % / ~24 % / minimal)

Status: DONE, reduced version (honest subset, see "Run counts"). Run Nov 3 2026 on one GB10 workstation, suite wall 28 min.
Published here: the four prompt files (`prompts/`), the analysis scripts (`scripts/`), per-run and per-level aggregates (`results/per-run-and-level.json`) and pooled per-request aggregates (`results/pooled-requests.json`). Raw request logs and per-run artifacts are not published (see LEAKCHECK.md).

## Setup
- Harness: Qwen Code 0.26.1 (`--system-prompt <text>` replaces the built-in main-session prompt). Full level = stock harness (no flag, built-in prompt).
- Model: local Qwen3.8-27B NVFP4 + DSpark k=7 (probabilistic draft sampling), vLLM, 131,072 ctx, temp 0.6 / top_p 0.95 / top_k 20 (declared, checked by a logging proxy), prefix caching on.
- Sandbox: OpenShell 0.1.6, one fresh sandbox per run, network none except the forwarder binary to the model port; hidden tests only in a separate network-less scoring sandbox; a memory-capped cgroup.
- Our 10-task everyday coding suite, strict scoring, budget 40,000 completion tokens/run, wall cap 2400 s/run, concurrency 8, harness variants interleaved.
- Prompt levels (chars counted from the system message actually sent, which includes ~950-976 chars Qwen Code appends after the prompt, e.g. environment/context):

| Level | File chars (words) | System message chars sent | What was removed vs full |
|---|---|---|---|
| p100 (full, built-in) | 18,698 (2,806) | 19,651 | nothing |
| p60 (~60 %) | 11,233 (1,711) | 12,193 | sections "New Applications", "Interaction Details" (Help Command, Feedback), "Outside of Sandbox", "Executing actions with care", "Git Repository" + "Git as Source of Truth", all "Examples"; Core Mandates, SE workflow, Communication, Tone, Security, Tool usage kept |
| p30 (~24 %) | 4,478 (681) | 5,446 | additionally: all of Operational Guidelines (Communicating With the User, Tone and Style, Security and Safety Rules) and New Applications; 4 sections remain (Core Mandates, Software Engineering Tasks, Using Your Tools, Final Reminder) with 10 of the original bullets: Conventions, Libraries/Frameworks, Do Not revert changes, Report outcomes faithfully, Implement, Verify, File Paths, Prefer Dedicated Tools, Background Processes, Denied Tool Calls. Dropped bullets include Proactiveness, Comments, Plan, Parallel Tool Calls, Security First, Explain Critical Commands, Subagent Delegation, Tool Fallback, Preserve Existing Work, Answer From Context First |
| pmin (minimal, ~1.3 %) | 235 (one paragraph) | 1,211 | everything except: "You are Qwen Code, a non-interactive CLI coding agent. Use your tools to complete the user's task in the current project, run the project's tests to verify, and end with a short summary. This is a single-turn run: never ask questions." |

Tool schemas (10 tools) are sent unchanged at every level; they are ~8.1K of the first request's ~8.3-12.3K prompt tokens.

## Run counts
REDUCED: 5 of the 10 everyday tasks (01-bugfix-pagination, 03-refactor-reports, 05-stacktrace-ingest, 08-pr-review, 09-multifile-api = the 5 fastest for Qwen Code in the earlier full-c8 suite) x 2 seeds (0, 1) x 4 levels = 40 runs, all 40 completed, 0 infra retries (attempts 1 each), 0 timeouts, 0 budget hits. Not run: 02, 04, 06, 07, 10 (slower, 06 runs near the 40K budget), to stay inside the ~40 min time box.

## Results per level (10 runs each; median [min-max])

| Level | Tasks passed (strict) | First-request prompt tokens | Prompt tokens / request (per-run mean) | Requests / run | TTFT per run (median of its requests), s | Wall / run, s | Completion tokens / run |
|---|---|---|---|---|---|---|---|
| p100 | **10/10** | 12,189 [12,168-12,300] | 16,837 [14,581-26,088] | 7 [5-13] | 1.68 [1.17-2.97] | 299 [160-975] | 5,517 [2,259-12,291] |
| p60 | **10/10** | 10,575 [10,555-10,686] | 14,294 [13,223-21,275] | 8 [4-12] | 1.55 [1.13-2.16] | 282 [177-360] | 4,705 [2,597-6,679] |
| p30 | **10/10** | 9,187 [9,167-9,297] | 12,383 [11,308-45,634] | 7 [5-23] | 1.41 [1.21-5.72] | 239 [148-1,213] | 4,124 [2,381-15,923] |
| pmin | **9/10** | 8,324 [8,304-8,435] | 12,030 [11,163-13,714] | 7 [4-9] | 1.53 [1.24-2.40] | 273 [171-419] | 4,972 [2,912-8,153] |

Pooled over all requests (all 200 OK): p100 n=85, prompt tokens/request median 17,151, TTFT median 1.641 s (p95 6.96 s); p60 n=80, 14,768, 1.549 s (6.61 s); p30 n=92, 13,699, 1.600 s (8.57 s); pmin n=65, 12,513, 1.485 s (3.92 s). Uncached (actually prefilled) tokens/request median: 1,888 / 1,713 / 2,162 / 1,728. Cached share of all prompt tokens: 85.3 / 84.9 / 84.6 / 82.6 %.

- Prompt saving: full -> minimal saves ~3,865 prompt tokens on every request (12,189 -> 8,324 first request, -32 %); p60 saves ~1,614, p30 ~3,002.
- Quality: no measurable loss down to p30 (10/10 each). The only miss is pmin 08-pr-review s0 (strict fail: found 1/4 planted bugs, 4 false positives); pmin 08 s1 passed. One miss in 10 runs is inside seed noise; it does not show a real drop.
- TTFT: barely moves (median per request 1.49-1.64 s at every level) because vLLM prefix caching serves the fixed system prompt + tools from cache after the first request; only ~1.7-2.2K uncached tokens are prefilled per request. First request of a run (cold system prompt) was 1.3-22.1 s, dominated by 8 runs starting together at c8, not by prompt size.
- Wall time and total tokens are dominated by single long runs (p100 08 s0 975 s / 10 requests, p30 08 s0 1,213 s / 23 requests / 1.05M prompt tokens), not by the prompt level.

## Environment
- One NVIDIA GB10 box, 121.6 GiB unified memory, 20 cores; vLLM (spark-vllm-b12x image), NVFP4 + DSpark k=7 probabilistic, gpu util 0.50, max-num-seqs 8, max-num-batched-tokens 4096, max-model-len 131072.
- Host memory (5 s samples): peak 73.81 GiB = 60.7 %; start 55.7 %.

## What broke
Nothing in the run (40/40 completed, rc 0). Caveat: 2 seeds x 5 tasks is small; the levels cannot be told apart statistically on pass rate. TTFT is measured under c8 contention (interleaved, so each level saw similar load).

## What it won't catch
Harder or longer tasks (06-sql-migration, multi-hour work), other harnesses (omp, dsh, Pi), prompt-cache-cold deployments where the trimmed prompt would cut real prefill, and safety behaviour (the removed "Security and Safety" / "Executing actions with care" text is not exercised by these tasks).
