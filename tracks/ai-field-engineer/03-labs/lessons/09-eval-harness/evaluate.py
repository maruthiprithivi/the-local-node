"""
Lesson 09 — the eval harness: quality, latency and cost in ONE table.

"The fine-tune seems better" is not a decision. This is:

    candidate          schema_valid  category  severity  judge  p95_ms  $/1k tasks
    fireworks gpt-oss-20b    100%       81%       74%     3.9    640     $0.042
    mlx triage-lora          100%       96%       93%     4.3    310     $0 (your Mac)

Each candidate is "target:model[@in_price/out_price]" — prices in $ per 1M tokens,
copied from the provider's pricing page (local = free, so omit).

Graders (cheap → expensive):
  1. schema_valid   code — does the JSON match the contract?
  2. category/severity accuracy   code — against held-out labels
  3. judge          an LLM with a rubric scores next_action 1–5 (--judge target:model)
                    Use for fields with no single right answer. Spot-check it by hand!

    python evaluate.py mock:mock-8b mock:mock-8b-lora --n 60
    python evaluate.py ollama "fireworks:accounts/fireworks/models/gpt-oss-20b@0.07/0.30" \
                       --judge fireworks --n 50
"""
import argparse
import json
import time

from felab import TARGETS, client, percentile, record, table
from felab.targets import Target, resolve
from felab.tickets import SCHEMA, SYSTEM, grade, load_test, parse

RUBRIC = """You are grading a support-triage assistant. Ticket:
{ticket}
Proposed next_action: {action}
Rubric: 5 = specific, correct owner, safe; 3 = plausible but vague; 1 = wrong or unsafe.
Reply with JSON only: {{"score": <1-5>}}"""


def parse_candidate(spec: str) -> tuple[Target, float, float]:
    """'fireworks:accounts/x/y@0.07/0.30' → (Target, in $/M, out $/M)."""
    price_in = price_out = 0.0
    if "@" in spec:
        spec, price = spec.rsplit("@", 1)
        price_in, price_out = (float(x) for x in price.split("/"))
    name, _, model = spec.partition(":")
    if name not in TARGETS:
        raise SystemExit(f"unknown target '{name}' — choose from {list(TARGETS)}")
    ns = argparse.Namespace(target=name, model=model or None, base_url=None)
    return resolve(ns), price_in, price_out


def judge_score(jcli, jmodel: str, ticket: str, action: str) -> float | None:
    r = jcli.chat.completions.create(model=jmodel, temperature=0, max_tokens=20,
                                     messages=[{"role": "user", "content": RUBRIC.format(ticket=ticket, action=action)}])
    obj = parse(r.choices[0].message.content)
    s = obj.get("score") if obj else None
    return float(s) if isinstance(s, (int, float)) and 1 <= s <= 5 else None


def evaluate(t: Target, pin: float, pout: float, rows: list[dict], judge) -> dict:
    cli = client(t)
    system = SYSTEM + "\nSchema:\n" + json.dumps(SCHEMA)
    grades, lat, judged = [], [], []
    tok_in = tok_out = 0
    for r in rows:
        t0 = time.perf_counter()
        resp = cli.chat.completions.create(
            model=t.model, temperature=0, max_tokens=120,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": r["ticket"]}],
            response_format={"type": "json_schema", "json_schema": {"name": "triage", "schema": SCHEMA}})
        lat.append((time.perf_counter() - t0) * 1000)
        reply = resp.choices[0].message.content
        grades.append(grade(reply, r))
        u = resp.usage
        tok_in += u.prompt_tokens if u else len(system + r["ticket"]) // 4
        tok_out += u.completion_tokens if u else len(reply or "") // 4
        if judge and (obj := parse(reply)) and obj.get("next_action"):
            judged.append(judge_score(judge[0], judge[1], r["ticket"], obj["next_action"]))
    n = len(rows)
    js = [j for j in judged if j is not None]
    cost_per_task = (tok_in * pin + tok_out * pout) / 1e6 / n
    return {
        "candidate": f"{t.name} {t.model.split('/')[-1]}",
        "schema_valid_%": 100 * sum(g["valid"] for g in grades) / n,
        "category_%": 100 * sum(g["category_ok"] for g in grades) / n,
        "severity_%": 100 * sum(g["severity_ok"] for g in grades) / n,
        "judge_1to5": sum(js) / len(js) if js else float("nan"),
        "p95_ms": percentile(lat, 95),
        "usd_per_1k": cost_per_task * 1000,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("candidates", nargs="+", help='e.g. mock:mock-8b  "fireworks:<model>@0.07/0.30"')
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--judge", help="target[:model] for the LLM judge (optional)")
    a = ap.parse_args()
    rows = load_test(a.n)

    judge = None
    if a.judge:
        jt, _, _ = parse_candidate(a.judge)
        judge = (client(jt), jt.model)

    out = []
    for spec in a.candidates:
        t, pin, pout = parse_candidate(spec)
        print(f"  evaluating {t.name} {t.model} on {len(rows)} tickets…", flush=True)
        out.append(evaluate(t, pin, pout, rows, judge))
        record("09-eval", {"n": len(rows), **out[-1]})

    print("\n" + table(out))
    best = max(out, key=lambda r: (r["category_%"], -r["usd_per_1k"]))
    print(f"\nHighest accuracy: {best['candidate']}. Now read across: is the gain worth the latency and $?")


if __name__ == "__main__":
    main()
