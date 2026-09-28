"""
Lesson 08 · step 3 — join batch results back to labels and score them.

    python score_batch.py results.jsonl          # a downloaded Fireworks output file
    python score_batch.py --simulate --target mock
        # no Fireworks needed: runs batch_input.jsonl through any target synchronously
        # and writes simulated_results.jsonl in the same shape, then scores it

The output file format can differ slightly between providers and versions, so we
don't hard-code a path to the answer: we find `custom_id`, then the first assistant
`content` string anywhere inside that line.
"""
import argparse
import json
from pathlib import Path

from felab import add_target_args, client, record, resolve, table
from felab.tickets import grade, load_test

HERE = Path(__file__).parent


def find_content(obj):
    """Depth-first search for choices[..].message.content (or any 'content' string)."""
    if isinstance(obj, dict):
        msg = obj.get("message")
        if isinstance(msg, dict) and isinstance(msg.get("content"), str):
            return msg["content"]
        for v in obj.values():
            c = find_content(v)
            if c is not None:
                return c
    elif isinstance(obj, list):
        for v in obj:
            c = find_content(v)
            if c is not None:
                return c
    return None


def simulate(args) -> Path:
    t = resolve(args)
    cli = client(t)
    out = HERE / "simulated_results.jsonl"
    with out.open("w") as f:
        for line in (HERE / "batch_input.jsonl").read_text().splitlines():
            req = json.loads(line)
            body = {k: v for k, v in req["body"].items() if k != "model"}
            resp = cli.chat.completions.create(model=t.model, **body)
            f.write(json.dumps({"custom_id": req["custom_id"], "response": resp.model_dump()}) + "\n")
    print(f"simulated {out}")
    return out


def main() -> None:
    ap = add_target_args(argparse.ArgumentParser(description=__doc__,
                                                 formatter_class=argparse.RawDescriptionHelpFormatter))
    ap.add_argument("results", nargs="?", help="downloaded results .jsonl")
    ap.add_argument("--simulate", action="store_true")
    a = ap.parse_args()
    path = simulate(a) if a.simulate else Path(a.results or "")
    if not path.is_file():
        raise SystemExit("Pass a results file, or --simulate.")

    labels = {f"t-{i:03d}": r for i, r in enumerate(load_test())}
    grades = []
    for line in path.read_text().splitlines():
        rec = json.loads(line)
        cid = rec.get("custom_id")
        if cid in labels:
            grades.append(grade(find_content(rec), labels[cid]))
    n = len(grades)
    row = {"file": path.name, "answered": n, "of": len(labels),
           "schema_valid_%": 100 * sum(g["valid"] for g in grades) / max(1, n),
           "category_acc_%": 100 * sum(g["category_ok"] for g in grades) / max(1, n),
           "severity_acc_%": 100 * sum(g["severity_ok"] for g in grades) / max(1, n)}
    print(table([row]))
    record("08-batch", row)


if __name__ == "__main__":
    main()
