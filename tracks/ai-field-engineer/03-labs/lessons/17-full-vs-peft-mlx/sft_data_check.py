"""
Lesson 17 · step 0 — check an SFT dataset BEFORE you spend compute on it (video 15).

Catches the mistakes that quietly ruin training runs:
  ✗ lines that are not valid JSON, or have no "messages"
  ✗ conversations that do not END with an assistant turn (nothing to learn)
  ✗ empty contents, unknown roles
  ✗ exact duplicates (the model over-learns them)
  ✗ test-set leakage: training examples whose user text appears in the held-out test set
  ✗ rows longer than your max sequence length (silently truncated = broken answers)
  ~ label balance (for the triage task: category counts parsed from the answers)

    python sft_data_check.py                                   # data/tickets/train.jsonl vs test.jsonl
    python sft_data_check.py my_train.jsonl --test my_test.jsonl --max-tokens 2048
Exit code 1 if any ✗ check fails, so it can gate a training script.
"""
import argparse
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("train", nargs="?", default=str(ROOT / "data/tickets/train.jsonl"))
ap.add_argument("--test", default=str(ROOT / "data/tickets/test.jsonl"))
ap.add_argument("--max-tokens", type=int, default=1024, help="trainer's max sequence length")
a = ap.parse_args()

rows, problems = [], collections.defaultdict(list)
for n, line in enumerate(Path(a.train).read_text().splitlines(), 1):
    if not line.strip():
        continue
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        problems["not valid JSON"].append(n)
        continue
    msgs = obj.get("messages")
    if not isinstance(msgs, list) or not msgs:
        problems['missing "messages"'].append(n)
        continue
    roles = [m.get("role") for m in msgs]
    if any(r not in ("system", "user", "assistant", "tool") for r in roles):
        problems["unknown role"].append(n)
    if roles[-1] != "assistant":
        problems["does not end with an assistant turn"].append(n)
    if any(not str(m.get("content", "")).strip() for m in msgs):
        problems["empty content"].append(n)
    toks = sum(len(str(m.get("content", ""))) for m in msgs) // 4 + 8 * len(msgs)   # ~4 chars/token + template
    if toks > a.max_tokens:
        problems[f"longer than --max-tokens {a.max_tokens}"].append(n)
    rows.append((n, obj, toks))

# duplicates
seen = {}
for n, obj, _ in rows:
    key = json.dumps(obj["messages"], sort_keys=True)
    if key in seen:
        problems["exact duplicate"].append(n)
    seen.setdefault(key, n)

# test leakage: user text that also appears in the test set
test_texts = set()
if Path(a.test).exists():
    for line in Path(a.test).read_text().splitlines():
        if line.strip():
            t = json.loads(line)
            test_texts.add((t.get("ticket") or next((m["content"] for m in t.get("messages", []) if m["role"] == "user"), "")).strip())
for n, obj, _ in rows:
    user = next((m["content"] for m in obj["messages"] if m["role"] == "user"), "").strip()
    if user in test_texts:
        problems["user text also in the TEST set (leakage)"].append(n)

# label balance (triage-specific, skipped if answers are not JSON)
cats = collections.Counter()
for _, obj, _ in rows:
    try:
        cats[json.loads(obj["messages"][-1]["content"]).get("category", "?")] += 1
    except Exception:
        pass

toks = sorted(t for *_, t in rows)
print(f"{a.train}\n  rows {len(rows)}   tokens p50 ≈{toks[len(toks) // 2] if toks else 0}   max ≈{toks[-1] if toks else 0}")
if cats:
    total = sum(cats.values())
    print("  label balance  " + "  ".join(f"{c} {100 * k / total:.0f}%" for c, k in cats.most_common()))
blocking = {k: v for k, v in problems.items()}
if not blocking:
    print("  ✓ no problems found")
for k, v in blocking.items():
    print(f"  ✗ {k}: {len(v)} rows (first: line {v[0]})")
if "exact duplicate" in blocking:
    print("\nDuplicates make the model over-learn those rows; dedupe before training.")
sys.exit(1 if blocking else 0)
