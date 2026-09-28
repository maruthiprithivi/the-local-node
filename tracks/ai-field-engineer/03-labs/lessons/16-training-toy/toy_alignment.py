"""
Lesson 16 · part 2 — the whole alignment story on one prompt, in numpy (seconds).

    base model → SFT → reward model → RLHF (with / without the KL leash) → DPO

The "model" is a probability distribution over six possible answers to one support
ticket ("Card declined twice, launch is tomorrow"). That is a toy, but every step
below is the real algorithm, just on 6 outputs instead of all possible text:

  SFT      cross-entropy on demonstrations        (videos 15)
  RM       Bradley-Terry fit on preference pairs  (video 17)
  RLHF     policy gradient on RM reward − β·KL    (video 17, PPO's objective)
  DPO      the DPO loss on the same pairs         (video 18)

The twist, which is realistic: the people labelling preferences are fast, not
experts. They judge what they can see (valid JSON? short? friendly?) but cannot
check whether the ticket category is right. The reward model learns THEIR taste.
Without a KL leash, RLHF pushes toward the answer that scores best on that proxy:
short, friendly JSON with the WRONG category. That is reward hacking.
--expert-labels switches to labellers who can check correctness, which is the real fix.

    python toy_alignment.py
    python toy_alignment.py --beta 0.1       # looser leash for the sampled RLHF run and DPO
    python toy_alignment.py --expert-labels  # labellers who can verify the category
"""
import argparse

import numpy as np

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--beta", type=float, default=0.5, help="KL leash for the sampled RLHF run and for DPO")
ap.add_argument("--pairs", type=int, default=400, help="preference pairs collected")
ap.add_argument("--seed", type=int, default=1)
ap.add_argument("--expert-labels", action="store_true", help="labellers can check correctness")
a = ap.parse_args()
rng = np.random.default_rng(a.seed)

# ── the six possible answers ─────────────────────────────────────────────────
#          name                                   correct  json  length  friendly
ANSWERS = [("concise JSON, right category",        1,       1,    0.15,   0),
           ("JSON + friendly line, right",          1,       1,    0.35,   1),
           ("concise JSON, WRONG category",         0,       1,    0.15,   0),
           ("friendly explanation, right, no JSON", 1,       0,    0.70,   1),
           ("short friendly JSON, WRONG category",  0,       1,    0.10,   1),
           ("'billing?' terse, no JSON",            1,       0,    0.05,   0)]
names = [x[0] for x in ANSWERS]
F = np.array([x[1:] for x in ANSWERS], float)          # features: correct, json, length, friendly
K = len(ANSWERS)

# What people actually value (hidden from the reward model): right answer, parseable, not bloated.
true_w = np.array([3.0, 1.5, -1.5, 0.8])
TRUE_U = F @ true_w
# What fast, non-expert labellers reward: everything visible, but NOT correctness.
LABEL_U = TRUE_U if a.expert_labels else F @ np.array([0.0, 1.5, -1.5, 0.8])


def softmax(z):
    z = z - z.max()
    e = np.exp(z)
    return e / e.sum()


def kl(p, q):
    return float(np.sum(p * (np.log(p + 1e-12) - np.log(q + 1e-12))))


def show(title, p, extra=""):
    top = int(np.argmax(p))
    print(f"\n{title}   E[true value] = {p @ TRUE_U:+.2f}{extra}")
    for i in range(K):
        bar = "█" * int(round(p[i] * 40))
        print(f"  {names[i]:38s} {p[i]:5.2f} {bar}{'  ◀' if i == top else ''}")


# ── 1. base model: knows many ways to answer, no idea which one we want ──────
base_logits = np.log(np.array([0.10, 0.12, 0.18, 0.20, 0.25, 0.15]))
p_base = softmax(base_logits)
show("1 · BASE MODEL", p_base)

# ── 2. SFT: imitate demonstrations written by good support agents ───────────
demos = rng.choice(K, size=300, p=[0.38, 0.30, 0.05, 0.16, 0.03, 0.08])  # agents slip up sometimes  # what agents actually wrote
logits = base_logits.copy()
for _ in range(400):                                   # gradient descent on cross-entropy
    p = softmax(logits)
    grad = p - np.bincount(demos, minlength=K) / len(demos)   # d(CE)/d(logits) for a softmax
    logits -= 0.5 * grad
p_sft = softmax(logits)
show("2 · AFTER SFT (imitation)", p_sft, f"   KL from base {kl(p_sft, p_base):.2f}")

# ── 3. preference pairs: sample two answers from the SFT model, a person picks one ──
i = rng.choice(K, size=a.pairs, p=p_sft)
j = rng.choice(K, size=a.pairs, p=p_sft)
keep = i != j
i, j = i[keep], j[keep]
prefer_i = rng.random(len(i)) < 1 / (1 + np.exp(-(LABEL_U[i] - LABEL_U[j])))  # labellers ~ Bradley-Terry on what THEY value
chosen = np.where(prefer_i, i, j)
rejected = np.where(prefer_i, j, i)
who = "expert labellers (can check the category)" if a.expert_labels else "fast labellers (cannot check the category)"
print(f"\n3 · PREFERENCE DATA  {len(chosen)} pairs sampled from the SFT model, labelled by {who}")

