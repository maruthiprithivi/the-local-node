# Field Engineer Labs

**Hands-on inference engineering, from a MacBook to a DGX Spark to Fireworks AI.**
Nineteen short lessons: sixteen that take you from "what is TTFT?" to a customer sizing
memo built entirely from numbers you measured yourself, then three on **how models are
trained**: full fine-tuning, SFT, LoRA and its family, RLHF and DPO.

Built to practise the work of an **AI Engineer or Field Engineer**. Every
lesson ends with a short explanation you could give to a customer or teammate.

```
 ┌──────────────────┐     ┌────────────────────────┐     ┌─────────────────────────┐
 │  1. WATCH        │ ──▶ │  2. READ               │ ──▶ │  3. RUN                 │
 │  18 narrated     │     │  Lab book web page     │     │  this repo              │
 │  explainer videos│     │  concepts, calculators,│     │  lessons/NN-*/          │
 │  (3–4 min each)  │     │  cards F1–7 L1–9 T1–3  │     │  README → code → results│
 └──────────────────┘     └────────────────────────┘     └─────────────────────────┘
          the WHY                 the WHAT                      the HOW (your numbers)
```

The **lab book** is the map. Open [`lab-book.html`](lab-book.html) in a browser (one
offline file) or use the hosted copy. It explains each concept, has the calculators, and
each lab card names its folder here. **This repo** is the territory: commented code you
run in order, which writes its measurements to `results/`. Keep them side by side, with the
page on the left and the terminal on the right.

---

