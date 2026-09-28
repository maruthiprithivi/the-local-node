# 18 · Preference tuning with DPO, on your Mac and on Fireworks

> **Lab book:** Training labs → **T3**  **Watch:** videos 17 `17-rlhf.mp4`, 18 `18-dpo.mp4`
> **Time:** about 1 h on the Mac · Fireworks optional  **Cost:** free locally · cents to train plus deployment time on Fireworks

## What and why

SFT teaches *what* to answer. DPO teaches *which of two answers is better* using pairs
of chosen and rejected answers, with no reward model and no reinforcement loop. Our triage
model sometimes wraps its JSON in chat ("Sure! Here's the JSON…"), writes prose, or gets
the category or severity wrong. Each of those is a **rejected** answer, and the clean,
correct JSON is **chosen**.

```
prompt    "Card declined twice, launch is tomorrow."
chosen    {"category": "billing", "severity": 4, "next_action": "route to billing; verify charge"}
rejected  Sure! Here's the JSON you asked for: {…} Let me know if you need anything else!
```

In a real product, these pairs come for free: an agent's edit (chosen) of a model draft
(rejected), a thumbs-down, a regenerate.

## The files, in order

| step | file | runs on | does |
|---|---|---|---|
| 1 | `make_pairs.py` | anywhere | 800 train and 100 valid pairs, with four realistic failure kinds; written in **mlx-lm-lora** and **Fireworks** formats |
| 2 | `dpo_mlx.sh` | Mac | fuses lesson 17's LoRA into an SFT model if present (SFT first, then DPO), then `mlx_lm_lora.train --train-mode dpo --beta 0.1` |
| 3 | `dpo_fireworks.sh` | Mac → FW | `firectl dpo-job create --loss-method DPO`; optional deployment and eval, with auto-delete |
| 4 | `pref_eval.py` | any target | valid JSON %, chatty %, category and severity accuracy, answer length; with `--pairwise`, DPO's implicit reward (chosen vs rejected log-prob) |

## Run

```bash
cd lessons/18-preference-dpo
python make_pairs.py
python pref_eval.py --target mock --label mock              # rehearse the metrics offline

bash dpo_mlx.sh                                             # 10–20 min
# two terminals, as the script prints:
#   mlx_lm.server --model <START> --port 8081
#   mlx_lm.server --model <START> --adapter-path adapters/dpo --port 8082
MLX_MODEL=<START> python pref_eval.py --target mlx --label before
MLX_URL=http://localhost:8082/v1 MLX_MODEL=<START> python pref_eval.py --target mlx --label after-dpo

python pref_eval.py --pairwise <START>                          --label pairs-before
python pref_eval.py --pairwise <START> --adapter adapters/dpo   --label pairs-after

bash dpo_fireworks.sh                                       # optional, paid
```

`<START>` is whichever model `dpo_mlx.sh` printed: `sft_model/` if you did lesson 17 first,
otherwise the instruct model.

## What you should see (shape)

```
label       valid_%  chatty_%  category_%  severity_%  avg_chars
before         ~80       ~20         ~70         ~60        ~110
after-dpo      ~98        ~1         ≈ or ↑      ≈ or ↑         ~85     ← format fixed, no correctness lost

label              pref_acc_%  margin
pairwise base            ~60     +1.x
pairwise +dpo            ~95    +10.x                                  ← the implicit reward grew
```

If `category_%` **drops** after DPO, taste has cost correctness (video 18). Try a larger β,
fewer iterations, or more `wrong_cat` pairs so correctness is part of what "preferred" means.

## Check yourself

1. Why fuse the SFT adapter first rather than running DPO on the raw instruct model? *(DPO refines a model that already does the task. With nothing to refine, it mostly learns "not the rejected text".)*
2. What does β do here, concretely? *(It scales the margin in the loss. A smaller β lets the policy move further from the reference before the loss stops rewarding it.)*
3. Your pairs are 50% "chatty". What happens to accuracy if none of them are `wrong_cat`? *(The model learns format, not correctness, and category accuracy may even slip.)*
4. When would you use ORPO instead (`--loss-method ORPO` on Fireworks)? *(When you want SFT and preference tuning in one step without holding a reference model in memory.)*

## Explain what you learned

> "Their agents already edit the model's drafts. Every edit is a preference pair. Run DPO on
> an SFT'd model and the formatting failures disappear. I'd watch category accuracy so taste
> doesn't cost correctness, and where correctness can be checked by code, I'd use RFT with a
> grader instead."

**Back to →** [the course README](../../README.md) · the lab book's training section
