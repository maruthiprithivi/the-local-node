# 11 · The same LoRA on your Mac with MLX (QLoRA)

> **Lab book:** Local labs → **L8**  **Watch:** video 12 `12-qlora.mp4`
> **Time:** 1–2 h  **Cost:** free

## What and why

This is the same dataset and task as lesson 10, trained locally. Because the base model is
already **4-bit**, what you are running is **QLoRA**: frozen 4-bit weights plus small
trainable adapters. It is a heavy textbook you can't write in (the base) with a pad of
sticky notes you *can* write on (the adapter).

```
full fine-tune  7B  ≈ 120 GB   weights + gradients + optimizer for every parameter
QLoRA           7B  ≈   6 GB   4-bit frozen base + gradients only for ~2M adapter params
adapter file        ≈   4 MB   ← what you ship, version, and hot-swap (multi-LoRA)
```

Doing it both ways gives you the **build-versus-buy** story with your own numbers.

## Read the code first

- `qlora_memory.py` is the memory budget above. Change `--params` and `--rank` and see what moves.
- `1_train_mlx.sh` explains every flag in a comment. Watch *validation* loss, not training loss.
- `2_fuse_and_serve.sh` shows the choice between keeping the adapter separate (the multi-LoRA pattern) and fusing it in (simplest to hand over).
- `COMPARISON.md` is the page you fill in to explain your local-versus-managed recommendation.

## Run

```bash
cd lessons/11-lora-local-mlx
python qlora_memory.py
bash 1_train_mlx.sh              # 15–40 min; Ctrl-C when val loss flattens
bash 2_fuse_and_serve.sh         # leave running
bash 3_eval_local.sh             # other terminal
# then fill in COMPARISON.md
```

## What you should see

```
Iter 50:  Val loss 0.412
Iter 100: Val loss 0.198
Iter 300: Val loss 0.121        ← flattening: more iterations would memorise
▸ adapter saved: 7.1M

candidate                         category_%  severity_%
mlx …/fused                             96.0        94.0
mlx Qwen2.5-7B-Instruct-4bit            78.0        66.0
```

## Check yourself

1. Why do we evaluate on `test.jsonl` and not `valid.jsonl`? *(Validation loss guided when to stop, so it has leaked into the decision. Test is untouched.)*
2. When would you tell a customer to fine-tune locally or on their own GPUs? *(When data can't leave their environment, or for fast iteration before a managed production run.)*
3. The adapter is 7 MB. Why does that matter for serving? *(One base model can hold hundreds of adapters in memory, which makes per-tenant fine-tunes affordable.)*

## Explain what you learned

> "I ran the same LoRA locally and managed. Local is free and private; managed got me to a
> scalable endpoint in minutes. The adapter is a few megabytes, so multi-LoRA makes
> per-customer tuning economical."

**Next →** [12 · MoE vs dense](../12-moe-vs-dense/) · **Go deeper:** [17 · full vs LoRA vs DoRA](../17-full-vs-peft-mlx/) and [18 · DPO](../18-preference-dpo/) (videos 14–18)
