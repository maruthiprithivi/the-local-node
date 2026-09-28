# 15 · Capstone: from measurements to a customer recommendation

> **Lab book:** Capstone section · Cost calculators · Talk tracks  **Watch:** video 8 `08-platform.mp4`
> **Time:** 2 h  **Cost:** free

## What and why

A Field Engineer is paid for the **recommendation**, not the benchmark. This lesson
turns every CSV in `results/` into the document you would send after a discovery call,
and a ten-minute talk you can give to the customer's team.

`build_memo.py` reads lessons 01–13 and writes `results/SIZING_MEMO.md` with:
needs → latency profile → capacity and replicas → levers (caching, schema, batch,
LoRA, speculation) → three cost options and the **serverless-versus-dedicated crossover**
→ recommendation → risks. Anything you haven't measured shows up as **TODO** rather
than an invented number.

## Run

```bash
cd lessons/15-capstone
python build_memo.py
python build_memo.py --peak-concurrency 200 --tickets-per-month 5e6 --slo-ms 800 \
                     --serverless-in 0.15 --serverless-out 0.60 --gpu-hour 8   # your scenario, current prices
open ../../results/SIZING_MEMO.md
```

## The 10-minute presentation (5 slides)

1. **The customer's problem, in their numbers:** peak concurrency, SLO, volume, format needs.
2. **What I measured:** the lesson 03 concurrency curve with the SLO line, plus the lesson 01 TTFT/ITL table.
3. **Three levers:** prefix caching (lesson 06), schema-constrained output (lesson 07) and a fine-tune (lessons 09–11), each with *your* before/after.
4. **Cost options:** serverless, serverless with caching, dedicated, and where they cross over.
5. **Recommendation, risks and the next two weeks of a proof of concept.**

## Drill: answer each in about 20 seconds

| they ask | your answer uses |
|---|---|
| "Why is our TTFT high but typing speed fine?" | prefill vs decode, prompt length, queueing (01, 03) |
| "Can we run a 70B on one GPU?" | weights + KV maths, quantization, TP (04, 05, 12) |
| "Serverless or dedicated?" | the crossover table, SLO, LoRA needs (15) |
| "Is fine-tuning worth it?" | the eval table: quality, p95 and $/1k (09–11) |
| "Why is the MoE faster than the smaller dense model?" | active vs total params (12) |
| "Will speculative decoding help us?" | acceptance on their traffic (13) |
| "Our agent bill is too high." | stable-first prompts, cached tokens, batch for evals (06, 08) |

## Explain what you learned

> "I'd start with their traffic shape and SLO, measure a concurrency curve on the
> candidate model, apply the cheap levers first (caching and structured output), and
> only then decide between serverless and dedicated, with the crossover point written
> down."

**Next →** the training track: [16 · Training methods in miniature](../16-training-toy/) (videos 14–18)
