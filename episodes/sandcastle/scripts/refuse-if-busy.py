#!/usr/bin/env python3
"""Refuse to add load when host mem, CPU, or GPU util is at or above 85%."""
import subprocess
import sys
import time


def mem_pct() -> float:
    info = {}
    with open("/proc/meminfo") as f:
        for line in f:
            k, v, *_ = line.split()
            info[k.rstrip(":")] = float(v)
    total, avail = info["MemTotal"], info["MemAvailable"]
    return (total - avail) * 100.0 / total


def cpu_pct() -> float:
    def snap():
        with open("/proc/stat") as f:
            vals = list(map(int, f.readline().split()[1:]))
        idle = vals[3] + (vals[4] if len(vals) > 4 else 0)
        return sum(vals), idle

    t1, i1 = snap()
    time.sleep(0.4)
    t2, i2 = snap()
    dt, di = t2 - t1, i2 - i1
    return (100.0 * (dt - di) / dt) if dt else 0.0


def gpu_util():
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    for line in out.splitlines():
        line = line.strip()
        if line and line.replace(".", "", 1).isdigit():
            return float(line)
    return None


def main() -> int:
    why = sys.argv[1] if len(sys.argv) > 1 else "start"
    mem, cpu, gpu = mem_pct(), cpu_pct(), gpu_util()
    if mem >= 85:
        sys.stderr.write(f"refusing to {why}: host memory already {mem:.1f}% used\n")
        return 3
    if cpu >= 85:
        sys.stderr.write(f"refusing to {why}: host CPU already {cpu:.1f}% used\n")
        return 3
    if gpu is not None and gpu >= 85:
        sys.stderr.write(f"refusing to {why}: GPU util already {gpu:.1f}%\n")
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
