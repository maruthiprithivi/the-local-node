"""
Lesson 00 · step 2 — what have I got?

Prints your chip, RAM (= your "VRAM" on a Mac: unified memory is shared by the
GPU and everything else), memory bandwidth (= your decode speed limit), and
which model servers are answering right now.

    python lessons/00-setup/check_env.py
"""
import os
import urllib.request

from felab import TARGETS
from felab.hardware import detect


def up(url: str) -> bool:
    """A server is 'up' if GET /models answers within a second."""
    try:
        with urllib.request.urlopen(url.rstrip("/") + "/models", timeout=1) as r:
            return r.status == 200
    except Exception:
        return False


hw = detect()
print("── machine ─────────────────────────────────────────────")
print(f"chip        {hw['chip']}")
print(f"memory      {hw['ram_gb']} GB   ← model weights + KV cache must fit in ~70% of this")
if hw["bw_gbs"]:
    bw = hw["bw_gbs"]
    print(f"bandwidth   ~{bw} GB/s   ← decode ceiling for an 8B model at 4-bit (≈4.9 GB): "
          f"~{bw / 4.9:.0f} tok/s")
else:
    print("bandwidth   unknown (not an Apple chip) — see felab/hardware.py")

print("\n── servers ─────────────────────────────────────────────")
for name, t in TARGETS.items():
    if name in ("fireworks",):
        state = "key set ✓" if t.api_key else "no FIREWORKS_API_KEY (fine until lesson 01b)"
    elif name == "spark" and not os.environ.get("SPARK_IP") and not os.environ.get("SPARK_URL"):
        state = "SPARK_IP not set (fine until lesson 14)"
    else:
        state = "UP ✓" if up(t.base_url) else "down"
    print(f"{name:10s} {t.base_url:45s} {state}")

print("\nStart the offline mock any time:  python -m felab.mock_server")
