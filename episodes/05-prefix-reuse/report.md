# Local 27B prefix reuse: measured result and compatibility boundary

Measurements completed 8 November 2026, before 00:32 SGT, on one NVIDIA GB10 Linux ARM64 system. Three pairs per prefix length, 8192 context, serial greedy raw completions (up to 16 output tokens), prompts 263/1031/4103 tokens. All 27 accepted cold resets independently demonstrated zero reported cold cached tokens. Initial rejected SGLang flush and unprimed Ollama diagnostics are excluded.

## Matched exact-checkpoint NVFP4 comparison
Same model files/tokenizer and FP8 KV, one sequence, 2048-token prefill batching/chunking, eager execution, no drafter. Serving-stack comparison: engine cache strategies, kernels, native defaults and streaming APIs differ. Not a universal kernel/engine ranking, accuracy test or speculative daily-service benchmark.

| Engine | Shared-prefix tokens | Cold TTFT median (s) | Repeated TTFT median (s) | Reported repeated token hits |
|---|---:|---:|---:|---:|
| vllm | 256 | 0.2242 | 0.2239 | 0.00% |
| vllm | 1024 | 0.5648 | 0.5618 | 0.00% |
| vllm | 4096 | 2.1353 | 0.5465 | 76.43% |
| sglang | 256 | 0.1911 | 0.1410 | 97.34% |
| sglang | 1024 | 0.4237 | 0.1412 | 99.32% |
| sglang | 4096 | 1.6746 | 0.1488 | 99.83% |

At 4096 shared-prefix tokens, median cold/repeated TTFT ratios were 3.91x (vLLM) and 11.26x (SGLang), with measured hit rates 76.43% and 99.83%. The short vLLM repeats had zero reported hits: they are not warm-cache speedups. SGLang's first 256-token repeated query was an outlier (~0.307s) and is retained in raw data. With n=3, nearest-rank p95 is just the maximum; fixed ordering and stream packaging limit inference.

## Separate Ollama Q8_0 / FP16-KV result — NOT cross-engine-equivalent
Exact NVFP4 import failed on official ARM64 Ollama because its MLX runtime is unavailable. A hash-verified official Q8_0 GGUF imported unchanged, fully GPU-loaded with 8192 context. Other two pinned engines failed common-GGUF qualification, so no three-way common-quant ranking is claimed.

| Engine | Shared-prefix tokens | Cold TTFT median (s) | Repeated TTFT median (s) | Reported repeated token hits |
|---|---:|---:|---:|---:|
| ollama | 256 | 0.5801 | 0.5075 | 0.00% |
| ollama | 1024 | 1.1673 | 1.0863 | 0.00% |
| ollama | 4096 | 4.1227 | 2.0556 | 50.09% |

Each Ollama pair unloads/reloads, verifies empty/loaded model state and 8192 context, then runs an unrelated same-shape primer before the target cold request. The primed 4096-token result shows 2.01x median cold/repeated ratio and 50.09% reported hits. Shorter repeats report zero hits despite small timing differences. Earlier unprimed cold TTFTs 13–17s included first-forward initialization; their large apparent ratios are NOT prefix-reuse benefits.

## Reproduction and boundary
See README.md, pinned launch scripts, model SHA256 manifest, prefix_probe.py and analyze_prefix.py. Cache assertions passed on 9 accepted pairs per arm; raw records retain reset responses, per-event timestamps and per-request cache evidence. All measured servers used network-none, read-only roots/weights, default AppArmor, no-new-privileges, all capabilities dropped, 80 GiB/no-swap limits and audited 85% stop/95% kill guards. No guard override, network relaxation or optional offload/low-bit experiment was used. Observed sampled benchmark host memory stayed below 42%; sampling is not a proof of transient peak absence.

Exact-format and common-GGUF failures, and the next bounded engineering task, are documented in runtime-compatibility.md. An ARM64/SM121 MLX build for Ollama, or reviewed standalone-text GGUF loader support for the other engines, would be a separate engineering task and is not part of this kit.
