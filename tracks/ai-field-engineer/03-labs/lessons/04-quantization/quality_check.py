"""
Lesson 04 · step 3 — a 12-question sanity check per quantization level.

Not a benchmark: a smoke alarm. If Q3 gets 7/12 where Q8 gets 11/12, you have found
the cliff. For a customer you would swap these questions for 50 of THEIR prompts
(lesson 09 builds that harness properly).

Serve one quant at a time, then run:
    bash ../02-three-local-servers/serve_llamacpp.sh Q3_K_M
    python quality_check.py --target llamacpp --label Q3_K_M
"""
import argparse

from felab import add_target_args, banner, client, record, resolve

# (question, substring that must appear in a correct answer). Mixed: arithmetic,
# facts, multi-step reasoning, format-following — low-bit quants fail the last two first.
QA = [
    ("What is 17 * 23? Answer with the number only.", "391"),
    ("What is the capital of Australia? One word.", "Canberra"),
    ("If a train leaves at 14:40 and the trip takes 95 minutes, when does it arrive? HH:MM only.", "16:15"),
    ("Spell 'bandwidth' backwards. Letters only.", "htdiwdnab"),
    ("How many bytes are in one FP16 number? Digit only.", "2"),
    ("Return exactly this JSON and nothing else: {\"ok\": true}", "\"ok\": true"),
    ("What is 2 to the power of 10? Number only.", "1024"),
    ("Which planet is known as the Red Planet? One word.", "Mars"),
    ("Alice is taller than Bob. Bob is taller than Carol. Who is shortest? One word.", "Carol"),
    ("Convert 3.5 GB to MB using 1 GB = 1000 MB. Number only.", "3500"),
    ("What is the chemical symbol for sodium? Symbol only.", "Na"),
    ("List the first three prime numbers separated by commas, nothing else.", "2, 3, 5"),
]


def main() -> None:
    ap = add_target_args(argparse.ArgumentParser(description=__doc__,
                                                 formatter_class=argparse.RawDescriptionHelpFormatter))
    ap.add_argument("--label", default="?", help="what is being served, e.g. Q4_K_M")
    a = ap.parse_args()
    t = resolve(a)
    banner(t)
    cli = client(t)

    score = 0
    for q, want in QA:
        r = cli.chat.completions.create(model=t.model, temperature=0, max_tokens=40,
                                        messages=[{"role": "user", "content": q}])
        got = (r.choices[0].message.content or "").strip()
        ok = want.replace(" ", "").lower() in got.replace(" ", "").lower()
        score += ok
        print(f"  {'✓' if ok else '✗'} {q[:60]:60s} → {got[:40]!r}")

    print(f"\n{a.label}: {score}/{len(QA)}")
    record("04-quality", {"target": t.name, "label": a.label, "score": score, "of": len(QA)})


if __name__ == "__main__":
    main()
