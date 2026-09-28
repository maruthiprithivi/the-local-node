"""
Lesson 08 · step 1 — turn the eval set into a Batch API input file.

One line per request: {"custom_id": ..., "body": {<normal chat-completions body>}}.
custom_id is how you join results back to labels — results may come back in any order.

    python make_batch.py                       # → batch_input.jsonl (100 tickets)
    python make_batch.py --model accounts/fireworks/models/gpt-oss-20b
"""
import argparse
import json
from pathlib import Path

from felab.tickets import SCHEMA, SYSTEM, load_test

HERE = Path(__file__).parent


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default=None, help="optional: some setups want the model per line")
    a = ap.parse_args()

    rows = load_test()
    out = HERE / "batch_input.jsonl"
    with out.open("w") as f:
        for i, r in enumerate(rows):
            body = {
                "messages": [{"role": "system", "content": SYSTEM + "\nSchema:\n" + json.dumps(SCHEMA)},
                             {"role": "user", "content": r["ticket"]}],
                "max_tokens": 120,
                "temperature": 0,
                "response_format": {"type": "json_schema", "json_schema": {"name": "triage", "schema": SCHEMA}},
            }
            if a.model:
                body["model"] = a.model
            f.write(json.dumps({"custom_id": f"t-{i:03d}", "body": body}) + "\n")
    print(f"wrote {out}  ({len(rows)} requests)")


if __name__ == "__main__":
    main()
