# 08 · Batch API: evaluations at half price

> **Lab book:** Fireworks labs → **F4**  **Watch:** video 8 `08-platform.mp4` (capacity modes)
> **Time:** 20 min  **Cost:** 50% of serverless, which comes to fractions of a cent here

## What and why

Not every request needs an answer in 300 ms. Evals, back-fills, nightly classification
and synthetic data can all wait an hour. The **Batch API** takes a file of requests,
runs them when capacity is free and charges about **half** the serverless price. Prompt
caching discounts stack on top.

It is the difference between a courier and the regular post: same letter, different
urgency, different price.

```
interactive  → serverless / dedicated     pay for latency
bulk         → batch                      pay ~50%, get results in minutes to hours
```

## Read the code first

- `make_batch.py`: one JSON line per request, `{"custom_id", "body"}`. The body is the normal chat-completions request.
- `submit_batch.sh`: upload the dataset, create the job, poll, then download.
- `score_batch.py → find_content()` joins results back to labels by `custom_id`, because results may come back in any order.

## Run

```bash
cd lessons/08-batch-api
python make_batch.py
python score_batch.py --simulate --target mock      # rehearse the whole loop offline

bash submit_batch.sh accounts/fireworks/models/gpt-oss-20b
firectl dataset download <OUTPUT_DATASET_ID>
python score_batch.py <downloaded>.jsonl
```

## What you should see

```
file                     answered  of   schema_valid_%  category_acc_%  severity_acc_%
simulated_results.jsonl       100  100           100.0            78.0            79.0
```

That is the base model's score on the held-out set. Lessons 10 and 11 try to beat it.

## Check yourself

1. Which customer workloads would you move to batch? *(Anything where no user is waiting: evals, embeddings back-fills, document classification, synthetic data.)*
2. Why `custom_id`? *(Results aren't ordered, and some requests may fail and land in the error file.)*

## Explain what you learned

> "Evaluation is batch work. At half price you can afford to evaluate every prompt or
> model change, not just the big ones."

**Next →** [09 · Eval harness](../09-eval-harness/)
