# Prefix-reuse measurement method

SGT, 7–8 November 2026. All timing work was serial on one isolated benchmark machine. Unpublished recovery and diagnostic evidence is held out of this folder; see report.md.

## Matched NVFP4 serving-stack comparison
Identical read-only Qwen3.8-27B-NVFP4 directory and tokenizer, modelopt MIXED_PRECISION checkpoint (FP8 projections, NVFP4 MLP/head), 8192 context, one request at a time, 2048-token chunk/batch, FP8 KV, eager execution, no speculation. Pinned image digests and exact launch options are in the launch-*.sh scripts in this folder. SGLang explicitly uses float32 Mamba state and extra_buffer radix strategy; vLLM retains its native Mamba defaults. Native allocation/kernels differ; equal .35 memory fraction is not equal allocator size.

Raw text shared prefixes have 256/1024/4096 tokenizer tokens, followed by a 7-token question suffix, A then B. Greedy requests allow at most 16 output tokens. Each length has three cold/repeated pairs in fixed increasing-length order. This is a cache microbenchmark, not accuracy, throughput or daily speculative-service testing.

Reset before EVERY pair: vLLM reset_prefix_cache successful response and independently zero cold hit-counter delta; SGLang flush_cache successful response and independently zero cached_tokens on the cold request. The initial SGLang busy HTTP400 flush was rejected and excluded; a fresh server run yielded all nine accepted resets. Preserve rejected evidence, do not mix it into timing results.

vLLM uses per-request differences of prefix_cache_hits_total / prefix_cache_queries_total; SGLang uses meta_info.cached_tokens / prompt_tokens. A repeated query with zero reported hits is explicitly NOT a warm-cache hit. Matching prompt counts (263/1031/4103) and actual prompt text are checked. Analyze with analyze_prefix.py.

TTFT is client wall time to first nonempty textual stream event. vLLM OpenAI completions and SGLang native generate wrappers have different stream packaging; these are serving-stack measurements, not isolated kernel rankings. Report median over three pairs; nearest-rank p95 equals the maximum at n=3 and is not robust tail evidence. Keep outliers. No order randomization, confidence claims or universal winner claims.

## Separately labeled Ollama Q8 arm
Exact NVFP4 safetensors could not import on official Linux ARM64 Ollama (missing MLX runtime). A common-GGUF route failed qualification in the other two pinned engines; see public/runtime-compatibility.md. Therefore Ollama Q8_0 plus FP16 KV is a SEPARATE within-engine experiment, NOT an engine-only comparison against NVFP4.

The official Q8_0 GGUF is hash-verified, imported without requantization, fully GPU-loaded, context8192, parallel1, batch2048. Each pair unloads the runner, verifies empty api/ps, reloads and verifies context8192, then runs an unrelated same-shape ZEBRA primer (different first token, asserted token count) before target cold/repeated requests. Target cold cached count MUST be zero. The primer removes runner first-forward initialization from the target comparison without prewarming its prefix. Require primer evidence in analyzer.

Earlier unprimed Ollama pairs are preserved as DIAGNOSTIC ONLY: 13–17 second cold starts versus much faster repeats, including zero-hit repeats, prove latency alone would manufacture a false cache story. Do not use these as cache speedups.

## Safety/reproduction
Inference/third-party runtime execution only in isolated network-none containers: read-only root and weights, default AppArmor, no-new-privileges, cap-drop ALL, no keys, no host network, audited bench.slice/memguard/earlyoom, 80GiB/no-swap server limits and conservative projected startup checks. Owned cache volumes provide JIT storage without changing noexec/AppArmor policy. Driver checks 85% before each inference; host guard and watcher enforce 95% kill of owned work. No guard exception or optional model/offload trial was used. Public reproduction scripts require a separately audited watchdog and memory budget, and do not provision or weaken host security.
