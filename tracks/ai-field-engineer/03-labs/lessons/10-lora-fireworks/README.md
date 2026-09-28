# 10 · A real LoRA fine-tune on Fireworks, start to teardown

> **Lab book:** Fireworks labs → **F5** · Fine-tune cost calculator  **Watch:** video 6 `06-training.mp4`, video 12 `12-qlora.mp4`
> **Time:** about 2 h (mostly waiting)  **Cost:** training costs cents; serving is **~1 h of a dedicated GPU** (check the rate)

## What and why

**LoRA** leaves the big model frozen and trains a small "clip-on" adapter, often under
1% of the weights, on your examples. It is cheap to train and small to store, and it
teaches *format and behaviour* well (our triage JSON), while teaching new *facts* poorly
(use RAG for those).

The lesson that matters for a Solutions Architect: **training is the cheap part.**

```
train     800 examples × 2 epochs        ≈ cents            (per training token)
serve     dedicated deployment           ≈ $ per GPU-hour   ← the real cost
share     multi-LoRA: many adapters on one deployment → the cost-sharing answer
```

## The five steps

| script | does | billing |
|---|---|---|
| `1_train.sh` | upload `data/tickets/train.jsonl`, start the SFT job (rank 8, 2 epochs) | per training token |
| `2_wait.sh` | poll until COMPLETED | – |
| `3_deploy.sh` | create a dedicated deployment and wait for READY | **⏱ clock starts** |
| `4_eval.sh` | lesson 09's harness: base vs fine-tune, same 60 held-out tickets | per request |
| `5_teardown.sh` | delete, then prove `deployment list` is empty | **⏱ clock stops** |

The ids are kept in `.state` between steps, so you can close the terminal after step 1.

## Run

```bash
cd lessons/10-lora-fireworks
bash ../00-setup/fireworks_guardrails.sh     # nothing running? good
bash 1_train.sh
bash 2_wait.sh
bash 3_deploy.sh                             # ⏱
bash 4_eval.sh
bash 5_teardown.sh                           # ⏱ stop — do not skip
```

The default `BASE_MODEL` is a 7B instruct model. Check it appears in Fireworks' list of
tunable models and override it if needed: `BASE_MODEL=accounts/fireworks/models/<id> bash 1_train.sh`.

## What you should see

```
candidate                         schema_valid_%  category_%  severity_%  p95_ms
fireworks qwen2p5-7b-instruct             100.0        80.0        70.0   420
fireworks triage-lora-…#…                 100.0        97.0        95.0   380
▸ deleted after 38 min (≈ $5.07 serving + a few cents of training)
```

## Check yourself

1. The customer wants 12 fine-tunes, one per business unit. How do you keep serving costs sane? *(Multi-LoRA: one base deployment with 12 adapters, loaded per request.)*
2. The fine-tune gains 17 points of accuracy. When would you still say no? *(When a prompt change or few-shot examples close most of the gap, or when traffic is too low to justify a dedicated deployment.)*
3. The loss is falling but eval accuracy is flat. What does that mean? *(The model is memorising. Use fewer epochs, more varied data, or a lower rank.)*

## Explain what you learned

> "Training was about a dollar. The thing to plan is serving: a LoRA needs dedicated
> capacity, so we either share it with multi-LoRA or justify it with volume."

**Next →** [11 · The same LoRA on your Mac](../11-lora-local-mlx/) · **Go deeper:** the training track, lessons 16–18 (videos 14–18)
