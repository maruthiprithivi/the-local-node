"""
Lesson 17 · step 1 — how many parameters does each method train, and how much memory does it need?

Counts come from the model's real shapes (config.json), not rules of thumb.
For a weight matrix of shape (in × out), a LoRA adapter of rank r adds  r·(in + out)  parameters.
DoRA adds one magnitude value per output channel on top.

Memory to TRAIN (weights + gradients + Adam state; activations excluded):
  full   16 B × all params                       (bf16 weights & grads, fp32 Adam m, v, master copy)
  LoRA    2 B × base  + 16 B × adapter params     (bf16 frozen base)
  QLoRA  ≈0.56 B × base + 16 B × adapter params   (4-bit frozen base)

    python peft_params.py --model 8b --rank 16
    python peft_params.py --model 70b --rank 64 --mlp
    python peft_params.py --model 0.5b          # what lesson 17 trains on your Mac
"""
import argparse

# hidden, layers, attention heads, kv heads, head_dim, mlp (intermediate) — from each config.json
MODELS = {
    "0.5b": ("Qwen2.5-0.5B", 896, 24, 14, 2, 64, 4864, 0.49e9),
    "7b": ("Qwen2.5-7B", 3584, 28, 28, 4, 128, 18944, 7.6e9),
    "8b": ("Llama-3.1-8B", 4096, 32, 32, 8, 128, 14336, 8.0e9),
    "70b": ("Llama-3.1-70B", 8192, 80, 64, 8, 128, 28672, 70.6e9),
}

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--model", choices=MODELS, default="8b")
ap.add_argument("--rank", type=int, default=16)
ap.add_argument("--mlp", action="store_true", help="also adapt the MLP (gate, up, down)")
ap.add_argument("--layers", type=int, help="adapt only the last N layers (default: all)")
a = ap.parse_args()

name, d, L, H, KV, hd, ff, total = MODELS[a.model]
layers = a.layers or L
mats = {"q": (d, H * hd), "k": (d, KV * hd), "v": (d, KV * hd), "o": (H * hd, d)}
if a.mlp:
    mats.update({"gate": (d, ff), "up": (d, ff), "down": (ff, d)})

lora_per_layer = sum(a.rank * (i + o) for i, o in mats.values())
dora_per_layer = lora_per_layer + sum(o for _, o in mats.values())
lora = lora_per_layer * layers
dora = dora_per_layer * layers

print(f"{name}: {total / 1e9:.1f}B params · hidden {d} · {L} layers · GQA {H}q/{KV}kv heads")
print(f"adapting {', '.join(mats)} in {layers} layers at rank {a.rank}\n")
print("  per layer:")
for m, (i, o) in mats.items():
    print(f"    {m:5s} {i:>6} × {o:<6}  full {i * o / 1e6:7.2f} M   LoRA r·(in+out) = {a.rank * (i + o) / 1e3:7.1f} K")

GB = 1e9
rows = [
    ("full fine-tune", total, 16 * total),
    ("LoRA", lora, 2 * total + 16 * lora),
    ("DoRA", dora, 2 * total + 16 * dora),
    ("QLoRA (4-bit base)", lora, 0.5625 * total + 16 * lora),
]
print(f"\n  {'method':20s} {'trainable':>14s} {'share':>8s} {'train memory*':>14s} {'checkpoint':>12s}")
for m, t, mem in rows:
    ckpt = f"{2 * total / GB:.1f} GB" if m.startswith("full") else f"{2 * t / 1e6:.0f} MB"
    print(f"  {m:20s} {t:>14,.0f} {100 * t / total:7.3f}% {mem / GB:11.1f} GB {ckpt:>12s}")
print("\n  * weights + gradients + optimizer only. Activations add more and grow with batch × sequence length;"
      "\n    gradient checkpointing shrinks them. Compare with the 'Peak mem' mlx_lm.lora prints.")
