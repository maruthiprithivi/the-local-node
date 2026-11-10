# LFM3-1.7B tool-loop check

Follow-along kit in [The Local Node](https://github.com/maruthiprithivi/the-local-node).

How many chained tool calls does [LiquidAI LFM3-1.7B](https://huggingface.co/LiquidAI/LFM3-1.7B-GGUF) make correctly, with ~3K-token tool results fed back each step, before it breaks? This kit has the driver, the run scripts and the measured results from one NVIDIA GB10 workstation (Nov 3-4 2026). It also covers the decode-speed numbers from the same test.

**Headline (10 seeds, 256K context, Q8_0, llama.cpp b11981):** median **11.5** correct calls before the first deviation (range 6-25). No run reached the 50-call cap. 8 of 10 breaks were the model reasoning until `max_tokens` without making a call. Every call before the break was exactly right: 0 invalid JSON, 0 wrong arguments, 0 repeat loops. Raising `max_tokens` from 2048 to 8192 did not help. Full tables are in [RESULTS.md](RESULTS.md).

## What is in here

| Path | What it is |
|---|---|
| `RESULTS.md` | The public write-up with every measured number (tool loop, decode speed, footprint, the small coding check) |
| `METHOD.md` | Exactly how the tool-loop chain, scoring and runs work, plus how to reproduce |
| `scripts/toolloop.py` | The tool-loop driver used in the run (stdlib Python, OpenAI-compatible `/v1/chat/completions` with native tools) |
| `scripts/mock_server.py` | A tiny mock server to test the driver without a GPU |
| `scripts/analyze.py` | Turns a run directory into the per-seed `summary.json` and the medians |
| `scripts/run-toolloop.sh` | Context sweep (32K/64K/128K/256K x seeds 0-2) in hardened containers |
| `scripts/run-toolloop-part2.sh` | Extra seeds 0, 3-9 at 256K, then `max_tokens` 8192 for seeds 0-1 |
| `scripts/bench-decode.sh`, `scripts/client.py` | Part A (llama-bench) and part B (llama-server decode at concurrency 1) |
| `scripts/download-models.sh` | Downloads the official GGUFs and checks their sha256 |
| `docker/Dockerfile` | The small runtime image the llama.cpp binaries are mounted into |
| `results/tool-loop/*.summary.json` | Per-seed results for the three tool-loop batches |
| `results/decode/*.json` | Raw llama-bench output per quant and the decode client output |
| `LEAKCHECK.md` | What was scanned before publishing and what was left out |
| `MANIFEST.sha256` | Checksums of every file in this folder |

## Quick start

Try the driver against the mock first (no GPU):

```bash
python3 scripts/mock_server.py 18555 5 &
python3 scripts/toolloop.py http://127.0.0.1:18555 mock 0 32768 /tmp/tl-mock.json --cap 12 --filler-lines 5
kill %1
```

The mock repeats an earlier call at call 6, so the driver should report `calls_completed: 5` and a `repeat_earlier_call` break.

Then point it at a real server. Any OpenAI-compatible endpoint with native tool calling works:

```bash
llama-server -m LFM3-1.7B-Q8_0.gguf -np 1 -c 262144 -ngl 999 --jinja --alias lfm3-1.7b --port 8080
python3 scripts/toolloop.py http://127.0.0.1:8080 lfm3-1.7b 0 262144 run-c262144-s0.json --filler-lines 75 --max-tokens 2048
```

The original run kept the model server and the driver in separate locked-down containers on an internal-only network. To repeat it that way:

```bash
docker build -t tlnode-runtime:0.1 docker/
export MODEL_DIR=$PWD/models/LFM3-1.7B-GGUF LLAMA_DIR=/path/to/llama-b11981 CUDART_DIR=/path/to/cudart-llama-b11981-bin-ubuntu-cuda-13.4-arm64
bash scripts/download-models.sh
OUT_DIR=$PWD/runs bash scripts/run-toolloop.sh          # context sweep, seeds 0-2
python3 scripts/analyze.py runs                          # writes runs/summary.json
OUT_BASE=$PWD bash scripts/run-toolloop-part2.sh         # seeds 0,3-9 at 256K, then max_tokens 8192
python3 scripts/analyze.py runs-extra; python3 scripts/analyze.py runs-mt8192
```

`LLAMA_DIR` and `CUDART_DIR` are the unpacked official llama.cpp release b11981 assets for your platform. The original run used the CUDA 13.4 arm64 build. Change the paths for other platforms.

The chain is generated from the seed, so the same seed should give the same plan on your machine. With the same model file, runtime build and sampling, seed 0 broke at call 7 the same way in all 5 of our runs at `max_tokens` 2048. Expect small differences on other GPUs or builds.

## What this check cannot show

Each result spells out the next call on its last line. So this measures how long the model keeps following explicit instructions as context grows. It does not test planning, picking a tool from real output, recovering from errors, or finding a value buried mid-document. It used one quant (Q8_0), one sampling setting, llama.cpp's chat template only, and sequential calls only.

## License

This folder is part of The Local Node repository. LFM3 weights and llama.cpp have their own licenses; this kit does not bundle them.
