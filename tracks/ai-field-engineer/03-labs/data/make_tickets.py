"""
data/make_tickets.py — the one dataset lessons 07–11 share.

A support-ticket TRIAGE task, the kind an enterprise customer brings on day one:
    input : free-text ticket
    output: {"category": billing|outage|how-to|abuse, "severity": 1–5, "next_action": str}

Why synthetic? So everyone gets the same numbers and nothing private leaks.
Why this task? It has a checkable answer (so evals are honest), needs structured
output (lesson 07), is cheap to batch (08), and small models improve visibly
with a LoRA (10, 11).

Honest splits: tickets are de-duplicated, the test set never shares a ticket text with
training, and one phrasing per category appears ONLY in the test set, so evals measure
generalisation, not memory. (lessons/17-full-vs-peft-mlx/sft_data_check.py verifies this.)

Writes (deterministic, seed 7):
    data/tickets/train.jsonl   800 rows  chat format → fine-tuning (Fireworks SFT + MLX LoRA)
    data/tickets/valid.jsonl   100 rows  chat format → MLX validation loss
    data/tickets/test.jsonl    100 rows  {"ticket", "category", "severity"} → evals, NEVER trained on

    python data/make_tickets.py
"""
import json
import random
from pathlib import Path

OUT = Path(__file__).parent / "tickets"
SYSTEM = ("You triage customer support tickets. Reply with JSON only: "
          '{"category": "billing|outage|how-to|abuse", "severity": 1-5, "next_action": "<short>"}')

PRODUCTS = ["the API", "the dashboard", "SSO login", "webhooks", "the EU cluster", "batch jobs", "the CLI"]
REGIONS = ["us-east", "eu-west", "ap-south", "us-west"]
URGENT = ["", "", "", " This is urgent.", " Launch is tomorrow.", " It affects all users.", " We are in production."]
OPENERS = ["", "", "Hi team, ", "Hello, ", "Quick one: ", "Hey, ", "Good morning. "]
CLOSERS = ["", "", " Thanks.", " Please help.", " Account {acct}.", " Ref #{ref}.", " Cheers, {name}."]
NAMES = ["Priya", "Tom", "Wei", "Aisha", "Carlos", "Mei", "Olu", "Sara", "Ken", "Lena"]

TEMPLATES = {
    "billing": [
        "My card was declined when renewing the plan.", "We were charged twice on the last invoice.",
        "Can I get a refund for the unused seats (${amt})?", "The invoice shows the wrong company name.",
        "Why did the payment for ${amt} fail?", "Billing page shows a charge I don't recognise.",
    ],
    "outage": [
        "{prod} is down in {region}.", "Getting 500 errors from {prod} since 09:00.",
        "Requests to {prod} time out after 30s.", "Huge latency spike on {prod} in {region}.",
        "{prod} unreachable for our whole team.", "Error rate on {prod} jumped to 40%.",
    ],
    "abuse": [
        "Someone is sending spam from an account on your platform.", "We received a phishing email using your logo.",
        "I think my API key was stolen — unknown usage overnight.", "An account is scraping our public pages via {prod}.",
        "Report fraud: fake invoices sent in your name.", "Abuse report: bot signups from {region}.",
    ],
    "how-to": [
        "How do I rotate my API key?", "How to configure {prod} for a second region?",
        "Where can I find docs for {prod} rate limits?", "How do I set up SSO with Okta?",
        "How to export usage data to CSV?", "Where can I change the default model?",
    ],
}
BASE_SEV = {"outage": 4, "abuse": 4, "billing": 3, "how-to": 2}
ACTION = {"billing": "route to billing; verify charge", "outage": "page on-call; check status page",
          "abuse": "route to trust & safety; suspend key if confirmed", "how-to": "reply with docs link"}


def make(rng: random.Random, held_out: bool) -> dict:
    """held_out=True uses only each category's LAST template (never seen in training)."""
    cat = rng.choice(list(TEMPLATES))
    pool = TEMPLATES[cat][-1:] if held_out else TEMPLATES[cat][:-1]
    text = rng.choice(pool).format(prod=rng.choice(PRODUCTS), region=rng.choice(REGIONS),
                                   amt=rng.choice([49, 120, 480, 900, 2400]))
    urgency = rng.choice(URGENT)
    close = rng.choice(CLOSERS).format(acct=rng.randint(10000, 99999), ref=rng.randint(1000, 9999), name=rng.choice(NAMES))
    sev = min(5, BASE_SEV[cat] + (1 if urgency else 0))
    return {"ticket": rng.choice(OPENERS) + text + urgency + close, "category": cat, "severity": sev,
            "next_action": ACTION[cat]}


def as_chat(r: dict) -> dict:
    answer = {"category": r["category"], "severity": r["severity"], "next_action": r["next_action"]}
    return {"messages": [{"role": "system", "content": SYSTEM},
                         {"role": "user", "content": r["ticket"]},
                         {"role": "assistant", "content": json.dumps(answer)}]}


def main() -> None:
    rng = random.Random(7)
    seen: set[str] = set()

    def unique(n: int, held_out: bool) -> list[dict]:
        out = []
        while len(out) < n:
            r = make(rng, held_out)
            if r["ticket"] not in seen:          # de-duplicate across ALL splits
                seen.add(r["ticket"])
                out.append(r)
        return out

    train_pool = unique(970, held_out=False)
    splits = {
        "train": train_pool[:800],
        "valid": train_pool[800:900],
        # test = 70 unseen tickets in familiar phrasings + 30 in phrasings never seen in training
        "test": train_pool[900:970] + unique(30, held_out=True),
    }
    rng.shuffle(splits["test"])
    OUT.mkdir(exist_ok=True)
    for name, rs in splits.items():
        with (OUT / f"{name}.jsonl").open("w") as f:
            for r in rs:
                f.write(json.dumps(as_chat(r) if name != "test" else
                                   {k: r[k] for k in ("ticket", "category", "severity")}) + "\n")
        print(f"wrote {OUT / name}.jsonl  ({len(rs)} rows)")


if __name__ == "__main__":
    main()
