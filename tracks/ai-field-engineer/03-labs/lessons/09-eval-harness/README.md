# 09 · Eval harness: quality, latency and cost in one table

> **Lab book:** Fireworks labs → **F6**  **Watch:** video 6 `06-training.mp4` (the "how do you know it worked" part)
> **Time:** 1 h  **Cost:** free locally · about $0.10 with a Fireworks judge

## What and why

Every customer conversation about models ends in a trade-off, and the table is how
you have it:

| candidate | valid | accuracy | judge | p95 | $/1k tasks |
|---|---|---|---|---|---|
| big general model | 100% | 81% | 3.9 | 640 ms | $0.42 |
| small fine-tune | 100% | 96% | 4.5 | 310 ms | $0.02 |

Never show one column alone. Better quality at 3× the latency may be the wrong call for a
chat product and the right one for batch.

**Graders, cheapest first:**
1. **Code checks**: schema validity, exact-match labels. They are free, deterministic and the first to run.
2. **LLM judge**: a second model scores the fuzzy field (`next_action`) against a rubric. It is useful but biased, so hand-check about 20 of its scores before you trust it.
3. **Humans** check a sample, especially before launch.

Always evaluate on **held-out** data (`test.jsonl` is never trained on). Otherwise you are
grading the student on the answer key.

## Read the code first

- `evaluate.py → parse_candidate()` lets any target, model and price enter the same table.
- `RUBRIC` is the judge prompt. Change it and watch the scores move, which shows why judges need calibrating.
- `usd_per_1k` comes from real token counts (`usage`) × prices you supply.

## Run

```bash
cd lessons/09-eval-harness
python evaluate.py mock:mock-8b mock:mock-8b-lora --n 60 --judge mock    # offline rehearsal

# base models you will fine-tune against in 10/11
python evaluate.py ollama mlx --n 50
python evaluate.py "fireworks:accounts/fireworks/models/gpt-oss-20b@0.07/0.30" --n 50 --judge fireworks
```

Prices are examples. Copy the current ones from the model's page on fireworks.ai.

Optional: `pip install eval-protocol` and port one grader to Fireworks' own eval
framework, so you can talk about their tooling from experience.

## What you should see (mock)

```
candidate          schema_valid_%  category_%  severity_%  judge_1to5  p95_ms  usd_per_1k
mock mock-8b                100.0        75.0        77.5         3.9   407.4         0.0
mock mock-8b-lora           100.0        92.5        97.5         4.5   404.0       0.015
```

Write down your **base** model's row. It is the number the fine-tunes in lessons 10 and 11 have to beat.

## Check yourself

1. The judge gives the fine-tune 4.5 and the base 3.9. Is that proof? *(No. Check that the judge agrees with you on a hand-labelled sample first. Judges favour length and style.)*
2. Accuracy went up 17 points but p95 doubled. What do you recommend? *(It depends on the SLO. Put both in the memo, and consider a smaller base model or speculative decoding.)*

## Explain what you learned

> "Benchmarks are for launches. For a customer I use three graders on their data and one
> table: quality, p95 latency and dollars per thousand tasks."

**Next →** [10 · LoRA on Fireworks](../10-lora-fireworks/)
