# 02 · Serve the same model three ways

> **Lab book:** Local labs → **L2**  **Watch:** video 9 `09-serving-stack.mp4`
> **Time:** 30 min  **Cost:** free

## What and why

An **inference server** turns a model file into an API. It owns the GPU memory,
batches users together, manages the KV cache and streams tokens back. The three you
can run on a Mac sit at different points on the convenience-versus-control line:

| server | analogy | you control | port |
|---|---|---|---|
| **Ollama** | automatic car | almost nothing — sensible defaults | 11434 |
| **llama.cpp** (`llama-server`) | manual gearbox | context, slots, quant, cache type, offload | 8080 |
| **MLX** (`mlx_lm.server`) | Apple's own engine | model and quant; plus local fine-tuning | 8081 |

vLLM and SGLang are the production equivalents. They need an NVIDIA GPU, so they
appear in lesson 14 on the Spark. All five speak the same OpenAI API, which is why
one harness works everywhere.

## Read the code first

- `serve_llamacpp.sh` has one comment per flag. Each flag is a concept from a later lesson.
- `felab/targets.py` lists every backend in a single table.

## Run

```bash
cd lessons/02-three-local-servers
# terminal 1
ollama serve
# terminal 2
bash serve_llamacpp.sh Q4_K_M 8192 4
# terminal 3
bash serve_mlx.sh
# terminal 4
bash compare_backends.sh
```

## What you should see

The same 8B 4-bit model, three rows. MLX is usually fastest on decode. llama.cpp and
Ollama are close, because Ollama *is* llama.cpp underneath. If Ollama is noticeably
slower, it is usually running a different quant or a smaller context by default. Run
`ollama show llama3.1:8b` to check.

## Check yourself

1. Why is `--parallel 4 -c 8192` a trap? *(llama.cpp splits the context across slots, so each user gets only 2,048 tokens.)*
2. A customer runs Ollama in production. What would you ask about? *(Concurrency, batching limits, observability, and whether vLLM or SGLang would suit multi-user traffic better.)*

## Explain what you learned

> "Ollama is llama.cpp with the flags hidden. For a customer workload I want the flags,
> and for multi-user GPU serving I want vLLM or SGLang."

**Next →** [03 · Concurrency sweep](../03-concurrency-sweep/)
