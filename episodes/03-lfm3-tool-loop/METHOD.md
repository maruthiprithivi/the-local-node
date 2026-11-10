# Method: LFM3-1.7B tool-loop check

## Model and runtime

- Model: `LiquidAI/LFM3-1.7B-GGUF`, file `LFM3-1.7B-Q8_0.gguf`, 1,846,238,496 B, sha256 `8f6b24182258205e9e01e21f1f24a1f208c1e8115578825d202ce39976af20b6` (repo sha `ee9698375b4034c0d044b8686d84e8ddb5f3ee92`).
- Runtime: llama.cpp release b11981 (commit `da6c30ade`), official prebuilt CUDA 13.4 arm64 binaries + matching CUDA runtime, mounted read-only into the image from `docker/Dockerfile`.
- Server: `llama-server -np 1 -c <ctx> -ngl 999 --jinja --alias lfm3-1.7b`. `--jinja` turns on native tool calling through the model's chat template.
- Hardware: one NVIDIA GB10 workstation (compute 12.1), aarch64, 20 cores, 121.6 GiB unified memory. An unrelated, idle 27B vLLM server stayed loaded during the run. Its memory is included in the host figures in RESULTS.md.

## Isolation

- Server container: memory 24 GiB with no swap, pids limit 2048, all capabilities dropped, no-new-privileges, read-only root, uid 1000, model and binaries mounted read-only, tmpfs `/tmp`. It runs on an internal-only Docker network with no outside route.
- Driver container: same flags, 2 GiB memory, on the same internal network. It can reach only the model port. No keys, no outside network.
- The original run put every container under a memory-capped systemd slice. In the scripts this is optional (`MEM_CGROUP`). A host memory gate refuses to start at >= 75 %, stops between contexts at >= 80 %, skips a seed at >= 85 % and kills the test containers at >= 95 %.

## The chain

`scripts/toolloop.py` defines 4 tools: `read_file(path)`, `search(query)`, `next_step(token)` and `get_record(record_id: integer)`.

- The plan is generated from `random.Random(1000 + seed)`: up to 50 calls (`--cap`), each with a tool that differs from the previous one and seeded arguments (paths, 3-word queries, 8-character tokens, 5-digit ids).
- The user prompt names call 1. Every correct call gets a result made of a header `=== result of <tool> (record N) ===`, `--filler-lines` lines of deterministic synthetic log lines (seeded `random.Random(5000 + seed)`), then `NEXT ACTION: call the tool `X` with arguments {...}`.
- With `--filler-lines 75`, the prompt grows by a median 2,999 tokens per step (range 2,976-3,274). A 110-line smoke run (~4.4K tokens per result) was not counted.
- The system prompt tells the model to make exactly the named call, one at a time, until a result says DONE.
- Requests are non-streaming, with `tool_choice: auto`, temperature 0.6, top_p 0.95, top_k 20, `seed` = run seed and `max_tokens` 2048 per turn (8192 in the sensitivity batch).

## Scoring

Scoring is strict: the first deviation ends the count. The break classes are:

- wrong tool;
- wrong or missing argument;
- invalid JSON arguments;
- a repeat of an earlier call (3x = loop);
- no call (the model stops or answers early);
- `max_tokens` reached with no call;
- server error or context overflow.

After a deviation the driver answers `Error: invalid call.` for up to 2 more turns. This only shows what the model does next and never changes the count. If the model makes several calls at once and the first is correct, the first counts. The extras get `Ignored: make one call at a time.`

`analyze.py` reports calls completed, the break class, and tokens at break, which is prompt + completion of the breaking turn (or `n_prompt_tokens` from an overflow error). It also reports wall time, post-break behaviour and memory peaks from `mem.csv`.

Automatic labels can be wrong. Seed 6 was labelled `malformed_call_in_text` because its early text answer names tools. Reading the turn shows an early stop, and RESULTS.md reports it that way.

## Runs

1. Context sweep: 32K, 64K, 128K and 256K, seeds 0-2, `max_tokens` 2048 (`run-toolloop.sh`).
2. 256K, seeds 0 and 3-9, `max_tokens` 2048 (`run-toolloop-part2.sh`, first half). Seed 0 is a determinism re-check.
3. 256K, seeds 0-1, `max_tokens` 8192 (`run-toolloop-part2.sh`, second half).

The same seed behaved identically on every server. So the context settings are not extra samples, and the independent samples are the 10 seeds at 256K. At ~3K tokens per step, the 50-call cap fits in 256K, so a break at 256K is the model's, not the window's.

## Decode speed (parts A and B)

`bench-decode.sh` runs `llama-bench -p 512 -n 128 -r 5` per quant with no network. It then serves Q8_0 (1 slot, 32K) and runs `client.py`: 1 warm-up (discarded), then 5 rounds of a 32-token short chat plus a 512-token decode, at concurrency 1.

## Not included

Part C of the original test (a 5-task coding check with the Pi agent in OpenShell sandboxes) used an unpublished benchmark harness and task suite. Its results are in RESULTS.md, but it cannot be repeated from this kit.
