"""
Lesson 01 — the latency harness you will reuse in every later lesson.

It sends the same prompt N times, one at a time, and reports:
  TTFT p50 / p95   how long until the first token  (prefill + queue)
  ITL  median      gap between tokens               (one decode step)
  tok/s            what ONE user sees once text is flowing (= 1000 / ITL)

Try it:
    python bench_ttft.py --target mock
    python bench_ttft.py --target mock --prompt-tokens 8000     # TTFT jumps, ITL doesn't
    python bench_ttft.py --target mock --prompt-tokens 8000 --warm-cache   # sneak peek of lesson 06
    python bench_ttft.py --target ollama
    python bench_ttft.py --target fireworks --runs 5            # ~ $0.01

The lesson hides in the second line: a longer prompt makes TTFT worse (more to
prefill) but leaves ITL flat (each new token costs about the same). Two different
bottlenecks, so two different numbers.
"""
import argparse

from felab import add_target_args, banner, client, percentile, record, resolve, stream_once, table, user

QUESTION = "Explain KV caching to a CFO in about 120 words."
FILLER = ("Context paragraph about a customer's support history, product catalogue and policies. " * 400)


def build_prompt(prompt_tokens: int) -> str:
    """Pad the question with filler until it is roughly `prompt_tokens` long (~4 chars/token).
    Padding goes FIRST and the question LAST, which is how real RAG prompts look."""
    if prompt_tokens <= 50:
        return QUESTION
    pad = FILLER[: prompt_tokens * 4]
    return f"{pad}\n\nUsing the context above if useful: {QUESTION}"


def main() -> None:
    ap = add_target_args(argparse.ArgumentParser(description=__doc__,
                                                 formatter_class=argparse.RawDescriptionHelpFormatter))
    ap.add_argument("--runs", type=int, default=10, help="sequential requests (default 10)")
    ap.add_argument("--prompt-tokens", type=int, default=0, help="pad prompt to ~N tokens (e.g. 8000)")
    ap.add_argument("--max-tokens", type=int, default=192)
    ap.add_argument("--warm-cache", action="store_true",
                    help="reuse the identical prompt so the server's prefix cache can hit (see lesson 06)")
    args = ap.parse_args()

    t = resolve(args)
    banner(t)
    cli = client(t)
    prompt = build_prompt(args.prompt_tokens)

    # 1 warm-up request: loads the model / opens connections. Never count the first call.
    stream_once(cli, t.model, user("Say hi."), max_tokens=8)

    samples = []
    for i in range(args.runs):
        # Servers cache prompt prefixes (lesson 06). A unique tag at the very START makes
        # every run a cold prefill, so TTFT measures real prefill — unless --warm-cache.
        p = prompt if args.warm_cache else f"[run {i}-{id(samples)}] {prompt}"
        s = stream_once(cli, t.model, user(p), max_tokens=args.max_tokens)
        samples.append(s)
        print(f"  run {i + 1:2d}: TTFT {s.ttft_ms:7.0f} ms   ITL {s.itl_median:5.1f} ms   {s.tokens} tokens")

    ttfts = [s.ttft_ms for s in samples]
    itl = percentile([x for s in samples for x in s.itl_ms], 50)
    row = {
        "target": t.name, "model": t.model.split("/")[-1], "prompt_tok": args.prompt_tokens or 12,
        "ttft_p50_ms": percentile(ttfts, 50), "ttft_p95_ms": percentile(ttfts, 95),
        "itl_ms": itl, "tok_per_s": 1000 / itl if itl else 0.0,
    }
    print("\n" + table([row]))
    print(f"\nsaved → {record('01-latency', row)}")


if __name__ == "__main__":
    main()
