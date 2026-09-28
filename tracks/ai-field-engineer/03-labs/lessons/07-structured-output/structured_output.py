"""
Lesson 07 — structured output that doesn't break.

Enterprise integrations parse the model's reply with code. One stray "Sure! Here's
the JSON:" and the pipeline throws. Three ways to ask for JSON, from weakest to strongest:

  prompt       "Reply with JSON only"                  → the model *usually* complies
  json_object  response_format={"type":"json_object"}  → guaranteed JSON, any shape
  json_schema  response_format={"type":"json_schema"}  → guaranteed JSON *matching the schema*
               (constrained decoding: tokens that would break the schema are masked out)

We run N held-out tickets through each mode and report a validity RATE — a number
you can put in a customer doc, instead of "it seemed fine".

    python structured_output.py --target mock --n 50
    python structured_output.py --target llamacpp --modes prompt,json_schema
    python structured_output.py --target fireworks --n 50        # ~ $0.02

Reasoning models: some return their thinking separately and constrained decoding can
interfere with it; the documented pattern is schema in the prompt, and validate after.
"""
import argparse
import json
import time

from felab import add_target_args, banner, client, percentile, record, resolve, table
from felab.tickets import SCHEMA, SYSTEM, grade, load_test


def request_kwargs(mode: str) -> dict:
    if mode == "json_object":
        return {"response_format": {"type": "json_object"}}
    if mode == "json_schema":
        return {"response_format": {"type": "json_schema",
                                    "json_schema": {"name": "triage", "schema": SCHEMA, "strict": True}}}
    return {}


def run(cli, model: str, mode: str, rows: list[dict]) -> dict:
    # The schema goes in the prompt in EVERY mode: the model should know the shape it is
    # being held to, not just be forced into it.
    system = SYSTEM + "\nSchema:\n" + json.dumps(SCHEMA)
    g, lat = [], []
    for r in rows:
        t0 = time.perf_counter()
        try:
            resp = cli.chat.completions.create(model=model, temperature=0, max_tokens=120,
                                               messages=[{"role": "system", "content": system},
                                                         {"role": "user", "content": r["ticket"]}],
                                               **request_kwargs(mode))
            reply = resp.choices[0].message.content
        except Exception as e:  # some servers reject a mode they don't support — that's a finding too
            print(f"  {mode}: server rejected request ({type(e).__name__}: {str(e)[:80]})")
            return {"mode": mode, "n": 0}
        lat.append((time.perf_counter() - t0) * 1000)
        g.append(grade(reply, r))
    n = len(g)
    return {"mode": mode, "n": n,
            "parses_%": 100 * sum(x["parses"] for x in g) / n,
            "schema_valid_%": 100 * sum(x["valid"] for x in g) / n,
            "category_acc_%": 100 * sum(x["category_ok"] for x in g) / n,
            "p95_ms": percentile(lat, 95)}


def main() -> None:
    ap = add_target_args(argparse.ArgumentParser(description=__doc__,
                                                 formatter_class=argparse.RawDescriptionHelpFormatter))
    ap.add_argument("--n", type=int, default=50, help="tickets per mode")
    ap.add_argument("--modes", default="prompt,json_object,json_schema")
    a = ap.parse_args()
    t = resolve(a)
    banner(t)
    cli = client(t)
    rows = load_test(a.n)

    results = []
    for mode in a.modes.split(","):
        print(f"  {mode} …", flush=True)
        r = run(cli, t.model, mode, rows)
        if r["n"]:
            results.append(r)
            record("07-structured", {"target": t.name, "model": t.model.split("/")[-1], **r})
    print("\n" + table(results))
    print("\nschema_valid_% is the reliability number. category_acc_% is a different question\n"
          "(is the answer RIGHT?) — constrained decoding fixes the first, not the second. Lesson 09.")


if __name__ == "__main__":
    main()
