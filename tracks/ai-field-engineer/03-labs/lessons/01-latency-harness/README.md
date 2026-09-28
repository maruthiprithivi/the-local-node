# 01 · The latency harness: TTFT and ITL, measured by you

> **Lab book:** Fireworks labs → **F1**  **Watch:** video 1 `01-inference-101.mp4`
> **Time:** 30 min  **Cost:** free locally · about $0.02 on Fireworks

## What and why

Every LLM request has two phases:

| phase | what the GPU does | what the user feels | metric |
|---|---|---|---|
| **prefill** | reads the whole prompt at once (compute-heavy) | "is it thinking?" | **TTFT**, time to first token |
| **decode** | writes one token at a time (memory-bandwidth-heavy) | "how fast does it type?" | **ITL**, inter-token latency |

Because the two phases have different bottlenecks, you always report them separately
and at **p50 and p95**. `bench_ttft.py` is the tool for that. You will point this same
script at Ollama, llama.cpp, MLX, Fireworks and the Spark.

## Read the code first

- `felab/measure.py → stream_once()` timestamps every streamed token. TTFT is the first stamp; ITL is the gaps between stamps.
- `bench_ttft.py → build_prompt()` pads the prompt to put the context first and the question last, which is the shape of a real RAG prompt.
- A warm-up call runs first and is never counted. Cold starts are a separate conversation.

## Run

```bash
cd lessons/01-latency-harness

# 01a — free
python bench_ttft.py --target mock
python bench_ttft.py --target mock --prompt-tokens 8000
python bench_ttft.py --target ollama
python bench_ttft.py --target ollama --prompt-tokens 8000

# 01b — Fireworks (≈ $0.01). Needs FIREWORKS_API_KEY in .env
bash compare_models.sh
```

## What you should see

```
target  model     prompt_tok  ttft_p50_ms  ttft_p95_ms  itl_ms  tok_per_s
------  --------  ----------  -----------  -----------  ------  ---------
ollama  llama3.1:8b       12        145.0        190.0    22.4       44.6
ollama  llama3.1:8b     8000      4,210.0      4,480.0    24.1       41.5   ← TTFT ×30, ITL ~same
```

Exact numbers depend on your chip. The **shape** is the lesson.

## Check yourself

1. The customer says "it's slow". Which number do you ask for first, and why? *(Both. Slow to start points at prefill, queueing or a long prompt. Slow to type points at decode, bandwidth or an oversized model.)*
2. Why p95 and not the average? *(Averages hide the tail, and the tail is what users complain about.)*
3. Why does ITL creep up a little with the long prompt? *(Each decode step also reads the KV cache, and a longer context means a bigger cache.)*

## Explain what you learned

> "I measure TTFT and ITL separately, at p50 and p95, on the customer's own prompt shape.
> One latency number hides two different bottlenecks."

**Next →** [02 · Three local servers](../02-three-local-servers/)
