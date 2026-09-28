"""
Lesson 18 · step 4 — did preference tuning move what we wanted, and break anything?

Behaviour on the 100 held-out tickets (any --target: mock, mlx, fireworks …):
  valid_%     strict JSON that matches the schema          ← DPO should push this up
  chatty_%    answers wrapped in chat ("Sure! …") or prose ← and this down
  category_%  right category                               ← must not drop (taste can cost correctness)
  severity_%  right severity
  avg_chars   answer length                                 ← watch for length drift

Pairwise, on the validation pairs (Apple silicon, --pairwise MODEL [--adapter PATH]):
  pref_acc_%  how often the model finds CHOSEN more likely than REJECTED (log-prob sum)
  margin      mean log-prob gap: DPO's implicit reward. It should grow after training.

    python pref_eval.py --target mock --label mock
    python pref_eval.py --target mlx --label before
    python pref_eval.py --pairwise mlx-community/Qwen2.5-0.5B-Instruct-bf16 --adapter adapters/dpo
"""
import argparse
import json
from pathlib import Path

from felab import add_target_args, banner, client, record, resolve, table
from felab.tickets import SYSTEM, grade, load_test, parse

HERE = Path(__file__).parent


def behaviour(a) -> dict:
    t = resolve(a)
    banner(t)
    cli = client(t)
    rows = load_test()
    g, lengths, chatty = [], [], 0
    for r in rows:
        resp = cli.chat.completions.create(model=t.model, temperature=0, max_tokens=120,
                                           messages=[{"role": "system", "content": SYSTEM},
                                                     {"role": "user", "content": r["ticket"]}])
        out = (resp.choices[0].message.content or "").strip()
        g.append(grade(out, r))
        lengths.append(len(out))
        chatty += parse(out) is None       # not parseable as a bare JSON object → chat or prose
    n = len(rows)
    return {"label": a.label, "target": t.name,
            "valid_%": 100 * sum(x["valid"] for x in g) / n, "chatty_%": 100 * chatty / n,
            "category_%": 100 * sum(x["category_ok"] for x in g) / n,
            "severity_%": 100 * sum(x["severity_ok"] for x in g) / n,
            "avg_chars": sum(lengths) / n}


def pairwise(model_path: str, adapter: str | None, limit: int) -> dict:
    """Sum of token log-probs of each response given the prompt: DPO's own currency."""
    import mlx.core as mx
    from mlx_lm import load
    model, tok = load(model_path, adapter_path=adapter)

    def logprob(system: str, prompt: str, response: str) -> float:
        p_txt = tok.apply_chat_template([{"role": "system", "content": system}, {"role": "user", "content": prompt}],
                                        add_generation_prompt=True, tokenize=False)
        p_ids = tok.encode(p_txt)
        r_ids = tok.encode(response, add_special_tokens=False)
        ids = p_ids + r_ids
        logits = model(mx.array([ids[:-1]]))[0]
        logp = logits - mx.logsumexp(logits, axis=-1, keepdims=True)
        tgt = mx.array(ids[1:])
        tok_lp = mx.take_along_axis(logp, tgt[:, None], axis=-1)[:, 0]
        return tok_lp[len(p_ids) - 1:].sum().item()     # only the response tokens

    pairs = [json.loads(line) for line in (HERE / "data/mlx/valid.jsonl").read_text().splitlines()][:limit]
    margins = [logprob(p["system"], p["prompt"], p["chosen"]) - logprob(p["system"], p["prompt"], p["rejected"])
               for p in pairs]
    return {"label": f"pairwise {'+' + Path(adapter).name if adapter else 'base'}",
            "pref_acc_%": 100 * sum(m > 0 for m in margins) / len(margins),
            "margin": sum(margins) / len(margins), "pairs": len(margins)}


def main() -> None:
    ap = add_target_args(argparse.ArgumentParser(description=__doc__,
                                                 formatter_class=argparse.RawDescriptionHelpFormatter))
    ap.add_argument("--label", default="run")
    ap.add_argument("--pairwise", metavar="MODEL", help="local MLX model path/repo for log-prob scoring")
    ap.add_argument("--adapter", help="adapter path for --pairwise (e.g. adapters/dpo)")
    ap.add_argument("--limit", type=int, default=100)
    a = ap.parse_args()
    row = pairwise(a.pairwise, a.adapter, a.limit) if a.pairwise else behaviour(a)
    print("\n" + table([row]))
    record("18-pref", row)
    if not a.pairwise:
        print("\nRun it before and after DPO with different --label values; results/18-pref.csv keeps both.")


if __name__ == "__main__":
    main()
