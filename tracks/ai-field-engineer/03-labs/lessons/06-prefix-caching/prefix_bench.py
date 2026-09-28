"""
Lesson 06 — prefix caching on an agent-shaped workload.

Agents resend the same big preamble (instructions + tool definitions + docs) on
every call and change only the last few lines. If the server remembers the KV
cache for that preamble, it skips re-reading it: TTFT collapses and, on Fireworks,
cached input tokens are billed at a steep discount.

This script sends 12 different questions two ways:

  --order stable-first    [ 3k-token preamble ][ question ]     ← cache-friendly
  --order variable-first  [ question + timestamp ][ preamble ]  ← one changed token early
                                                                   invalidates everything after it

    python prefix_bench.py --target mock
    python prefix_bench.py --target mock --order variable-first
    python prefix_bench.py --target llamacpp            # llama-server reuses slot caches
    python prefix_bench.py --target fireworks --usage   # ~$0.03; prints cached_tokens
"""
import argparse
import datetime as dt

from felab import add_target_args, banner, client, percentile, record, resolve, stream_once, table

TOOLS = "\n".join(
    f"- tool `{name}`: {desc}. Arguments: JSON object with fields id (string), limit (int), filters (object)."
    for name, desc in [("search_tickets", "full-text search over support tickets"),
                       ("get_invoice", "fetch an invoice by id"), ("refund", "issue a refund up to the limit"),
                       ("status_page", "read current incident status"), ("escalate", "page the on-call engineer")])
POLICY = ("Refunds over $500 need manager approval. Outages affecting more than 5% of users are SEV-2. "
          "Never reveal internal ticket ids. Answer in under 80 words. ") * 75
PREAMBLE = f"You are the support agent for Acme Cloud.\n\n## Tools\n{TOOLS}\n\n## Policy\n{POLICY}"

QUESTIONS = [
    "A customer was charged twice this month. What do I do?", "Is there an outage in eu-west right now?",
    "How do I rotate my API key?", "Customer wants a $900 refund — can I approve it?",
    "What counts as a SEV-2?", "Can I share the internal ticket id with the customer?",
    "Which tool finds old tickets about SSO?", "Latency spiked at 09:00 — who do I page?",
    "The customer asks for their March invoice.", "How long should my answer be?",
    "Card declined on renewal, launch is tomorrow.", "Summarise the refund policy in one line.",
]


def messages(q: str, order: str) -> list[dict]:
    if order == "stable-first":
        return [{"role": "system", "content": PREAMBLE}, {"role": "user", "content": q}]
    # anti-pattern: something that changes every call goes FIRST
    stamp = dt.datetime.now().isoformat(timespec="microseconds")
    return [{"role": "system", "content": f"Request time {stamp}. User asks: {q}\n\n{PREAMBLE}"},
            {"role": "user", "content": q}]


def main() -> None:
    ap = add_target_args(argparse.ArgumentParser(description=__doc__,
                                                 formatter_class=argparse.RawDescriptionHelpFormatter))
    ap.add_argument("--order", choices=["stable-first", "variable-first"], default="stable-first")
    ap.add_argument("--usage", action="store_true", help="one extra non-streamed call to print cached_tokens")
    a = ap.parse_args()
    t = resolve(a)
    banner(t)
    cli = client(t)

    # `user` = session affinity on Fireworks: keeps you on the replica that holds your cache.
    extra = {"user": "lesson-06-session"} if t.is_paid else {}
    print(f"preamble ≈ {len(PREAMBLE) // 4:,} tokens · order = {a.order}\n")

    ttft = []
    for i, q in enumerate(QUESTIONS):
        s = stream_once(cli, t.model, messages(q, a.order), max_tokens=48, **extra)
        ttft.append(s.ttft_ms)
        print(f"  call {i + 1:2d}  TTFT {s.ttft_ms:7.0f} ms  {'(cold)' if i == 0 else ''}")

    row = {"target": t.name, "order": a.order, "first_ms": ttft[0],
           "rest_p50_ms": percentile(ttft[1:], 50), "speedup_x": ttft[0] / max(1e-6, percentile(ttft[1:], 50))}
    print("\n" + table([row]))
    record("06-prefix", row)

    if a.usage:
        r = cli.chat.completions.create(model=t.model, max_tokens=8,
                                        messages=messages("One more question.", a.order), **extra)
        u = r.usage
        cached = getattr(getattr(u, "prompt_tokens_details", None), "cached_tokens", None)
        print(f"\nusage: prompt_tokens={u.prompt_tokens}  cached_tokens={cached}")
        print("Cost check: cached input is billed at a fraction of normal input — see the model's pricing page.")


if __name__ == "__main__":
    main()
