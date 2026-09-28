# 16 · Training methods, in miniature

> **Lab book:** Training labs → **T1**  **Watch:** videos 14 `14-full-finetuning.mp4`, 16 `16-peft.mp4`, 17 `17-rlhf.mp4`, 18 `18-dpo.mp4`
> **Time:** 30 min  **Cost:** free, pure numpy, runs anywhere in seconds

## What and why

Real training runs take minutes to hours, which makes it hard to *see* what an algorithm does.
These two scripts shrink the problem until every number fits on one screen, while keeping
the real algorithms intact.

| script | shrinks | lets you see |
|---|---|---|
| `toy_finetune.py` | a model → one 64×64 layer | full fine-tuning vs LoRA ranks: trainable parameters, optimizer memory, held-out error as the data grows |
| `toy_alignment.py` | all possible text → 6 answers to one ticket | base → **SFT** → **reward model** → **RLHF** (β sweep and a sampled policy-gradient run) → **DPO**, including reward hacking |

## Read the code first

- `toy_finetune.py → train_lora()`: `W = W0 + B @ A` with `W0` frozen. The gradient reaches B and A through the chain rule, and those are the only trainables. `B` starts at zero, so training starts exactly at the pretrained model.
- `toy_finetune.py → adam()`: look at what it stores for every trainable number. That storage is the memory bill from video 14.
- `toy_alignment.py`:
  - `LABEL_U`: fast labellers can't check the ticket category, which is the realistic blind spot.
  - `VIS`: what the reward model is allowed to see.
  - `π* ∝ π_sft · exp(RM/β)`: the exact optimum that PPO approximates by sampling.
  - The DPO loop is the loss from video 18, written out gradient by gradient.

## Run

```bash
cd lessons/16-training-toy
python toy_finetune.py                     # ~20 s
python toy_finetune.py --true-rank 16      # a bigger shift: small ranks can't keep up

python toy_alignment.py                    # ~2 s
python toy_alignment.py --expert-labels    # labellers who CAN check the category
python toy_alignment.py --beta 0.1         # looser leash for the sampled RLHF run and DPO
```

## What you should see

```
method      trainable   share  adam_bytes      n=16      n=48     n=200
full            4,096  100.0%      49,152    0.3600    0.1084    0.0002
lora r=1          128    3.1%       1,536    0.3937    0.1951    0.1321   ← rank too small: plateaus
lora r=2          256    6.2%       3,072    0.4024    0.0996    0.0000   ← = full, at 6% of the trainables
```

```
5 · RLHF: where the policy converges as the KL leash loosens
       β    E[RM]   E[true]     KL   most likely answer
    0.50    +1.69     +4.30   0.34   JSON + friendly line, right
    0.10    +1.96     +3.45   1.81   short friendly JSON, WRONG category    ← reward hacking
    0.02    +2.11     +2.15   3.90   short friendly JSON, WRONG category
```

The reward model's score (`E[RM]`) keeps rising as the leash loosens, while true value
peaks and then falls. That is Goodhart's law in one table. With `--expert-labels`, every
row improves on SFT.

## Check yourself

1. Why does LoRA r=1 never catch up, even with 200 examples? *(The change the task needs is rank 2, and a rank-1 adapter cannot represent it.)*
2. The reward model agrees with its labellers 71% of the time, yet RLHF still hacks it. Why? *(It learned the labellers' blind spot. Agreement on the pairs it saw says nothing about answers it rarely saw.)*
3. DPO moved less than loose RLHF. Is that good? *(Both. It can't exploit answers missing from the pairs, but it can't discover better ones either.)*
4. What fixes reward hacking for good? *(Better labels, meaning experts or a program that checks correctness, which is what RFT graders are, plus a tuned KL leash and evals on true quality.)*

## Explain what you learned

> "A reward model is a proxy for what the customer wants. Optimise it too hard and it stops
> tracking the goal, so I keep a KL leash, and where correctness can be checked by a program
> I'd rather use a grader, which is what reinforcement fine-tuning on Fireworks does."

**Next →** [17 · Full vs LoRA vs DoRA on your Mac](../17-full-vs-peft-mlx/)
