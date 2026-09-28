# 14 · The Spark track: vLLM, SGLang, speculation, two boxes

> **Lab book:** Local labs → **L9** · DGX Spark section  **Watch:** video 9 `09-serving-stack.mp4`, video 13 `13-scale-out.mp4`
> **Time:** 2–3 h  **Cost:** free (your hardware)

## What and why

The Mac covers the concepts. The Spark gives you the **production server stack** the job
description names: **vLLM** and **SGLang** on an NVIDIA GPU, in containers, benchmarked
with the same harness you built in lessons 01, 03 and 06. The DGX Spark (GB10, 128 GB
unified memory, ~273 GB/s) has about the same bandwidth as an M4 Pro, so your ceiling
maths carries straight over. The difference is the software: CUDA, FP8/NVFP4 and the
engines customers run.

```
Mac  ──(same python scripts, --target spark)──►  Spark :8000 vLLM   /  :30000 SGLang
```

## The scripts

| script | where it runs | does |
|---|---|---|
| `remote.sh X.sh` | Mac | runs any script below on the Spark over SSH |
| `0_check.sh` | Spark | GPU, driver, CUDA, memory, and whether Docker can see the GPU |
| `1_vllm.sh [model]` | Spark | vLLM container with prefix caching; prints the KV pool size |
| `2_bench.sh` | **Mac** | lessons 01, 03 and 06 against the Spark, with Mac and Spark curves on one chart |
| `2b_vllm_bench.sh` | Spark | `vllm bench serve` as a cross-check on your own numbers |
| `3_sglang.sh [model]` | Spark | SGLang with `--enable-cache-report`; RadixAttention hits |
| `9_teardown.sh` | Spark | frees the GPU |
| `TWO_BOX.md` | – | fabric first (iperf, NCCL busbw), then TP=2 or PP=2 |

## Run

```bash
# .env: SPARK_IP=…, HF_TOKEN=… (for gated models)
cd lessons/14-spark-track
bash remote.sh 0_check.sh
bash remote.sh 1_vllm.sh nvidia/Llama-3.1-8B-Instruct-FP8
bash 2_bench.sh
bash remote.sh 2b_vllm_bench.sh
bash remote.sh 3_sglang.sh Qwen/Qwen3-8B
SPARK_URL=http://$SPARK_IP:30000/v1 SPARK_MODEL=Qwen/Qwen3-8B \
  python ../06-prefix-caching/prefix_bench.py --target spark --usage
bash remote.sh 9_teardown.sh
```

Container tags move quickly. If an image tag isn't found, look up the current GB10/arm64
tag (links are in the script comments) and set `VLLM_IMAGE` or `SGLANG_IMAGE`.

## What you should see

- The vLLM log line `Maximum concurrency for 8192 tokens per request: …x` is lesson 05's KV maths done by the engine.
- The Spark's sweep curve keeps rising well past the Mac's, because vLLM's continuous batching and paged KV cache handle many users far better than a laptop server.
- The SGLang usage block shows `cached_tokens` close to the preamble size on calls 2 and later.

## Check yourself

1. The vLLM log says max concurrency is 18× at 8k context. How do you double it? *(Use an FP8 KV cache, a lower `--max-model-len` or a smaller or quantized model.)*
2. When would you pick SGLang over vLLM? *(For heavy shared-prefix or branching agent workloads and structured-generation-heavy pipelines. Benchmark both on the real traffic.)*
3. Why containers only? *(CUDA, driver and engine versions have to match exactly. Containers pin them, and host pip installs break them.)*

## Explain what you learned

> "Mac for iteration, Spark for the server stack. It's the same harness pointed at both,
> so the numbers are comparable, and I validate the fabric before I scale across boxes."

**Next →** [15 · Capstone](../15-capstone/)
