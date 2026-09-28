# 17 · Full fine-tuning vs LoRA vs DoRA, on your Mac

> **Lab book:** Training labs → **T2**  **Watch:** videos 14 `14-full-finetuning.mp4`, 15 `15-sft.mp4`, 16 `16-peft.mp4`
> **Time:** about 1 h (three short training runs)  **Cost:** free

## What and why

Videos 14–16 make three claims. This lesson tests all three on a real model:

1. **Full fine-tuning costs about 16 bytes per parameter** to train, against about 2 to serve.
2. **LoRA and DoRA train under 1% of the weights** and land close to full fine-tuning on a narrow task.
3. **Full fine-tuning risks more forgetting**, meaning getting better at your task and worse at everything else.

You train **Qwen2.5-0.5B-Instruct** three ways on the same ticket data. Then you read
cost (memory, minutes, checkpoint size), gain (task accuracy) and damage (a general quiz)
from one table. The model is small enough that *full* fine-tuning fits on a 16 GB Mac.

## The files, in order

| step | file | runs on | does |
|---|---|---|---|
| 0 | `sft_data_check.py` | anywhere | checks the data: JSON, roles, ends-with-assistant, duplicates, **test leakage**, length, label balance |
| 1 | `peft_params.py` | anywhere | trainable parameters and training memory for full, LoRA, DoRA and QLoRA, from real model shapes |
| 2 | `run_variants.sh` | Mac | `mlx_lm.lora --fine-tune-type full / lora / dora`, same data and settings |
| 3 | `compare_variants.py` | Mac | one table: trainable %, peak memory, val loss, minutes, checkpoint MB, task accuracy, general quiz |

> This checker earned its place while the course was being built. On its first run it found that
> the synthetic dataset had 301 training tickets identical to test tickets, which would have
> inflated every fine-tune score. `data/make_tickets.py` now dedupes, keeps the splits disjoint
> and keeps one phrasing per category for the test set only.

## Run

```bash
cd lessons/17-full-vs-peft-mlx
python sft_data_check.py
python peft_params.py --model 0.5b          # what you are about to train
python peft_params.py --model 8b --rank 16  # the same maths at a size customers use
python peft_params.py --model 70b --rank 64 --mlp

bash run_variants.sh                        # ~15–45 min for all three
python compare_variants.py
```

Tight on memory? Run `VARIANTS="lora dora" bash run_variants.sh` and skip full. Short on
time? Use `ITERS=150`.

## What you should see (shape, not exact numbers)

```
variant              trainable_%  peak_mem_GB  val_loss  minutes  ckpt_MB  task_acc_%  general_quiz
base (no training)           0.0          nan       nan      0.0      0.0        ~40        ~9/12
full                       100.0        ~8–10     lowest     slowest   ~990       high     may drop
lora                        ~0.4         ~2–3      close      fast      ~9        high     ≈ base
dora                        ~0.45        ~3        close      a bit slower ~9     high     ≈ base
```

- **Peak memory:** full is several times LoRA's. That is claim 1.
- **Checkpoint:** about 1 GB for full against single-digit MB. That is why multi-LoRA serving works.
- **Task accuracy:** all three jump well above base, and LoRA and DoRA land close to full. That is claim 2. Look at the held-out phrasings too, since they test generalisation rather than memory.
- **General quiz:** if any variant drops, it is usually full. That is claim 3. On 12 questions it is a smoke alarm, not proof.

## Check yourself

1. Why must the base be bf16 here, and not the 4-bit model from lesson 11? *(Full fine-tuning updates the weights, and you can't train 4-bit weights directly. QLoRA only works because the base stays frozen.)*
2. `peft_params.py --model 8b` says LoRA needs about 16 GB, but full needs 128. Where does LoRA's 16 GB go? *(Almost all of it is the frozen bf16 base, 2 bytes × 8B. The adapter's optimizer state is tiny. Switch to QLoRA and it drops to about 5 GB.)*
3. Why is full fine-tuning's learning rate 10× smaller? *(Every weight moves, so a big step damages what the model already knows.)*

## Explain what you learned

> "I ran full, LoRA and DoRA on the same data. LoRA got within a couple of points of full at a
> fraction of the memory, with a 9 MB checkpoint instead of a gigabyte, and without denting
> general ability. For a narrow task, I start with LoRA and only go full when the eval gap is
> real."

**Next →** [18 · Preference tuning with DPO](../18-preference-dpo/)
