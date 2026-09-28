"""
felab.hardware — detect the machine and know its memory bandwidth.

Why bandwidth? During decode, every new token requires reading (roughly) all
active weights from memory once. So:

    decode ceiling (tok/s) ≈ memory bandwidth (GB/s) ÷ bytes read per token (GB)

That single line explains why quantization, MoE and batching matter. Lessons 04
and 12 compare this ceiling with what you measure (expect 60–85% of it).
"""
from __future__ import annotations

import platform
import re
import subprocess

# Approximate peak unified-memory bandwidth, GB/s. Where a chip ships in two
# bandwidth bins (e.g. M3 Max, M4 Max) we list the higher one — check yours.
APPLE_BW = {
    "M1": 68, "M1 Pro": 200, "M1 Max": 400, "M1 Ultra": 800,
    "M2": 100, "M2 Pro": 200, "M2 Max": 400, "M2 Ultra": 800,
    "M3": 100, "M3 Pro": 150, "M3 Max": 400, "M3 Ultra": 819,
    "M4": 120, "M4 Pro": 273, "M4 Max": 546,
    "M5": 153,
}
OTHER_BW = {"DGX Spark (GB10)": 273, "RTX 4090": 1008, "H100 SXM": 3350, "H200": 4800, "B200": 8000}


def _sysctl(key: str) -> str:
    try:
        return subprocess.run(["sysctl", "-n", key], capture_output=True, text=True, timeout=3).stdout.strip()
    except Exception:
        return ""


def detect() -> dict:
    """Return {'chip': str, 'ram_gb': float, 'bw_gbs': int|None}."""
    if platform.system() == "Darwin":
        chip = _sysctl("machdep.cpu.brand_string") or "Apple ?"
        ram = int(_sysctl("hw.memsize") or 0) / 1e9
        m = re.search(r"(M\d)(\s+(Pro|Max|Ultra))?", chip)
        key = (m.group(1) + (" " + m.group(3) if m.group(3) else "")) if m else ""
        return {"chip": chip, "ram_gb": round(ram, 1), "bw_gbs": APPLE_BW.get(key)}
    try:
        ram = int(open("/proc/meminfo").read().split()[1]) / 1e6
    except Exception:
        ram = 0.0
    return {"chip": platform.processor() or platform.machine(), "ram_gb": round(ram, 1), "bw_gbs": None}


def ceiling(bw_gbs: float, gb_per_token: float) -> float:
    """Upper bound on single-stream decode speed."""
    return bw_gbs / gb_per_token if gb_per_token else float("inf")
