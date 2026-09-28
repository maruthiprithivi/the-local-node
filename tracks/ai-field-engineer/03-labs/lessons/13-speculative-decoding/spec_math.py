"""
Lesson 13 · step 1 — when does speculation pay? The maths, before the GPU.

A small DRAFT model guesses k tokens; the big TARGET model checks all k in ONE pass
(checking is parallel, like prefill). Accepted guesses are free tokens.

    expected tokens per target pass  E = (1 − α^(k+1)) / (1 − α)
    speedup                          ≈ E / (1 + k·c)

    α  acceptance rate — how often the draft guesses what the target would say
    k  tokens drafted per step
    c  cost of one draft token relative to one target token (1B vs 8B ≈ 0.1)

    python spec_math.py
    python spec_math.py --c 0.2      # a bigger/slower drafter
"""
import argparse

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--c", type=float, default=0.1, help="draft/target cost ratio")
a = ap.parse_args()

alphas = [0.3, 0.5, 0.6, 0.7, 0.8, 0.9]
ks = [2, 4, 6, 8]
print(f"speedup vs normal decoding (draft cost ratio c = {a.c})\n")
print("   α \\ k " + "".join(f"{k:>8}" for k in ks))
for al in alphas:
    cells = []
    for k in ks:
        E = (1 - al ** (k + 1)) / (1 - al)
        s = E / (1 + k * a.c)
        cells.append(f"{s:7.2f}{'×' if s >= 1 else '↓'}")
    print(f"  {al:4.1f}   " + "".join(cells))
print("\n↓ = slower than no speculation.  Structured/repetitive output (JSON, code, extraction)\n"
      "has high α; creative prose has low α. So: measure α on the customer's traffic first.")
