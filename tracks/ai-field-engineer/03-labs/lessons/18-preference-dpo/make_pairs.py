"""
Lesson 18 · step 1 — build preference pairs from the ticket data (video 18).

Each training ticket becomes one pair with the SAME prompt:
  chosen    the correct, concise JSON answer (what a reviewer approves)
  rejected  one realistic failure (what a reviewer would edit or thumbs-down):
              chatty     "Sure! Here's the JSON: …"              → breaks the parser
              prose      a helpful paragraph, no JSON             → breaks the parser
              wrong_cat  valid JSON, wrong category               → wrong answer
              wrong_sev  valid JSON, severity off by 2            → wrong judgement

Pairs should differ in the thing you care about. Here that is "parseable AND right".
In a real product, these come from agent edits, thumbs-down and regenerate clicks.

Writes two formats of the same pairs:
    data/mlx/{train,valid}.jsonl        {"system", "prompt", "chosen", "rejected"}   (mlx-lm-lora)
    data/fireworks/train.jsonl          {"input": {"messages": [...]}, "preferred_output": [...],
                                         "non_preferred_output": [...]}             (firectl dpo-job)

    python make_pairs.py
"""
import json
import random
from pathlib import Path

HERE = Path(__file__).parent
SRC = HERE.parents[1] / "data" / "tickets"
CATS = ["billing", "outage", "how-to", "abuse"]
rng = random.Random(18)


def rejected_for(ticket: str, ans: dict) -> tuple[str, str]:
    kind = rng.choice(["chatty", "prose", "wrong_cat", "wrong_sev"])
    if kind == "chatty":
        return kind, "Sure! Here's the JSON you asked for:\n" + json.dumps(ans) + "\nLet me know if you need anything else!"
    if kind == "prose":
        art = "an" if ans["category"][0] in "aeiou" else "a"
        return kind, (f"This looks like {art} {ans['category']} issue. I'd rate it around {ans['severity']} out of 5, "
                      f"and the next step would be to {ans['next_action']}.")
    if kind == "wrong_cat":
        wrong = dict(ans, category=rng.choice([c for c in CATS if c != ans["category"]]))
        return kind, json.dumps(wrong)
    wrong = dict(ans, severity=max(1, min(5, ans["severity"] + rng.choice([-2, 2]))))
    return kind, json.dumps(wrong)


def build(split: str) -> list[dict]:
    pairs = []
    for line in (SRC / f"{split}.jsonl").read_text().splitlines():
        msgs = json.loads(line)["messages"]
        system, user, answer = msgs[0]["content"], msgs[1]["content"], msgs[2]["content"]
        kind, bad = rejected_for(user, json.loads(answer))
        pairs.append({"system": system, "prompt": user, "chosen": answer, "rejected": bad, "kind": kind})
    return pairs


def main() -> None:
    if not (SRC / "train.jsonl").exists():
        raise SystemExit("run: python data/make_tickets.py")
    (HERE / "data" / "mlx").mkdir(parents=True, exist_ok=True)
    (HERE / "data" / "fireworks").mkdir(parents=True, exist_ok=True)
    kinds = {}
    for split in ("train", "valid"):
        pairs = build(split)
        with (HERE / "data" / "mlx" / f"{split}.jsonl").open("w") as f:
            for p in pairs:
                f.write(json.dumps({k: p[k] for k in ("system", "prompt", "chosen", "rejected")}) + "\n")
                kinds[p["kind"]] = kinds.get(p["kind"], 0) + (split == "train")
        if split == "train":
            with (HERE / "data" / "fireworks" / "train.jsonl").open("w") as f:
                for p in pairs:
                    f.write(json.dumps({
                        "input": {"messages": [{"role": "system", "content": p["system"]},
                                               {"role": "user", "content": p["prompt"]}]},
                        "preferred_output": [{"role": "assistant", "content": p["chosen"]}],
                        "non_preferred_output": [{"role": "assistant", "content": p["rejected"]}],
                    }) + "\n")
        print(f"{split}: {len(pairs)} pairs")
    print("rejected kinds (train): " + ", ".join(f"{k} {v}" for k, v in sorted(kinds.items())))
    print(f"→ {HERE / 'data'}")
    ex = build("valid")[0]
    print(f"\nexample\n  prompt   {ex['prompt']}\n  chosen   {ex['chosen']}\n  rejected {ex['rejected']}  ({ex['kind']})")


if __name__ == "__main__":
    main()
