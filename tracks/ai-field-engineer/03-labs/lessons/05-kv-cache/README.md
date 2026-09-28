# 05 · KV cache and context length

> **Lab book:** Local labs → **L5**  **Watch:** video 2 `02-kv-cache.mp4`
> **Time:** 45 min  **Cost:** free

## What and why

While a model writes, it keeps notes on every token it has seen so far (the **K**eys
and **V**alues), so it doesn't reread the whole conversation for each new word. Those
notes are the **KV cache**. They grow with every token and every user:

```
KV bytes/token = 2 × layers × kv_heads × head_dim × bytes
Llama-3.1-8B   = 2 × 32 × 8 × 128 × 2 B = 128 KiB per token
× 131,072 tokens                          ≈ 17 GB for ONE long conversation
```

The weights are 4.9 GB. **The cache, not the model, is what runs out.** It is the most
common production failure and the easiest to fix:

1. **Cap the context** to what the use case needs. A 4k support chat doesn't need a 128k window.
2. **Quantize the cache** (FP8 or Q8), which roughly halves it and doubles how many users fit.
3. **PagedAttention** (vLLM) allocates cache in small pages instead of one worst-case block per user, so less goes to waste.

## Read the code first

- `kv_calc.py` has the formula, with model shapes taken from `config.json`.
- `context_ladder.sh` starts the server six times and greps the allocation line from the log.

## Run

```bash
cd lessons/05-kv-cache
python kv_calc.py
python kv_calc.py --ctx 131072
python kv_calc.py --ctx 32768 --free-gb 20            # how many users fit in 20 GB?
bash context_ladder.sh                                # the real allocations
```

## What you should see

```
ctx      cache  what llama.cpp allocated
4096     f16    512.00 MiB
4096     q8_0   272.00 MiB
32768    f16    4096.00 MiB
32768    q8_0   2176.00 MiB
131072   f16    16384.00 MiB   (or ✗ on a small Mac — the lesson)
131072   q8_0   8704.00 MiB    ← the fix
```

`kv_calc.py --ctx 131072` predicts 17.18 GB, which is 16,384 MiB. The log agrees.

## Check yourself

1. Why do GQA models (8 KV heads instead of 32) matter so much here? *(The cache is 4× smaller. That architecture choice is what makes long context affordable.)*
2. The customer's p95 prompt is 3k tokens but they configured 128k "to be safe". What does that cost? *(Engines that reserve the maximum per slot strand memory. Capping at about 8k frees it for more concurrent users.)*
3. What does FP8 KV cost you? *(A small quality risk on some tasks. Check it with the eval harness in lesson 09.)*

## Explain what you learned

> "Weights fit; the cache doesn't. I size KV per token from the config, cap context to the
> real p95, and quantize the cache. That usually doubles concurrency on the same GPU."

**Next →** [06 · Prefix caching](../06-prefix-caching/)
