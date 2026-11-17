"""Write judgments.jsonl, the shippable copy of out/llm_judgments.jsonl.

Keeps every field needed to replay the run (prompt hash, kind, model, time, finish_reason,
raw answer, parsed answer) and drops the prompts, which quote the raw private logs.
Session ids are replaced by the same short sha1 ids used in validation.csv.
`run.py --offline` reads this file when out/llm_judgments.jsonl is absent."""
import hashlib, json, os
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = os.path.join(HERE, "out", "llm_judgments.jsonl")
dst = os.path.join(HERE, "judgments.jsonl")
n = 0
with open(dst, "w") as f:
    for line in open(src):
        d = json.loads(line)
        if d.get("parsed") is None:
            continue
        f.write(json.dumps({"hash": d["hash"], "kind": d["kind"],
                            "session": hashlib.sha1(d["sid"].encode()).hexdigest()[:8],
                            "model": d["model"], "t": d["t"], "finish_reason": d["finish_reason"],
                            "response": d["response"], "parsed": d["parsed"]}) + "\n")
        n += 1
print(n, "judgments ->", dst)
