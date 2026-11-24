# Server log excerpts

Verbatim lines from the 14 Nov 2026 server logs behind the claims in README.md. Container log times are UTC (add 8 h for UTC+8). Full logs are not published.

## vLLM: attention block size

```
(EngineCore pid=254) INFO 11-14 11:36:42 [interface.py:1051] Setting attention block size to 528 tokens to ensure that attention page size is >= mamba page size.
(EngineCore pid=254) INFO 11-14 11:38:10 [kv_cache_utils.py:753] kv lcm block sizes 528
```

## vLLM: model dtype (engine config, excerpt)

```
trust_remote_code=False, dtype=torch.bfloat16, max_seq_len=8192
```

## SGLang: BF16 KV cache (attempt 2)

```
[2026-11-14 11:53:12] KV Cache is allocated. dtype: torch.bfloat16, #tokens: 8192, K size: 0.13 GB, V size: 0.13 GB
```

## SGLang: attempt 1 failure (--mem-fraction-static 0.15, no mamba cap)

```
RuntimeError: Not enough GPU memory for hybrid (mamba/linear-attention) state cache. Computed max_mamba_cache_size=-28 (total_rest_memory=-2.66 GB, mamba_cache_per_req=49.12 MB)
```

## Ollama: version, imported model, llama-server flags

```
ollama version is 0.40.13
    architecture        qwen35
    parameters          4.3B
    quantization        BF16
    num_ctx    8192
cmd="/usr/lib/ollama/llama-server --model /root/.ollama/models/blobs/sha256-4ba990ad6736f2b07691fa5cf9836c4b0eb26498ecdd646c1e76ba597c99ec9f --port 42665 --host 127.0.0.1 --no-webui --offline -c 8192 -np 1 --log-verbosity 4 --no-log-prefix --no-log-timestamps --load-mode dio --cache-type-k f16 --cache-type-v f16
```

## Ollama: CUDA library selection on GB10

```
msg="skipping CUDA device — compute capability not in compiled architectures" device="NVIDIA GB10" cc=1210
```

The cuda_v12 library skipped the GB10 (compute capability 12.1). Discovery then used cuda_v13:

```
msg="bootstrap discovery took" duration=1.328367393s OLLAMA_LIBRARY_PATH="[/usr/lib/ollama /usr/lib/ollama/cuda_v13]"
```
