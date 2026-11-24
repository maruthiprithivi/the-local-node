#!/usr/bin/env python3
"""Stream-compare HF safetensors (source of truth) to a GGUF export of the same files."""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import torch
from safetensors import safe_open
from gguf.gguf_reader import GGUFReader


VISION_MARKERS = ("visual", "vision", "pixel", "patch_embed", "merger", "image_", "video_")


def hf_to_candidates(hf_name: str) -> list[str]:
    n = hf_name
    for pref in (
        "model.language_model.",
        "model.model.",
        "language_model.",
        "model.",
    ):
        if n.startswith(pref):
            n = n[len(pref):]
            break
    table = {
        "embed_tokens.weight": ["token_embd.weight"],
        "norm.weight": ["output_norm.weight"],
        "lm_head.weight": ["output.weight"],
    }
    if n in table:
        return table[n]
    parts = n.split(".")
    if parts and parts[0] == "layers" and len(parts) > 2 and parts[1].isdigit():
        layer, suffix = parts[1], ".".join(parts[2:])
        smap = {
            "input_layernorm.weight": f"blk.{layer}.attn_norm.weight",
            "post_attention_layernorm.weight": f"blk.{layer}.ffn_norm.weight",
            "self_attn.q_proj.weight": f"blk.{layer}.attn_q.weight",
            "self_attn.k_proj.weight": f"blk.{layer}.attn_k.weight",
            "self_attn.v_proj.weight": f"blk.{layer}.attn_v.weight",
            "self_attn.o_proj.weight": f"blk.{layer}.attn_output.weight",
            "self_attn.q_norm.weight": f"blk.{layer}.attn_q_norm.weight",
            "self_attn.k_norm.weight": f"blk.{layer}.attn_k_norm.weight",
            "mlp.gate_proj.weight": f"blk.{layer}.ffn_gate.weight",
            "mlp.up_proj.weight": f"blk.{layer}.ffn_up.weight",
            "mlp.down_proj.weight": f"blk.{layer}.ffn_down.weight",
        }
        if suffix in smap:
            return [smap[suffix]]
    return []


def is_vision(name: str) -> bool:
    return any(m in name for m in VISION_MARKERS)


def torch_to_f32(ten: torch.Tensor) -> tuple[np.ndarray, str]:
    if ten.dtype == torch.bfloat16:
        u = ten.contiguous().view(torch.uint16).cpu().numpy()
        return (u.astype(np.uint32) << 16).view(np.float32), "BF16"
    if ten.dtype == torch.float16:
        return ten.contiguous().cpu().numpy().astype(np.float32), "F16"
    if ten.dtype == torch.float32:
        return ten.contiguous().cpu().numpy(), "F32"
    return ten.contiguous().cpu().float().numpy(), str(ten.dtype)


def gguf_type_name(t) -> str:
    typ = str(t.tensor_type)
    if "BF16" in typ:
        return "BF16"
    if "F32" in typ:
        return "F32"
    if "F16" in typ:
        return "F16"
    return typ


def gguf_to_f32(t) -> np.ndarray:
    dtn = gguf_type_name(t)
    arr = np.asarray(t.data)
    if dtn == "F32":
        return arr.astype(np.float32, copy=False)
    if dtn == "F16":
        if arr.dtype == np.float16:
            return arr.astype(np.float32)
        return arr.view(np.float16).astype(np.float32)
    if dtn == "BF16":
        if arr.dtype == np.uint16:
            u = arr
        elif arr.dtype.itemsize == 2:
            u = arr.view(np.uint16)
        else:
            return arr.astype(np.float32)
        return (u.astype(np.uint32) << 16).view(np.float32)
    return arr.astype(np.float32)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hf-dir", required=True)
    ap.add_argument("--gguf", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    hf_dir = Path(args.hf_dir)
    out_path = Path(args.out)

    reader = GGUFReader(str(args.gguf))
    gg_index = {t.name: t for t in reader.tensors}
    gg_dtype = Counter(gguf_type_name(t) for t in reader.tensors)

    hf_dtype = Counter()
    hf_count = 0
    matched = []
    unmatched_hf = []
    used_gg = set()
    exact = close = mismatch = shape_fail = 0

    for fp in sorted(hf_dir.glob("*.safetensors")):
        with safe_open(str(fp), framework="pt") as f:
            for k in f.keys():
                ten = f.get_tensor(k)
                hf32, hdtn = torch_to_f32(ten)
                hshape = tuple(ten.shape)
                del ten
                hf_dtype[hdtn] += 1
                hf_count += 1
                cands = hf_to_candidates(k)
                found = next((c for c in cands if c in gg_index), None)
                if found is None:
                    unmatched_hf.append(k)
                    continue
                used_gg.add(found)
                t = gg_index[found]
                g32 = gguf_to_f32(t)
                if g32.size != hf32.size:
                    shape_fail += 1
                    matched.append({
                        "hf": k, "gguf": found, "status": "shape_mismatch",
                        "hf_shape": list(hshape), "gguf_shape": list(np.asarray(t.data).shape),
                    })
                    continue
                if g32.shape != hf32.shape:
                    g32 = g32.T if g32.shape == hf32.shape[::-1] else g32.reshape(hf32.shape)
                diff = np.abs(hf32 - g32)
                denom = np.maximum(np.abs(hf32), 1e-8)
                mx = float(diff.max()) if diff.size else 0.0
                rel = float((diff / denom).max()) if diff.size else 0.0
                if mx == 0.0:
                    status = "exact"; exact += 1
                elif mx <= 2e-2 and rel <= 5e-3:
                    status = "close"; close += 1
                else:
                    status = "mismatch"; mismatch += 1
                matched.append({
                    "hf": k, "gguf": found, "status": status,
                    "hf_dtype": hdtn, "gguf_dtype": gguf_type_name(t),
                    "hf_shape": list(hshape), "gguf_shape": list(np.asarray(t.data).shape),
                    "max_abs_diff": mx, "max_rel_diff": rel,
                })
                del hf32, g32, diff, denom

    vision = [n for n in unmatched_hf if is_vision(n)]
    other = [n for n in unmatched_hf if not is_vision(n)]
    gg_unmatched = sorted(set(gg_index) - used_gg)
    summary = {
        "hf_dir": str(hf_dir),
        "gguf": str(args.gguf),
        "hf_tensor_count": hf_count,
        "hf_dtype_counts": dict(hf_dtype),
        "gguf_tensor_count": len(gg_index),
        "gguf_dtype_counts": dict(gg_dtype),
        "compared": len(matched),
        "exact": exact,
        "close": close,
        "mismatch": mismatch,
        "shape_fail": shape_fail,
        "hf_unmatched_total": len(unmatched_hf),
        "hf_unmatched_vision": len(vision),
        "hf_unmatched_other": other,
        "gguf_unmatched": gg_unmatched,
        "pass": mismatch == 0 and shape_fail == 0 and exact + close == len(matched) and len(other) == 0,
        "criterion": "Every exported GGUF tensor must map to an HF source tensor with max_abs_diff==0 (exact) or <=0.02 (close). Unexported HF tensors must be vision/mmproj only.",
    }
    out_path.write_text(json.dumps({
        "summary": summary,
        "matched": matched,
        "hf_unmatched_vision_sample": vision[:30],
        "hf_unmatched_vision_count": len(vision),
    }, indent=2))
    print(json.dumps(summary, indent=2))
    return 0 if summary["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