# ── 4. reward model: Bradley-Terry on what it CAN see (json, length, confident) ──
VIS = F if a.expert_labels else F[:, 1:]               # a fast labeller's RM can't see correctness
w_rm = np.zeros(VIS.shape[1])
for _ in range(3000):
    margin = (VIS[chosen] - VIS[rejected]) @ w_rm
    g = -((1 - 1 / (1 + np.exp(-margin)))[:, None] * (VIS[chosen] - VIS[rejected])).mean(0)
    w_rm -= 0.5 * (g + 1e-3 * w_rm)
RM = VIS @ w_rm
acc = np.mean(RM[chosen] > RM[rejected])
labels = ["correct", "json", "length", "friendly"][-VIS.shape[1]:]
print("\n4 · REWARD MODEL  learned weights  " + "  ".join(f"{n} {w:+.2f}" for n, w in zip(labels, w_rm))
      + f"   (agrees with its labellers on {acc:.0%} of pairs)")
print(f"     Its favourite answer: '{names[int(np.argmax(RM))]}'  (true value {TRUE_U[int(np.argmax(RM))]:+.2f})")
for k in range(K):
    print(f"  {names[k]:38s} RM {RM[k]:+.2f}   true {TRUE_U[k]:+.2f}")


# ── 5. RLHF: policy gradient on  E[RM] − β·KL(π ‖ π_sft)  (PPO optimises this objective) ──
def rlhf(beta, steps=4000, lr=0.2, batch=64):
    th = np.log(p_sft).copy()
    for _ in range(steps):
        p = softmax(th)
        y = rng.choice(K, size=batch, p=p)              # sample answers from the current policy
        adv = RM[y] - beta * (np.log(p[y]) - np.log(p_sft[y]))   # reward minus the KL "leash" charge
        adv = adv - adv.mean()                          # baseline, reduces variance
        g = np.zeros(K)
        for yy, aa in zip(y, adv):                      # REINFORCE: raise log-prob of above-average answers
            g += aa * (np.eye(K)[yy] - p)
        th += lr * g / batch
    return softmax(th)


# Where does RLHF end up? The KL-regularised objective has an exact optimum:
#     π*(y) ∝ π_sft(y) · exp(reward(y) / β)
# PPO is a sampling-based way of approaching it. Sweep the leash β from tight to loose:
print("\n5 · RLHF: where the policy converges as the KL leash loosens   (π* ∝ π_sft · exp(RM/β))")
print(f"  {'β':>6s}  {'E[RM]':>7s}  {'E[true]':>8s}  {'KL':>5s}   most likely answer")
sweep = []
for beta in (4, 1, 0.5, 0.2, 0.1, 0.05, 0.02, 0.01):
    pi = softmax(np.log(p_sft) + RM / beta)
    sweep.append((beta, pi))
    print(f"  {beta:6.2f}  {pi @ RM:+7.2f}  {pi @ TRUE_U:+8.2f}  {kl(pi, p_sft):5.2f}   {names[int(np.argmax(pi))]}")
best = max(sweep, key=lambda t: t[1] @ TRUE_U)
worst = sweep[-1]
if worst[1] @ TRUE_U < best[1] @ TRUE_U - 0.2:
    print(f"  ↑ the proxy (E[RM]) keeps rising as β shrinks, but TRUE value peaks near β = {best[0]} and then falls:"
          "\n    that is reward hacking (Goodhart's law: optimise a proxy hard enough and it stops tracking the goal).")

b = a.beta if a.beta > 0 else 0.5
p_rlhf = rlhf(b)
closed = softmax(np.log(p_sft) + RM / b)
show(f"5b · RLHF by policy gradient (β = {b}), the PPO-style sampled version", p_rlhf,
     f"   E[RM] {p_rlhf @ RM:+.2f}   KL from SFT {kl(p_rlhf, p_sft):.2f}   (exact optimum KL {kl(closed, p_sft):.2f})")

# ── 6. DPO: same pairs, no reward model, no sampling ─────────────────────────
th = np.log(p_sft).copy()
ref = np.log(p_sft)
for _ in range(3000):
    lp = th - np.log(np.sum(np.exp(th)))                # log π(y)
    m = b * ((lp[chosen] - ref[chosen]) - (lp[rejected] - ref[rejected]))
    s = 1 - 1 / (1 + np.exp(-m))                        # = σ(−m): how wrong each pair still is
    p = softmax(th)
    g = np.zeros(K)
    np.add.at(g, chosen, -b * s)                        # push chosen up …
    np.add.at(g, rejected, b * s)                       # … rejected down
    # (the softmax normaliser cancels inside each pair's margin, so these are the exact gradients)
    th -= 0.5 * g / len(chosen)
p_dpo = softmax(th)
show(f"6 · DPO (β = {b}, same pairs, no reward model)", p_dpo, f"   KL from SFT {kl(p_dpo, p_sft):.2f}")

print(f"""
What to notice
  • SFT moved probability onto the kinds of answers agents write. Imitation got most of the way.
  • The reward model learned its labellers' taste, blind spot included. It is a proxy for what you want.
  • Loosening the leash (smaller β) always raises the proxy E[RM]. True value rises, peaks, then falls.
    That is reward hacking, and it is why production RLHF always keeps a KL term and tunes β.
  • The sampled policy-gradient run (5b) lands on the same answer as the exact optimum: that is PPO's job.
  • The leash limits the damage by keeping the policy close to SFT. It cannot fix bad labels.
  • DPO learns from the same pairs, so it inherits the same bias. It stays closer to SFT because it only
    moves answers that appear in the pairs.
  • Re-run with --expert-labels: every method now improves on SFT. Better preferences beat a better
    algorithm, and a program that checks correctness is what RFT graders are for.
""")
