# Raw-text prefix-reuse timing and cache microbenchmark

Follow-along kit in [The Local Node](https://github.com/maruthiprithivi/the-local-node).

This is a timing and cache microbenchmark, not an accuracy evaluation. It measures whether a raw-text shared prefix is actually reused (token-level hit evidence) on vLLM, SGLang and Ollama, and how that shows up in time to first token. The numbers are from one NVIDIA GB10 Linux ARM64 workstation (8 November 2026, before 00:32 SGT).

**Headline (three pairs per prefix length, 8192 context, greedy, up to 16 output tokens):**

- At 4096 shared-prefix tokens, vLLM's median cold/repeated TTFT was 2.1353 s / 0.5465 s (3.91×) with 76.43% reported repeated-token hits. SGLang was 1.6746 s / 0.1488 s (11.26×) with 99.83% hits.
- vLLM's 256- and 1024-token repeats reported 0.00% hits, so those timing gaps are not warm-cache speedups.
- Ollama is a separate Q8_0 / FP16-KV arm, not a like-for-like comparison with the NVFP4 engines. At 4096 tokens, primed median cold/repeated TTFT was 4.1227 s / 2.0556 s (2.01×) with 50.09% reported hits.

Full tables and caveats are in [report.md](report.md).

## What is in here

| Path | What it is |
|---|---|
| `report.md` | The public write-up with every measured number |
| `METHOD.md` | How the prefixes, resets, scoring and runs work |
| `runtime-compatibility.md` | Why Ollama could not load the same NVFP4 checkpoint, and why there is no three-engine common-quant ranking |
| `prefix_probe.py` | The probe: raw-text prefixes, resets, primers (Ollama), timestamps and cache metrics |
| `analyze_prefix.py` | Asserts reset, cold-miss and cache accounting, then prints the summary tables |
| `launch-vllm-nvfp4.sh`, `launch-sglang-nvfp4.sh` | Pinned image digests and launch flags for the matched NVFP4 arms |
| `launch-ollama-q8.sh` | Pinned image digest and import/launch flags for the separate Q8_0 arm |
| `nvfp4-model-sha256.txt` | Checksums of the NVFP4 model files used |
| `vllm-asserted-summary.json`, `sglang-asserted-summary.json`, `ollama-q8-primed-summary.json` | Analyzer output from the original run |
| `LEAKCHECK.md` | What was scanned before publishing and what was left out |
| `MANIFEST.sha256` | Checksums of every file in this folder |

## How to use this kit

You can read the results with no GPU. Open [report.md](report.md) and the three `*-summary.json` files; those summaries are the analyzer output from the original run.

Re-running the probe needs an isolated model server, the matching tokenizer mounted read-only at `/models`, and a host resource watchdog you have already audited. The launch scripts do not install that watchdog. They will refuse to start unless `bench.slice`, `bench-memguard` and `earlyoom` are already active, and unless `MODEL_DIR` (or `ARTIFACT_DIR` for Ollama) and `STOP_MARKER` are set. That is intentional: this kit does not provision or weaken host security.

```bash
export MODEL_DIR=/absolute/path/to/nvfp4-model
export STOP_MARKER=/absolute/path/to/your/stop-marker
bash launch-vllm-nvfp4.sh          # or launch-sglang-nvfp4.sh
# Ollama Q8 arm (not equivalent to NVFP4):
#   export ARTIFACT_DIR=/absolute/path/to/q8-artifacts
#   bash launch-ollama-q8.sh
```

Then run the probe inside the isolated serving container, or in an isolated driver that shares only that container's network namespace. It uses Python stdlib HTTP plus the engine's installed Transformers tokenizer. Mount the tokenizer and weights read-only. No credentials or remote model code are required. vLLM needs developer mode only inside that isolated container (`VLLM_SERVER_DEV_MODE=1` is already in the launch script).

```bash
python3 prefix_probe.py --engine vllm --port 8000 --model prefix-local --repeats 3
python3 prefix_probe.py --engine sglang --port 30000 --model prefix-local --repeats 3
python3 prefix_probe.py --engine ollama --port 11434 --model prefix-local --repeats 3 --prime-after-load
```

Analyze counter deltas, not lifetime hit rates. Assert cold hits are zero after each successful reset. A repeated-prefix query with measured zero hits is a no-reuse result, not a warm hit. If reset is refused, that pair is invalid unless a separately logged fresh-process reset establishes cold state.

```bash
python3 analyze_prefix.py vllm vllm-pairs.jsonl
python3 analyze_prefix.py sglang sglang-pairs.jsonl
python3 analyze_prefix.py ollama ollama-primed-pairs.jsonl --require-primer
```

Suggested common workload (already encoded in the probe and launch scripts): 8192 max context, one request at a time, greedy sampling, 16 output tokens, raw completion text, 256/1024/4096 shared-prefix tokens. Keep speculation off. For comparable initial operating points, use 2048-token prefill batching or chunks, FP8 KV for the two NVFP4 arms, eager execution, and matching CPU limits. Engine-specific state allocation and kernels still differ.

Pin image digests and model hashes, verify GPU architecture support, and audit the host's resource watchdog before starting. Stop owned containers after collecting evidence.

## Ollama first-forward trap

Unloading also destroys the runner's kernel/graph warm state. After each unload/reload, use the unrelated **same-shape primer** before the target cold request (`--prime-after-load`). Its first token differs from the target, and target cold cached tokens must still be zero. A large latency drop with zero cached tokens is not evidence of prefix reuse. Preserve primer events as part of the evidence. The analyzer reports no positive reuse when repeated-token hits are zero. For only three pairs, nearest-rank p95 is simply the maximum, not a robust tail estimate.

## What this kit does not include

The raw per-pair JSONL (timestamps, server responses, reset bodies) is not published; only the asserted summaries and the write-up are. Host watchdog configuration is a precondition, not something these scripts install. An early rejected SGLang flush and earlier unprimed Ollama pairs were kept out of the timing results; they are described in report.md and METHOD.md but are not in this folder.

## What this check cannot show

No result may be called a warm-cache speedup without token-level hit evidence. Absence of a cached-token counter is not zero hits: mark hit accounting unverified. Do not silently replace checkpoints, quantization, KV dtype, or speculative decoding between engines.

This is not an accuracy, throughput, or daily speculative-service benchmark, and it is not a universal kernel or engine ranking. Ollama Q8_0 plus FP16 KV is not equivalent to the NVFP4 arms. With n=3, do not treat p95 as a robust tail. TTFT is client wall time to the first nonempty textual stream event; vLLM and SGLang package streams differently.

## License

This folder is part of The Local Node repository. Model weights, vLLM, SGLang and Ollama have their own licenses; this kit does not bundle them.
