"""
Lesson 12 — infer a model's ACTIVE size from how fast it decodes.

A dense model reads all its weights for every token. A Mixture-of-Experts model has
many "expert" blocks but a router picks only a few per token, so it reads a fraction.
We can see that fraction from the outside, using nothing but a stopwatch:

    bytes read per token ≈ bandwidth (GB/s) ÷ measured decode tok/s
    active fraction      ≈ bytes per token ÷ file size

Uses Ollama's native API because it reports exact eval_count and eval_duration.

    ollama pull llama3.1:8b && ollama pull gpt-oss:20b      # ~5 GB + ~14 GB
    python moe_probe.py llama3.1:8b gpt-oss:20b
    python moe_probe.py --demo                               # sample numbers, no download
"""
import argparse
import json
import urllib.request

from felab import record, table
from felab.hardware import detect

OLLAMA = "http://localhost:11434"
# published totals / active params, for checking your inference (billions)
KNOWN = {"llama3.1:8b": (8.0, 8.0), "gpt-oss:20b": (21.0, 3.6), "qwen3:30b-a3b": (30.5, 3.3),
         "qwen3:30b": (30.5, 3.3), "gpt-oss:120b": (117.0, 5.1)}
EFFICIENCY = 0.75   # engines hit ~60–85% of peak bandwidth; we assume 75% when inverting
DEMO = [("llama3.1:8b", 4.9, 84.0), ("gpt-oss:20b", 13.8, 118.0)]   # M4 Max-like, illustrative


def _post(path: str, body: dict) -> dict:
    req = urllib.request.Request(OLLAMA + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read())


def file_gb(model: str) -> float:
    with urllib.request.urlopen(OLLAMA + "/api/tags", timeout=5) as r:
        for m in json.loads(r.read())["models"]:
            if m["name"] == model or m["name"] == model + ":latest":
                return m["size"] / 1e9
    raise SystemExit(f"{model} not pulled — run: ollama pull {model}")


def decode_tps(model: str) -> float:
    _post("/api/generate", {"model": model, "prompt": "hi", "stream": False, "options": {"num_predict": 4}})  # load
    r = _post("/api/generate", {"model": model, "stream": False, "options": {"num_predict": 200, "temperature": 0},
                                "prompt": "Write 150 words about why caches make computers fast."})
    return r["eval_count"] / (r["eval_duration"] / 1e9)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("models", nargs="*", default=["llama3.1:8b", "gpt-oss:20b"])
    ap.add_argument("--bw", type=float, help="GB/s (default: detect)")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    bw = a.bw or (546 if a.demo else detect()["bw_gbs"])
    if not bw:
        raise SystemExit("pass --bw <GB/s>")

    data = DEMO if a.demo else [(m, file_gb(m), decode_tps(m)) for m in a.models]
    rows = []
    for m, size, tps in data:
        read = bw * EFFICIENCY / tps                     # GB actually streamed per token
        total, active = KNOWN.get(m, (None, None))
        rows.append({"model": m, "file_gb": size, "tok_s": tps, "gb_per_token": read,
                     "active_%": 100 * min(1.0, read / size),
                     "published_%": 100 * active / total if total else float("nan")})
        record("12-moe", {"bw_gbs": bw, **rows[-1]})

    print(f"bandwidth {bw} GB/s × {EFFICIENCY:.0%} efficiency\n")
    print(table(rows))
    print("\nThe MoE file is ~3× bigger, yet it decodes FASTER: it only reads its active experts.\n"
          "Memory must hold ALL experts (file_gb); speed depends on ACTIVE bytes (gb_per_token).")


if __name__ == "__main__":
    main()
