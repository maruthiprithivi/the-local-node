"""
Lesson 16 · part 1 — full fine-tuning vs LoRA on ONE layer, in numpy (seconds, no GPU).

Setup
  A "pretrained" layer W0 (64 × 64) already does a general job well.
  The new task needs W0 + ΔW, where ΔW is low-rank (rank 2) — like most real fine-tunes.
  We try it with 16, 48 and 200 training examples for the new task.

We train it five ways with plain gradient descent:
  full        update all 4,096 weights of W                              (full fine-tuning)
  lora r=1…8  freeze W0, train B (64×r) and A (r×64); W = W0 + B·A        (LoRA)

and report, for each:
  trainable   how many numbers the optimizer must track
  adam_bytes  optimizer + gradient memory at 12 bytes per trainable param
  task_err    error on NEW held-out task examples (did it learn the task, or just memorise?)

    python toy_finetune.py
    python toy_finetune.py --true-rank 16      # a bigger shift: now small ranks can't keep up
"""
import argparse

import numpy as np

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--d", type=int, default=64, help="layer width")
ap.add_argument("--true-rank", type=int, default=2, help="rank of the change the task really needs")
ap.add_argument("--n-train", default="16,48,200", help="comma list of training-set sizes")
ap.add_argument("--steps", type=int, default=5000)
ap.add_argument("--seed", type=int, default=0)
a = ap.parse_args()
rng = np.random.default_rng(a.seed)
d = a.d

# ── the world ────────────────────────────────────────────────────────────────
W0 = rng.normal(0, 1 / np.sqrt(d), (d, d))                                   # "pretrained" weights
U, V = rng.normal(0, 1, (d, a.true_rank)), rng.normal(0, 1, (a.true_rank, d))
dW_true = 0.6 * U @ V / np.sqrt(d * a.true_rank)                             # the low-rank shift the task needs
W_task = W0 + dW_true

X_test = rng.normal(0, 1, (500, d))                                           # held-out task inputs


def mse(W, X, Wref):
    return float(np.mean((X @ W.T - X @ Wref.T) ** 2))


def adam(params, grads, state, lr=1e-2, b1=0.9, b2=0.999, eps=1e-8):
    """Plain Adam. Note what it stores: m and v for EVERY trainable number — that is the memory bill."""
    state["t"] = state.get("t", 0) + 1
    for k in params:
        m = state.setdefault("m_" + k, np.zeros_like(params[k]))
        v = state.setdefault("v_" + k, np.zeros_like(params[k]))
        m[:] = b1 * m + (1 - b1) * grads[k]
        v[:] = b2 * v + (1 - b2) * grads[k] ** 2
        mh, vh = m / (1 - b1 ** state["t"]), v / (1 - b2 ** state["t"])
        params[k] -= lr * mh / (np.sqrt(vh) + eps)


def train_full(X_train, Y_train):
    P = {"W": W0.copy()}
    st = {}
    for _ in range(a.steps):
        err = X_train @ P["W"].T - Y_train                      # forward + residual
        G = 2 * err.T @ X_train / len(X_train)                  # dLoss/dW, same shape as W
        adam(P, {"W": G}, st)
    return P["W"], P["W"].size


def train_lora(r, X_train, Y_train):
    # Standard LoRA init: A small random, B zero → training starts exactly at W0.
    P = {"A": rng.normal(0, 1 / np.sqrt(d), (r, d)), "B": np.zeros((d, r))}
    st = {}
    for _ in range(a.steps):
        W = W0 + P["B"] @ P["A"]                                # W0 is frozen; only B·A changes
        err = X_train @ W.T - Y_train
        G = 2 * err.T @ X_train / len(X_train)                  # gradient w.r.t. the effective W …
        adam(P, {"B": G @ P["A"].T, "A": P["B"].T @ G}, st)     # … chained into B and A (the only trainables)
    return W0 + P["B"] @ P["A"], P["A"].size + P["B"].size


sizes = [int(x) for x in a.n_train.split(",")]
methods = ["full"] + [f"lora r={r}" for r in (1, 2, 4, 8)]
err = {m: {} for m in methods}
count = {}
for n in sizes:
    X_train = rng.normal(0, 1, (n, d))                                   # n task examples
    Y_train = X_train @ W_task.T + rng.normal(0, 0.02, (n, d))            # labels, a little noise
    W, count["full"] = train_full(X_train, Y_train)
    err["full"][n] = mse(W, X_test, W_task)
    for r in (1, 2, 4, 8):
        W, count[f"lora r={r}"] = train_lora(r, X_train, Y_train)
        err[f"lora r={r}"][n] = mse(W, X_test, W_task)

print(f"layer {d}×{d} · the task needs a rank-{a.true_rank} change · held-out task error (lower is better)\n")
head = f"{'method':10s} {'trainable':>10s} {'share':>7s} {'adam_bytes':>11s} " + " ".join(f"{'n=' + str(n):>9s}" for n in sizes)
print(head)
print("-" * len(head))
for m in methods:
    n_t = count[m]
    print(f"{m:10s} {n_t:10,d} {100 * n_t / W0.size:6.1f}% {n_t * 12:11,d} " + " ".join(f"{err[m][n]:9.4f}" for n in sizes))

print(f"""
How to read it
  • Enough data (right-hand column): LoRA with r ≥ {a.true_rank} (the true rank of the change) matches full
    fine-tuning, while training only a few percent of the numbers.
  • r below the true rank plateaus however much data you add: rank is the capacity dial (video 16).
  • Little data (left-hand column): nothing generalises well. With fewer examples than the layer
    is wide, no method can pin down the whole change. More clean data beats a cleverer method
    (video 15).
  • adam_bytes is the gradient and optimizer bill at 12 bytes per trainable number. Scale 4,096
    up to 8 billion and you have the memory wall of full fine-tuning (video 14). Scale it to
    20 million and you have LoRA's.
  • A linear toy can't show "forgetting" of general skills; lesson 17 checks that on a real model.
""")
