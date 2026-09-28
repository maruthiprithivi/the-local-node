"""
Lesson 13 · step 3 — measure speculation on two kinds of traffic.

Runs 5 "structured" prompts (JSON, lists, code — predictable) and 5 "prose" prompts
(creative — unpredictable) and reports decode tok/s for each. Run it twice: against
the baseline server and the speculative one, with --label so the rows line up.

llama-server also returns `timings.draft_n` / `draft_n_accepted` on each response;
if present we print the acceptance rate α directly.

    bash serve_spec_llamacpp.sh off   &   python spec_bench.py --target llamacpp --label baseline
    bash serve_spec_llamacpp.sh       &   python spec_bench.py --target llamacpp --label spec
    python spec_bench.py --target fireworks --model "<model>#<deployment>" --label fw-spec
"""
import argparse
import time

from felab import add_target_args, banner, client, record, resolve, table

PROMPTS = {
    "structured": [
        "Return a JSON array of the 12 months, each as {\"n\": <number>, \"name\": \"<name>\"}.",
        "Write a Python function that returns the first 30 Fibonacci numbers, with a docstring.",
        "List the numbers from 1 to 60 separated by commas.",
        "Convert to JSON: name Ada, role engineer, city London, skills python sql go.",
        "Write an HTML table with 8 rows: country and capital for European countries.",
    ],
    "prose": [
        "Write a surreal short story about a lighthouse that collects lost umbrellas.",
        "Invent a new board game and describe its strangest rule.",
        "Write a poem about latency in the voice of a tired sea captain.",
        "Describe an alien market using only smells and sounds.",
        "Pitch a movie where the villain is a very polite fog.",
    ],
}


def main() -> None:
    ap = add_target_args(argparse.ArgumentParser(description=__doc__,
                                                 formatter_class=argparse.RawDescriptionHelpFormatter))
    ap.add_argument("--label", default="run")
    ap.add_argument("--max-tokens", type=int, default=256)
    a = ap.parse_args()
    t = resolve(a)
    banner(t)
    cli = client(t)
    extra = {"extra_body": {"perf_metrics_in_response": True}} if t.is_paid else {}

    rows = []
    for kind, prompts in PROMPTS.items():
        toks = secs = drafted = accepted = 0
        for p in prompts:
            t0 = time.perf_counter()
            r = cli.chat.completions.create(model=t.model, temperature=0, max_tokens=a.max_tokens,
                                            messages=[{"role": "user", "content": p}], **extra)
            secs += time.perf_counter() - t0
            toks += r.usage.completion_tokens if r.usage else 0
            timings = (r.model_extra or {}).get("timings") or {}           # llama.cpp
            drafted += timings.get("draft_n", 0)
            accepted += timings.get("draft_n_accepted", 0)
            pm = (r.model_extra or {}).get("perf_metrics")                  # Fireworks
            if pm and kind == "structured" and p == prompts[0]:
                print(f"  fireworks perf_metrics sample: {pm}")
        rows.append({"label": a.label, "traffic": kind, "tok_s": toks / secs if secs else 0.0,
                     "alpha": accepted / drafted if drafted else float("nan")})
        record("13-spec", {"target": t.name, **rows[-1]})

    print("\n" + table(rows))
    print("\nCompare tok_s between --label baseline and --label spec for each traffic type.")


if __name__ == "__main__":
    main()