> **Got this inside the Field Engineer Kit?** The videos are in `../01-videos/` (numbered
> `01-…` to `18-…`, the same numbers each lesson's "Watch:" line uses) and the lab book is
> `../02-lab-book/field-engineer-lab-book.html`. Start with `../README.md`.

## Quick start (10 minutes, no model download)

```bash
git clone <this repo> field-engineer-labs && cd field-engineer-labs
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e .     # Linux: drop mlx-lm from requirements
cp .env.example .env

make mock &            # a fake LLM server with realistic latency behaviour, on :9000
make smoke             # runs every lesson offline, about 2 minutes
```

Once the smoke test passes, run `bash lessons/00-setup/setup_mac.sh` for the real local
stack and start at lesson 00.

## The lessons

Each folder has a `README.md` (what, why, run, expected output, self-check, concise
explanation) and numbered or commented scripts. Work through them in order, because later
lessons reuse earlier tools.

| # | lesson | lab book | video | runs on | time | cost |
|---|---|---|---|---|---|---|
| 00 | [Setup and guardrails](lessons/00-setup/) | L1 | serving-stack | Mac | 15 m | free |
| 01 | [Latency harness: TTFT and ITL](lessons/01-latency-harness/) | F1 | inference-101 | Mac → FW | 30 m | ~$0.02 |
| 02 | [Three local servers](lessons/02-three-local-servers/) | L2 | serving-stack | Mac | 30 m | free |
| 03 | [Concurrency sweep](lessons/03-concurrency-sweep/) | L3 | benchmarking, batching | Mac | 45 m | free |
| 04 | [Quantization](lessons/04-quantization/) | L4 | quantization, gpu-bandwidth | Mac | 45 m | free |
| 05 | [KV cache and context](lessons/05-kv-cache/) | L5 | kv-cache | Mac | 45 m | free |
| 06 | [Prefix caching](lessons/06-prefix-caching/) | L6 + F2 | prefix-caching | Mac → FW | 30 m | ~$0.03 |
| 07 | [Structured output](lessons/07-structured-output/) | F3 | platform | Mac → FW | 30 m | ~$0.02 |
| 08 | [Batch API](lessons/08-batch-api/) | F4 | platform | FW | 20 m | <$0.01 |
| 09 | [Eval harness](lessons/09-eval-harness/) | F6 | training | Mac → FW | 1 h | ~$0.10 |
| 10 | [LoRA on Fireworks](lessons/10-lora-fireworks/) | F5 | training, qlora | FW | 2 h | **~1 GPU-hour** |
| 11 | [LoRA on the Mac (QLoRA)](lessons/11-lora-local-mlx/) | L8 | qlora | Mac | 1–2 h | free |
| 12 | [MoE vs dense](lessons/12-moe-vs-dense/) | L7 | offloading | Mac | 30 m | free |
| 13 | [Speculative decoding](lessons/13-speculative-decoding/) | F7 | scale-out, batching | Mac → FW | 45 m | ~½ GPU-hour |
| 14 | [The Spark track](lessons/14-spark-track/) | L9 | serving-stack, scale-out | Spark | 2–3 h | free |
| 15 | [Capstone: sizing memo](lessons/15-capstone/) | Capstone | platform | Mac | 2 h | free |
| | **Training track** (after the capstone, or alongside lessons 09–11) | | | | | |
| 16 | [Training methods in miniature](lessons/16-training-toy/) | T1 | full-finetuning, peft, rlhf, dpo | anywhere | 30 m | free |
| 17 | [Full vs LoRA vs DoRA on your Mac](lessons/17-full-vs-peft-mlx/) | T2 | full-finetuning, sft, peft | Mac | 1 h | free |
| 18 | [Preference tuning with DPO](lessons/18-preference-dpo/) | T3 | rlhf, dpo | Mac → FW | 1 h | free / optional |

**The 10-day plan** in the lab book maps onto these lessons: day 1 → 00–01, day 2 → 02,
day 3 → 03, day 4 → 04–05, day 5 → 06, day 6 → 07–08, day 7 → 09–10, day 8 → 11,
day 9 → 12–14, day 10 → 15. The training track (16–18, videos 14–18) adds two
more days: day 11 → 16–17, day 12 → 18.

## One harness, every backend

Every script takes `--target`, so the same code measures every server and the numbers
stay comparable:

| `--target` | what | start it with |
|---|---|---|
| `mock` | offline fake LLM (latency, batching, prefix cache, JSON behaviour) | `make mock` |
| `ollama` | Ollama, :11434 | `ollama serve` |
| `llamacpp` | llama.cpp `llama-server`, :8080 | `lessons/02-*/serve_llamacpp.sh` |
| `mlx` | `mlx_lm.server`, :8081 | `lessons/02-*/serve_mlx.sh` |
| `fireworks` | Fireworks serverless or your deployment (**paid**) | `FIREWORKS_API_KEY` in `.env` |
| `spark` | vLLM or SGLang on a DGX Spark | `lessons/14-*/1_vllm.sh` |

Override with `--model` and `--base-url`, or set defaults in `.env`.

## Repository layout

```
felab/                 shared toolkit every lesson imports
  targets.py           the --target table; loads .env
  measure.py           stream_once(): TTFT and ITL per token; percentiles
  results.py           record() → results/<lesson>.csv; table()
  tickets.py           dataset loader and graders (parse / schema-valid / correct)
  hardware.py          chip, RAM and bandwidth detection; the decode-ceiling formula
  mock_server.py       offline OpenAI-compatible server that behaves like the real thing
data/
  make_tickets.py      builds the shared triage dataset (800 train / 100 valid / 100 test;
                       de-duplicated, disjoint splits, 30 test tickets in unseen phrasings)
  triage_schema.json   the JSON contract used in lessons 07–11
lessons/NN-*/          README.md + commented scripts, in course order
results/               your measurements (git-ignored), read by the capstone
scripts/smoke_test.sh  every offline lesson in about 2 minutes (also runs in CI)
```

## Spending on Fireworks: the rules

The whole course costs **well under $15** if you follow these rules:

1. **Serverless is per token and costs cents. Dedicated deployments bill per GPU-hour from the moment they are created**, whether or not you send a request.
2. Only lessons **10**, **13** and (optionally) **18** create deployments. Lesson 10 ends with `5_teardown.sh`, and lesson 13 deletes its deployment automatically on exit, even after Ctrl-C.
3. Set a budget or alert in the Fireworks console before you start. Run `make fw-check` at the end of every session: it lists anything still billing.
4. Rehearse every paid lesson against `--target mock` first.

## Troubleshooting

| symptom | fix |
|---|---|
| `Connection refused` | That server isn't running. `make check` shows what is up. |
| `FIREWORKS_API_KEY is not set` | Put it in `.env` (never commit it). |
| model id not found on Fireworks | Ids change. Copy a current one from the model library and pass `--model`. |
| llama.cpp refuses a quantized V cache | Add flash attention: `EXTRA="-fa on" bash context_ladder.sh` |
| MLX out of memory while training | Use `--batch-size 1`, lower `--num-layers`, or a smaller base model. |
| a container tag isn't found on the Spark | Tags move. See the links in `lessons/14-*/1_vllm.sh` and `3_sglang.sh`. |

Commands and flags follow the vendors' docs as of September 2026. When a flag has moved,
`<tool> --help` is the source of truth.

## Licence

MIT. Model weights you download keep their own licences.
