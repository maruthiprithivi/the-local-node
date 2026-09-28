"""
Lesson 03 — concurrency sweep: the curve that sizes a deployment.

Single-user speed sells hardware. Concurrency curves size deployments.

For each concurrency level C (1, 2, 4, 8, 16, 32) we keep C requests in flight and
measure:
  agg tok/s     total tokens per second across everyone  → goes UP with C (batching)
  per-user tok/s what one user sees                       → goes DOWN slowly
  TTFT p95      tail wait for the first token              → flat, then a KNEE (queueing)
  goodput       requests/s that met the SLO                → the number to sell

The capacity of one replica = the highest C where TTFT p95 is still under your SLO.

    python sweep.py --target mock
    python sweep.py --target mock --levels 1,2,4,8,16,32 --slo-ms 1000
    python sweep.py --target llamacpp          # start it with --parallel 8 for a fair fight
    python plot_sweep.py                       # draws the chart from results/
"""
import argparse
import asyncio
import time

from felab import add_target_args, astream_once, banner, client, percentile, record, resolve, table, user

TOPICS = ["caching", "batching", "quantization", "attention", "tokenizers", "GPUs", "speculation", "MoE"]


async def run_level(cli, model: str, conc: int, total: int, max_tokens: int, slo_ms: float) -> dict:
    """Fire `total` requests with at most `conc` in flight at any moment."""
    sem = asyncio.Semaphore(conc)

    async def worker(i: int):
        async with sem:  # the semaphore IS the concurrency level
            # Unique prompts so the prefix cache doesn't flatter us (see lesson 06).
            prompt = f"#{i} Summarise the idea of {TOPICS[i % len(TOPICS)]} for a new engineer in 80 words."
            return await astream_once(cli, model, user(prompt), max_tokens=max_tokens)

    t0 = time.perf_counter()
    samples = await asyncio.gather(*(worker(i) for i in range(total)))
    wall = time.perf_counter() - t0

    ttft = [s.ttft_ms for s in samples]
    tokens = sum(s.tokens for s in samples)
    per_user = percentile([s.decode_tps for s in samples if s.decode_tps], 50)
    ok = sum(1 for s in samples if s.ttft_ms <= slo_ms)
    return {
        "conc": conc,
        "agg_tok_s": tokens / wall,
        "user_tok_s": per_user,
        "ttft_p50": percentile(ttft, 50),
        "ttft_p95": percentile(ttft, 95),
        "goodput_rps": ok / wall,        # only requests that met the SLO count
    }


async def main_async(args) -> None:
    t = resolve(args)
    banner(t)
    cli = client(t, asynchronous=True)
    await astream_once(cli, t.model, user("warm up"), max_tokens=4)

    rows = []
    for conc in [int(x) for x in args.levels.split(",")]:
        total = max(args.min_requests, conc * 3)   # enough requests to reach steady state
        print(f"  running C={conc:>3} ({total} requests)…", flush=True)
        r = await run_level(cli, t.model, conc, total, args.max_tokens, args.slo_ms)
        rows.append(r)
        record("03-sweep", {"target": t.name, "model": t.model.split("/")[-1], "slo_ms": args.slo_ms, **r})

    print("\n" + table(rows))
    fits = [r["conc"] for r in rows if r["ttft_p95"] <= args.slo_ms]
    if fits:
        best = max(fits)
        print(f"\nCapacity line: TTFT p95 ≤ {args.slo_ms:.0f} ms holds up to C={best} concurrent users on this replica.")
    else:
        print(f"\nEven C=1 misses the {args.slo_ms:.0f} ms SLO — the model or hardware is too slow for this target.")
    print("Plot it:  python plot_sweep.py")


def main() -> None:
    ap = add_target_args(argparse.ArgumentParser(description=__doc__,
                                                 formatter_class=argparse.RawDescriptionHelpFormatter))
    ap.add_argument("--levels", default="1,2,4,8,16,32")
    ap.add_argument("--slo-ms", type=float, default=1000, help="TTFT p95 target (default 1000)")
    ap.add_argument("--max-tokens", type=int, default=128)
    ap.add_argument("--min-requests", type=int, default=12)
    asyncio.run(main_async(ap.parse_args()))


if __name__ == "__main__":
    main()
