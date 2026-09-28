"""
Lesson 17 · step 3 — one table: what each method cost, what it bought, what it broke.

From the training logs (works anywhere):
  trainable %, peak memory, final validation loss, wall time, checkpoint size on disk

From the models themselves (Apple silicon, needs mlx-lm):
  task accuracy     triage category on the 100 held-out tickets (30 in phrasings never trained on)
  general quiz      the 12 general questions from lesson 04, which checks for FORGETTING (video 14)

    python compare_variants.py               # logs + evaluation
    python compare_variants.py --logs-only   # skip the model evaluation
"""
import argparse
import importlib.util
import json
import re
from pathlib import Path

from felab import record, table
from felab.tickets import SCHEMA, SYSTEM, grade, load_test

HERE = Path(__file__).parent
MODEL = "mlx-community/Qwen2.5-0.5B-Instruct-bf16"


def parse_log(path: Path) -> dict:
    txt = path.read_text(errors="ignore")
    m = re.search(r"Trainable parameters:\s*([\d.]+)%\s*\(([\d.]+)M", txt)
    peaks = [float(x) for x in re.findall(r"Peak mem\s*([\d.]+)\s*GB", txt)]
    vals = re.findall(r"Val loss\s*([\d.]+)", txt)
    wall = re.search(r"wall_seconds\s+(\d+)", txt)
    return {
        "trainable_%": float(m.group(1)) if m else float("nan"),
        "trainable_M": float(m.group(2)) if m else float("nan"),
        "peak_mem_GB": max(peaks) if peaks else float("nan"),
        "val_loss": float(vals[-1]) if vals else float("nan"),
        "minutes": int(wall.group(1)) / 60 if wall else float("nan"),
    }


def dir_mb(p: Path) -> float:
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) / 1e6 if p.exists() else float("nan")


def evaluate(adapter: str | None) -> tuple[float, int]:
    """Greedy-decode the test tickets and the general quiz with mlx-lm."""
    from mlx_lm import generate, load
    model, tok = load(MODEL, adapter_path=adapter)

    def ask(messages, max_tokens):
        prompt = tok.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
        return generate(model, tok, prompt=prompt, max_tokens=max_tokens, verbose=False)

    rows = load_test()
    ok = sum(grade(ask([{"role": "system", "content": SYSTEM}, {"role": "user", "content": r["ticket"]}], 60), r)["category_ok"]
             for r in rows)
    spec = importlib.util.spec_from_file_location("q", HERE.parent / "04-quantization" / "quality_check.py")
    q = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(q)          # safe: its main() only runs under __main__
    quiz = sum(want.replace(" ", "").lower() in ask([{"role": "user", "content": qq}], 40).replace(" ", "").lower()
               for qq, want in q.QA)
    return 100 * ok / len(rows), quiz


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--logs-only", action="store_true")
    a = ap.parse_args()

    variants = [p.stem for p in sorted((HERE / "logs").glob("*.log"))]
    if not variants:
        raise SystemExit("No logs yet: run bash run_variants.sh first.")
    rows = []
    can_eval = not a.logs_only and importlib.util.find_spec("mlx_lm") is not None
    if can_eval:
        print("evaluating base model …", flush=True)
        acc, quiz = evaluate(None)
        rows.append({"variant": "base (no training)", "trainable_%": 0.0, "peak_mem_GB": float("nan"),
                     "val_loss": float("nan"), "minutes": 0.0, "ckpt_MB": 0.0, "task_acc_%": acc, "general_quiz": f"{quiz}/12"})
    for v in variants:
        r = {"variant": v, **parse_log(HERE / "logs" / f"{v}.log"), "ckpt_MB": dir_mb(HERE / "adapters" / v)}
        r.pop("trainable_M")
        if can_eval:
            print(f"evaluating {v} …", flush=True)
            acc, quiz = evaluate(str(HERE / "adapters" / v))
            r.update({"task_acc_%": acc, "general_quiz": f"{quiz}/12"})
        rows.append(r)
        record("17-variants", r)
    print("\n" + table(rows))
    print("\nRead across a row: what it cost (memory, minutes, MB) → what it bought (task accuracy) →"
          "\nwhat it broke (general quiz; a drop means forgetting). On a narrow task, LoRA and DoRA"
          "\nshould land near full fine-tuning at a fraction of the memory and checkpoint size.")
    if not can_eval:
        print("\n(model evaluation skipped: needs mlx-lm on Apple silicon)")


if __name__ == "__main__":
    main()
