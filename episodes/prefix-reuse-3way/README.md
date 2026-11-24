# Prefix reuse, three ways: vLLM vs SGLang vs Ollama on one BF16 source

Reproduction kit in [The Local Node](https://github.com/maruthiprithivi/the-local-node).

This follows up [`05-prefix-reuse`](../05-prefix-reuse/). That kit could not put all three engines on the same weights (Ollama cannot load the NVFP4 checkpoint). This run does: vLLM and SGLang load one unquantized BF16 Hugging Face tree of **Qwen3.5-4B**, and Ollama loads a BF16 GGUF converted from that same tree. Same probe, same analyzer, same three prefix lengths, all on one NVIDIA GB10 (Linux ARM64) workstation on 14 November 2026 (UTC+8).

It is a timing and cache microbenchmark, not an accuracy test. The question is whether a repeated raw-text prefix is actually reused, shown by the engine's own count of cached prompt tokens, and what that does to time to first token (TTFT).

**You do not need a GPU to check the numbers.** The raw per-pair JSONL from the run is committed. `./reproduce.sh` re-runs the analyzer on it with the Python 3 standard library and diffs the output against the committed summaries.

## Headline

Three cold/repeated pairs per prefix length, 8192 context, greedy, 16 output tokens. "Hit fraction" is cached tokens / query tokens on the repeated request. Reuse is only counted when the engine reported hits above zero.

| engine | prefix | cold TTFT p50 (s) | repeated TTFT p50 (s) | repeated hit fraction | cold/repeated | reuse shown |
|---|---:|---:|---:|---:|---:|---|
| vLLM | 256 | 0.0846 | 0.0789 | 0.0000 | 1.07x | no |
| vLLM | 1024 | 0.1963 | 0.1059 | 0.5121 | 1.85x | yes |
| vLLM | 4096 | 0.6911 | 0.1069 | 0.9008 | 6.46x | yes |
| SGLang | 256 | 0.0809 | 0.0616 | 0.9734 | 1.31x | yes |
| SGLang | 1024 | 0.2087 | 0.0669 | 0.9932 | 3.12x | yes |
| SGLang | 4096 | 0.6245 | 0.0639 | 0.9983 | 9.78x | yes |
| Ollama | 256 | 0.1384 | 0.1186 | 0.0000 | 1.17x | no |
| Ollama | 1024 | 0.2781 | 0.2541 | 0.0000 | 1.09x | no |
| Ollama | 4096 | 0.9649 | 0.4832 | 0.5009 | 2.00x | yes |

(`python3 table.py` prints this table from `summaries/`. Full precision is in the JSON.)

What it shows:

- **SGLang** reused the entire shared prefix at every length (256 / 1024 / 4096 cached tokens out of 263 / 1031 / 4103; only the differing 7-token suffix was recomputed).
- **vLLM** reuses in whole blocks. On this hybrid linear-attention model it set the attention block size to **528 tokens** (see `log-excerpts.md`), so the 256-token prefix got 0 hits by construction, 1024 got 528 and 4096 got 3696.
- **Ollama** reported 0 cached tokens at 256 and 1024, so those small TTFT gaps are not counted as reuse. At 4096 it cached 2055 of 4103 tokens, about half.

## Method

- Prompts: a shared raw-text prefix of 256, 1024 or 4096 tokens plus a 7-token suffix. The probe asserts query token counts of 263 / 1031 / 4103 with the model's own tokenizer.
- Prefix text is `' alpha'` repeated and cut to the exact token count. Suffixes are `\nQuestion A: Reply OK.` (cold) and `\nQuestion B: Reply OK.` (repeated), so the two requests share the prefix but not the last 7 tokens.
- Each pair: reset the cache, send the cold request, then the repeated-prefix request. 3 repeats per length, a fresh reset before every pair.
- Resets: vLLM `POST /reset_prefix_cache`, SGLang `flush_cache`, Ollama unload and reload. After an Ollama reload the probe sends an unrelated same-shape primer (`--prime-after-load`) so the first forward pass's warm-up cost does not pose as a cache effect. The analyzer refuses Ollama data without primers (`--require-primer`).
- Hit accounting: vLLM `prefix_cache_hits_total` / `prefix_cache_queries_total` counter deltas from `/metrics`; SGLang `cached_tokens` and `prompt_tokens` in the final stream event; Ollama `prompt_eval_cached_count` and `prompt_eval_count`.
- The analyzer fails unless every reset succeeded, every cold request reported 0 hits and every token count matches. TTFT is client wall time to the first non-empty streamed text event. With n=3, p50 is the middle sample and "p95" is the maximum.
- Isolation: every server ran in Docker with `--network none --read-only --cap-drop ALL --security-opt no-new-privileges`, under a cgroup with a memory watchdog (start nothing above 85% memory, stop at 95%). The probe reached each server through its network namespace only.

### Engines and flags

| engine | image | weights | key flags |
|---|---|---|---|
| vLLM | `eugr/spark-vllm-b12x@sha256:03a95654…` | HF BF16 tree | `--dtype bfloat16 --enable-prefix-caching --enable-chunked-prefill --max-model-len 8192 --max-num-seqs 1 --max-num-batched-tokens 2048 --gpu-memory-utilization 0.15 --seed 0 --enforce-eager` |
| SGLang | `lmsysorg/sglang@sha256:7f132b89…` | same HF BF16 tree | `--dtype bfloat16 --kv-cache-dtype auto --context-length 8192 --mem-fraction-static 0.22 --max-mamba-cache-size 5 --max-running-requests 1 --chunked-prefill-size 2048 --disable-cuda-graph` |
| Ollama v0.40.13 | `ollama/ollama@sha256:b2f0122c…` | BF16 GGUF from the same tree | `OLLAMA_KV_CACHE_TYPE=f16 OLLAMA_CONTEXT_LENGTH=8192 OLLAMA_FLASH_ATTENTION=true OLLAMA_NUM_PARALLEL=1` |

Full digests and commands are in `launch/`. The flags listed are the ones the server logs show (`log-excerpts.md`).

### One source of weights

- `provenance/hf-weights.sha256`: sha256 of every file in the BF16 HF tree that vLLM and SGLang loaded. The tree was checked with `sha256sum -c` on the test host before the run.
- The GGUF was made with llama.cpp `convert_hf_to_gguf.py --outtype bf16` (commit `8642541`) from that tree: 441 tensors, 8,665,619,904 bytes, sha256 in `provenance/gguf.sha256`. Ollama ran llama-server on that exact blob, and `ollama show` reported `quantization BF16`.
- `provenance/tensor_equiv.py` and `tensor-equiv.json` are an automated HF-vs-GGUF tensor check. It **did not pass**, and that file is an incomplete checker, not proof the weights differ: it misread GGUF dtype codes (so shapes look 2x wide) and its name map misses the converter's renames and transforms (fused QKV, linear-attention and MTP tensors, norm offsets). The supported claim is provenance: same hashed source, `--outtype bf16`, the hashed GGUF, and Ollama reporting BF16.

## Reproduce the analysis (no GPU)

Needs only Python 3 (standard library; tested with 3.12 and 3.13) and `sha256sum`.

```bash
git clone https://github.com/maruthiprithivi/the-local-node.git
cd the-local-node/episodes/prefix-reuse-3way
./reproduce.sh
```

It verifies `SHA256SUMS`, runs `analyze_prefix.py` on each `raw/*-pairs.jsonl`, diffs against `summaries/*-summary.json` (any difference exits non-zero), and prints the headline table. By hand:

```bash
python3 analyze_prefix.py vllm   raw/vllm-pairs.jsonl
python3 analyze_prefix.py sglang raw/sglang-pairs.jsonl
python3 analyze_prefix.py ollama raw/ollama-pairs.jsonl --require-primer
```

## Re-running the probe (optional, needs a GPU host)

`prefix_probe.py` and `launch/` are what ran, kept as a reference. Re-running needs the Qwen3.5-4B BF16 tree (check it against `provenance/hf-weights.sha256`), a BF16 GGUF for Ollama, Docker with GPU access, and a host memory watchdog you have already audited. The launch scripts do not install one: they refuse to start unless `bench.slice`, `bench-memguard` and `earlyoom` are active and `MODEL_DIR`, `STOP_MARKER` and `RESULTS` (plus `GGUF_PATH` for Ollama) are set. For Ollama, import with `ollama create prefix-local -f launch/Modelfile` (the Modelfile expects the GGUF at `/gguf/qwen3.5-4b-bf16.gguf` inside the container). The probe needs `transformers` for the tokenizer; the Ollama image has none, so it ran in a separate driver container sharing the Ollama container's network.

```bash
python3 prefix_probe.py --engine vllm   --port 18000 --model prefix-local --repeats 3 > vllm-pairs.jsonl
python3 prefix_probe.py --engine sglang --port 30000 --model prefix-local --repeats 3 > sglang-pairs.jsonl
python3 prefix_probe.py --engine ollama --port 11435 --model prefix-local --repeats 3 --prime-after-load > ollama-pairs.jsonl
```

Expect different absolute TTFTs on other hardware. The hit counts should match, because they come from block sizes and cache policy, not speed.

## Caveats

- **Small model.** Qwen3.5-4B in BF16: a hybrid model (linear attention / Gated DeltaNet plus full attention, MTP head, multimodal checkpoint). It is not a 27B or a dense-transformer result, and the vLLM 528-token block comes from this hybrid design.
- **One host.** All three arms ran on a single GB10 workstation. An unrelated server on the same machine held about 56 GiB of memory the whole time, so absolute TTFTs include that background load. All three arms ran under it, so the ratios and hit fractions compare fairly, but the absolute numbers will not transfer.
- **3 repeats.** n=3 per length. p50 is the middle sample and p95 is the maximum, not a real tail estimate.
- **No GPU rerun for this kit.** The numbers come from the 14 Nov run. The kit re-derives them from the committed raw files; it does not re-measure.
- **Ollama is close, not identical.** Its weights are BF16 but its KV cache is f16 (no bf16 KV option), and the GGUF is a text-only converted view of the same source, not a byte-identical copy. The automated tensor check did not pass (see above). The Ollama image is v0.40.13, not the digest pinned in `05-prefix-reuse`.
- **Startup outlier kept.** SGLang's first 256-token pair was slow (cold 0.324 s, repeated 0.212 s). It was kept; the p50 is unaffected.
- **Seeds.** vLLM ran with `--seed 0`. SGLang picked its own random seed (not set). Decoding was greedy for all three.

## What is in here

| Path | What it is |
|---|---|
| `README.md` | This page: method, results, how to reproduce, caveats |
| `reproduce.sh` | Checks hashes, re-runs the analyzer on `raw/`, diffs against `summaries/`, prints the table |
| `analyze_prefix.py` | Asserts reset, cold miss and token accounting, prints the per-engine summary JSON |
| `table.py` | Prints the headline table from summary JSON |
| `prefix_probe.py` | The probe that produced `raw/` (needs live servers; reference) |
| `raw/{vllm,sglang,ollama}-pairs.jsonl` | Raw evidence from the run: resets, primers, every streamed event, metrics snapshots |
| `summaries/{vllm,sglang,ollama}-summary.json` | Analyzer output as committed |
| `launch/launch-{vllm,sglang,ollama}-bf16.sh`, `launch/Modelfile` | Launch commands and pinned images as run (reference) |
| `provenance/` | Weight and GGUF hashes, plus the tensor check and its (failed) output |
| `log-excerpts.md` | The server log lines behind the flag and block-size claims |
| `LEAKCHECK.md` | What was scanned before publishing and what was left out |
| `SHA256SUMS` | sha256 of every other file in this folder |

Not included: model weights, the 8.7 GB GGUF, container images, and the full server logs (excerpts only).

## License

This folder is part of The Local Node repository. Qwen3.5-4B, vLLM, SGLang, Ollama and llama.cpp have their own licenses; this kit does not bundle them.
