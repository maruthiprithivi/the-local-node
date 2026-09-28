# 03 · Concurrency sweep: the curve that sizes a deployment

> **Lab book:** Local labs → **L3**  **Watch:** video 10 `10-benchmarking.mp4`, video 5 `05-batching.mp4`
> **Time:** 45 min  **Cost:** free

## What and why

A GPU decode step reads all the weights once, whether it serves 1 user or 16.
**Batching** lets many users share that one read, so total throughput climbs almost
for free. Then the batch slots fill up, new requests wait in a queue, and **TTFT
p95 shoots up**. The last concurrency level *before* that knee is the capacity of one
replica. Divide the customer's peak traffic by it and you have a replica count.

```
 tok/s ▲        ________ aggregate (flattens: slots full)
       │      /
       │    /                      ╱ TTFT p95 (the knee = queueing)
       │  /    ─────────────────── ╱ ─ ─ SLO
       └──────────────────────────────▶ concurrent users
            1   2   4   8   16  32
```

**Goodput** counts only the requests that met the SLO. That is the number to sell,
not raw tokens per second.

## Read the code first

- `sweep.py → run_level()` shows that an `asyncio.Semaphore(conc)` *is* the concurrency level.
- Prompts are unique, so the prefix cache can't inflate the numbers.
- `plot_sweep.py` puts both curves on one chart and draws the SLO line.

## Run

```bash
cd lessons/03-concurrency-sweep
python sweep.py --target mock --slo-ms 500        # mock has 8 slots → knee after C=8
python plot_sweep.py && open ../../results/03-sweep.png

# real: restart llama.cpp with 8 slots (context split across them)
bash ../02-three-local-servers/serve_llamacpp.sh Q4_K_M 16384 8
python sweep.py --target llamacpp --levels 1,2,4,8,16
python plot_sweep.py
```

## What you should see (mock)

```
conc  agg_tok_s  user_tok_s  ttft_p50  ttft_p95  goodput_rps
   1       54.1        54.9      25.4      27.4          0.5
   8      275.1        38.9      26.3      41.4          2.5   ← 5× throughput, still fast
  16      294.3        38.9   2,776.3   3,357.0          0.4   ← slots full: queueing
Capacity line: TTFT p95 ≤ 500 ms holds up to C=8 concurrent users on this replica.
```

## Check yourself

1. Throughput went up 5×, but per-user speed only dropped from 55 to 39 tok/s. Why so cheap? *(Decode is memory-bound, so sharing one weight read across 8 users costs little extra.)*
2. Peak traffic is 120 concurrent users and one replica handles 8 within SLO. How many replicas? *(15, plus headroom. Say 18.)*
3. What changes the knee? *(More slots or memory for KV cache, a smaller or quantized model, shorter contexts, and prefill/decode interference.)*

## Explain what you learned

> "Single-stream numbers sell hardware; concurrency curves size deployments. I sweep,
> find the highest concurrency that holds p95 TTFT under the SLO, and size replicas from
> peak traffic divided by that."

**Next →** [04 · Quantization](../04-quantization/)
