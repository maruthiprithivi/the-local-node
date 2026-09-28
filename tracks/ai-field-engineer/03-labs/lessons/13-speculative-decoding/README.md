# 13 · Speculative decoding, measured

> **Lab book:** Fireworks labs → **F7**  **Watch:** video 13 `13-scale-out.mp4`, video 5 `05-batching.mp4` (speculation part)
> **Time:** 45 min  **Cost:** free locally · about 30–45 min of one deployment on Fireworks

## What and why

Decode is slow because the big model writes one token per pass. **Speculative decoding**
has a small, fast *draft* model guess the next k tokens, and the big model *checks all k in
one pass*. Checking is parallel, like prefill, so it is cheap. Every guess it accepts is a
free token. Every miss costs a little wasted drafting.

It is an intern drafting an email while the senior engineer approves or corrects it word
by word. It is fast when the intern is predictable, and slower than no intern when they aren't.

```
E (tokens per big-model pass) = (1 − α^(k+1)) / (1 − α)      α = acceptance rate
α 0.8, k 4 → 3.4 tokens per pass → ~2.4× faster
α 0.3, k 8 → ~0.8× → SLOWER
```

**Structured output** (JSON, code, extraction) has high α. **Creative prose** has low α.
Always measure α on the customer's own traffic.

## Read the code first

- `spec_math.py` builds the α × k table. Find the ↓ cells.
- `serve_spec_llamacpp.sh` needs a draft with the *same tokenizer* as the target, because the ids are compared directly.
- `spec_bench.py` compares the two traffic types and reads `timings.draft_n_accepted` (llama.cpp) or `perf_metrics` (Fireworks).
- `fireworks_spec.sh` sets a `trap … EXIT` so the deployment is deleted even if you press Ctrl-C.

## Run

```bash
cd lessons/13-speculative-decoding
python spec_math.py

bash serve_spec_llamacpp.sh off &   sleep 30
python spec_bench.py --target llamacpp --label baseline;  kill %1
bash serve_spec_llamacpp.sh &       sleep 40
python spec_bench.py --target llamacpp --label spec;      kill %1

bash fireworks_spec.sh          # ⏱ deploy → measure → auto-delete
```

## What you should see

```
label     traffic     tok_s   alpha
baseline  structured   62.0     nan
baseline  prose        61.5     nan
spec      structured  118.0   0.780    ← ~1.9×
spec      prose        70.0   0.410    ← small gain; could be a loss with bigger k
```

## Check yourself

1. Why must the draft share the tokenizer? *(The target verifies token ids, not text.)*
2. Why does speculation help less at high concurrency? *(With a full batch the GPU is already busy, so spare compute for verification shrinks. It shines on latency-bound, low-batch workloads.)*
3. What is the zero-model alternative for editing tasks? *(N-gram speculation or Fireworks predicted outputs: the draft comes from the prompt itself.)*

## Explain what you learned

> "Acceptance rate decides whether speculation pays. On structured traffic it can double
> decode speed; a generic drafter on unusual traffic can make things slower. I measure α
> on their prompts before recommending it."

**Next →** [14 · The Spark track](../14-spark-track/)
