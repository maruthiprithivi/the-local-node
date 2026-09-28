# 12 · MoE vs dense on the bandwidth wall

> **Lab book:** Local labs → **L7** · Ceiling calculator (MoE rows)  **Watch:** video 7 `07-offloading.mp4`
> **Time:** 30 min  **Cost:** free (≈19 GB download)

## What and why

A **dense** model is one big team where everyone works on every token. A **Mixture of
Experts (MoE)** model is a large company with a receptionist, the *router*, who sends
each token to only 2–4 specialists out of dozens.

| | memory needed | speed depends on |
|---|---|---|
| dense 8B | all 8B | all 8B, read per token |
| MoE 21B total / 3.6B active | **all 21B** (every expert must be loaded) | **only ~3.6B**, read per token |

So MoE gives big-model quality at small-model decode speed, **if you have the memory**.
That is why DeepSeek, gpt-oss, Qwen3-MoE and others are built this way, and why unified
memory (Mac, DGX Spark) suits them well.

When the model does *not* fit, you have three options:
**offload** layers to CPU (slow, because PCIe or system RAM becomes the bottleneck),
**tensor parallel** (split every layer across GPUs; needs fast NVLink; lowers latency) or
**pipeline parallel** (give each GPU a block of layers; tolerates slower links; adds bubbles).

## Read the code first

- `moe_probe.py`: two lines of physics turn a stopwatch into an architecture estimate.
- `KNOWN` holds the published total and active sizes to check your estimate against.

## Run

```bash
cd lessons/12-moe-vs-dense
python moe_probe.py --demo                          # see the shape first
ollama pull llama3.1:8b && ollama pull gpt-oss:20b
python moe_probe.py llama3.1:8b gpt-oss:20b
# 64 GB+ Mac? also try:  ollama pull qwen3:30b-a3b
```

## What you should see

```
model        file_gb  tok_s  gb_per_token  active_%  published_%
llama3.1:8b      4.9   84.0           4.9      99.5        100.0
gpt-oss:20b     13.8  118.0           3.5      25.1         17.1
```

The MoE file is about 3× bigger and still faster. Your `active_%` will come out above
the published figure, because attention layers, embeddings and the KV cache are read on
every token too. Getting within 2× from a stopwatch is a good result.

## Check yourself

1. A customer asks why their 120B MoE is faster than their 70B dense. What do you say? *(About 5B active parameters against 70B read per token, so decode is bandwidth ÷ active bytes.)*
2. Why can MoE be *harder* to serve at high concurrency on GPUs? *(Different tokens hit different experts, so batches fragment. Expert parallelism across GPUs and all-to-all traffic also add complexity.)*
3. The model needs 160 GB and each H100 has 80 GB. TP=2 or PP=2? *(TP=2 inside one NVLink node for latency. PP only if the link between GPUs is slow.)*

## Explain what you learned

> "Memory is set by total parameters; decode speed by active parameters. I can estimate a
> model's active footprint from its decode speed on known hardware."

**Next →** [13 · Speculative decoding](../13-speculative-decoding/)
