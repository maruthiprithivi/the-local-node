"""
Lesson 11 — why QLoRA fits on a laptop: a back-of-envelope memory budget.

Full fine-tuning keeps, per parameter: the weight (2 B), its gradient (2 B), and
Adam's two moments (8 B in fp32) ≈ 12–16 bytes/param → a 7B model needs ~100 GB.

QLoRA freezes the base in 4-bit (~0.56 B/param) and trains only small adapters,
so gradients and optimizer state exist ONLY for the adapter.

    python qlora_memory.py                      # 7B, rank 8, last 8 layers
    python qlora_memory.py --params 70 --rank 16 --layers 80
"""
import argparse

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--params", type=float, default=7.6, help="base model size in billions")
ap.add_argument("--hidden", type=int, default=3584, help="hidden size (Qwen2.5-7B: 3584)")
ap.add_argument("--layers", type=int, default=8, help="layers that get adapters")
ap.add_argument("--rank", type=int, default=8)
ap.add_argument("--targets", type=int, default=4, help="adapted matrices per layer (q,k,v,o)")
ap.add_argument("--act-gb", type=float, default=2.0, help="activations + overhead, rough")
a = ap.parse_args()

P = a.params * 1e9
full = P * 16 / 1e9                                    # weights+grads+Adam, mixed precision
lora_params = a.layers * a.targets * 2 * a.hidden * a.rank   # A (h×r) + B (r×h) per matrix
base_4bit = P * 0.5625 / 1e9                           # 4.5 bits/weight incl. scales
adapter_train = lora_params * 16 / 1e9                 # adapter weights+grads+Adam
qlora = base_4bit + adapter_train + a.act_gb

print(f"base model            {a.params:.1f} B params")
print(f"LoRA adapter          {lora_params / 1e6:,.1f} M params  ({100 * lora_params / P:.3f}% of the model)")
print()
print(f"full fine-tune        ≈ {full:6.1f} GB   (multi-GPU territory)")
print(f"QLoRA                 ≈ {qlora:6.1f} GB   = 4-bit base {base_4bit:.1f} + adapter training "
      f"{adapter_train:.2f} + activations {a.act_gb}")
print(f"adapter file on disk  ≈ {lora_params * 2 / 1e6:6.1f} MB   (what you ship / hot-swap in multi-LoRA)")
