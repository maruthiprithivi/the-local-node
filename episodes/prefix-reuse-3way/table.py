#!/usr/bin/env python3
"""Print the headline table from analyzer summaries (default: summaries/)."""
import json, sys
from pathlib import Path
d = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent / "summaries")
print("| engine | prefix | cold TTFT p50 (s) | repeated TTFT p50 (s) | repeated hit fraction | cold/repeated | reuse shown |")
print("|---|---:|---:|---:|---:|---:|---|")
for e, name in [("vllm", "vLLM"), ("sglang", "SGLang"), ("ollama", "Ollama")]:
    for r in json.loads((d / f"{e}-summary.json").read_text()):
        print(f"| {name} | {r['prefix_tokens']} | {r['cold_ttft_p50_s']:.4f} | {r['repeated_ttft_p50_s']:.4f} | "
              f"{r['repeated_token_hit_fraction']:.4f} | {r['ratio_of_median_cold_to_repeated']:.2f}x | "
              f"{'yes' if r['positive_reuse_demonstrated'] else 'no'} |")
