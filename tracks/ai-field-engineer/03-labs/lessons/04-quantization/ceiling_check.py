"""
Lesson 04 · step 2 — does the physics hold?

For each llama-bench result in bench/*.json:

    ceiling tok/s  = memory bandwidth (GB/s) ÷ model size (GB)
    efficiency     = measured tg128 ÷ ceiling       (expect 60–85%)

If efficiency is way below 60%, something else is the bottleneck: layers on the CPU
(-ngl too low), thermal throttling, or another app hogging memory bandwidth.

    python ceiling_check.py                 # auto-detects your Mac's bandwidth
    python ceiling_check.py --bw 546        # or tell it (GB/s)
    python ceiling_check.py --demo          # no downloads: sample numbers, see the shape
"""
import argparse
import json
from pathlib import Path

from felab import record, table
from felab.hardware import APPLE_BW, ceiling, detect

HERE = Path(__file__).parent

# Illustrative figures for an 8B model on an M4 Max (546 GB/s), used by --demo only.
DEMO = [
    {"quant": "Q8_0", "size_gb": 8.5, "pp512": 1150.0, "tg128": 52.0},
    {"quant": "Q4_K_M", "size_gb": 4.9, "pp512": 1050.0, "tg128": 86.0},
    {"quant": "Q3_K_M", "size_gb": 4.0, "pp512": 980.0, "tg128": 98.0},
]


def load_bench() -> list[dict]:
    """Parse llama-bench -o json files into {quant, size_gb, pp512, tg128}."""
    rows = []
    for f in sorted((HERE / "bench").glob("*.json")):
        runs = json.loads(f.read_text())
        pp = next((r["avg_ts"] for r in runs if r.get("n_prompt", 0) > 0 and r.get("n_gen", 0) == 0), 0)
        tg = next((r["avg_ts"] for r in runs if r.get("n_gen", 0) > 0 and r.get("n_prompt", 0) == 0), 0)
        size = runs[0].get("model_size", 0) / 1e9
        rows.append({"quant": f.stem, "size_gb": size, "pp512": pp, "tg128": tg})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bw", type=float, help="memory bandwidth GB/s (default: detect)")
    ap.add_argument("--demo", action="store_true", help="use built-in sample numbers")
    a = ap.parse_args()

    bw = a.bw or (546 if a.demo else detect()["bw_gbs"])
    if not bw:
        raise SystemExit(f"Unknown bandwidth — pass --bw. Apple chips: {APPLE_BW}")
    rows = DEMO if a.demo else load_bench()
    if not rows:
        raise SystemExit("No bench/*.json yet — run quant_bench.sh (or try --demo).")

    out = []
    for r in rows:
        ceil = ceiling(bw, r["size_gb"])
        out.append({**r, "ceiling": ceil, "efficiency_%": 100 * r["tg128"] / ceil})
        record("04-quant", {"bw_gbs": bw, **out[-1]})

    print(f"memory bandwidth: {bw} GB/s\n")
    print(table(out))
    print("\nRead it like this:")
    print("  • tg128 (decode) scales with 1/size — halve the bytes, nearly double the speed.")
    print("  • pp512 (prefill) barely moves — prefill is compute-bound, not bandwidth-bound.")
    print("  • Now run quality_check.py per quant: speed without a quality check is meaningless.")


if __name__ == "__main__":
    main()
