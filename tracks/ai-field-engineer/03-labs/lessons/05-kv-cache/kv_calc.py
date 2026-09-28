"""
Lesson 05 · step 1 — KV cache maths by hand (then check it against the server log).

For every token in every live conversation, each layer stores a Key and a Value vector:

    KV bytes per token = 2 (K and V) × layers × kv_heads × head_dim × bytes_per_value

Multiply by context length and concurrent users and you get the memory that is NOT
the model — and it is usually what runs out first.

    python kv_calc.py                                   # Llama-3.1-8B, 8k ctx, 1 user
    python kv_calc.py --model llama-3.1-70b --ctx 32768 --users 16
    python kv_calc.py --ctx 131072 --kv q8_0 --free-gb 20   # how many users fit?
"""
import argparse

# layers, kv_heads (GQA), head_dim — from each model's config.json
MODELS = {
    "llama-3.1-8b": (32, 8, 128),
    "llama-3.1-70b": (80, 8, 128),
    "qwen2.5-7b": (28, 4, 128),
    "mistral-7b": (32, 8, 128),
    "gpt-oss-20b": (24, 8, 64),
}
BYTES = {"f16": 2.0, "q8_0": 1.0625, "q4_0": 0.5625}   # llama.cpp block formats carry a small scale overhead


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default="llama-3.1-8b", choices=MODELS)
    ap.add_argument("--ctx", type=int, default=8192, help="tokens per conversation")
    ap.add_argument("--users", type=int, default=1, help="concurrent conversations")
    ap.add_argument("--kv", default="f16", choices=BYTES, help="KV cache precision")
    ap.add_argument("--free-gb", type=float, help="memory left after weights → max users")
    a = ap.parse_args()

    L, H, D = MODELS[a.model]
    per_tok = 2 * L * H * D * BYTES[a.kv]                     # bytes
    per_seq = per_tok * a.ctx
    total = per_seq * a.users

    print(f"{a.model}: {L} layers × {H} KV heads × {D} head dim, KV in {a.kv}\n")
    print(f"  per token         2 × {L} × {H} × {D} × {BYTES[a.kv]} B = {per_tok / 1024:,.0f} KiB")
    print(f"  per conversation  × {a.ctx:,} tokens            = {per_seq / 1e9:,.2f} GB")
    print(f"  all users         × {a.users} users               = {total / 1e9:,.2f} GB")

    if a.free_gb:
        fit = int(a.free_gb * 1e9 // per_seq)
        print(f"\n  with {a.free_gb} GB free for cache → {fit} concurrent conversations at {a.ctx:,} tokens")
        alt = int(a.free_gb * 1e9 // (per_seq / BYTES[a.kv] * BYTES['q8_0'])) if a.kv == "f16" else None
        if alt:
            print(f"  switch KV to q8_0                → {alt} conversations (≈2×) — the cheapest fix there is")

    print("\nNow compare with what llama-server reports:  bash context_ladder.sh")


if __name__ == "__main__":
    main()
