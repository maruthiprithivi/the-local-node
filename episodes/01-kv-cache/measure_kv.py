"""
Episode 1 — sweep Ollama context length and record what the runtime reports.

The prompt stays short on purpose. Ollama sizes the KV cache from num_ctx
when the model loads, so this script unloads the model between rungs and
reads /api/ps after each load. predicted_kv_bytes is the formula from
kv_cache.py. measured_runtime_bytes is the size Ollama reports. That
total includes the weights and compute buffers, not just the KV cache.
The growth from one context rung to the next is the part that tracks the cache.
The chart plots that growth: attributed GPU memory when gpu_attribution is
set, and process RSS when the row says unavailable. Ollama's reported size
stays in the file.

    python measure_kv.py
    python measure_kv.py --pull
    python measure_kv.py --model llama3.2:1b --contexts 512,1024,2048,4096,8192

The default model is small. Nothing is downloaded unless you pass --pull.
A name that looks like 7B or larger still needs that flag, and the script
says so before it downloads.

Pass the JSON this writes straight to the Remotion chart:

    cd chart && npm run render -- --props=../runs/kv-sweep.json
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from kv_cache import (
    KV_WIDTHS,
    format_bytes,
    kv_bytes_for,
    layer_count_line,
    load_ollama,
    ollama_base,
    ollama_host_label,
    ollama_json,
    parse_contexts,
    shape_fields,
)

DEFAULT_MODEL = "llama3.2:1b"
DEFAULT_CONTEXTS = (512, 1024, 2048, 4096, 8192)
PROMPT = "Reply with one short word."


@dataclass
class InstallPlan:
    action: str
    reason: str


def model_is_large(name: str) -> bool:
    """True when the name advertises about 7B parameters or more."""
    for match in re.finditer(r"(?:^|[^0-9])(\d+(?:\.\d+)?)b(?:[^a-z0-9]|$)", name.lower()):
        if float(match.group(1)) >= 7:
            return True
    return False


def is_installed(installed: list[str], wanted: str) -> bool:
    wanted = wanted.strip()
    for name in installed:
        if name == wanted or (":" not in wanted and name == f"{wanted}:latest"):
            return True
    return False


def plan_install(name: str, installed: list[str], pull: bool) -> InstallPlan:
    if is_installed(installed, name):
        return InstallPlan("ready", "")
    if not pull:
        extra = " This name looks like a large model." if model_is_large(name) else ""
        return InstallPlan(
            "refuse",
            f"{name} is not installed. Nothing was downloaded.{extra} "
            "Pass --pull to download it, or pick a model you already have.",
        )
    if model_is_large(name):
        return InstallPlan("pull", f"{name} looks like a large model. Downloading it because --pull was set.")
    return InstallPlan("pull", "")


def bytes_for_kv_type(name: str | None) -> tuple[float, str, str | None]:
    """Map OLLAMA_KV_CACHE_TYPE onto a formula width.

    Returns width, label, and a note when the value was missing or unknown.
    """
    if name is None or not str(name).strip():
        return 2.0, "f16", None
    key = str(name).strip().lower()
    if key not in KV_WIDTHS:
        return 2.0, "f16", f"OLLAMA_KV_CACHE_TYPE {name!r} is not a width this script knows, so the prediction uses f16."
    return KV_WIDTHS[key], key, None


_NOT_A_NUMBER = {"[N/A]", "N/A", "[NOT SUPPORTED]"}
NUM_PREDICT = 64
NUM_PREDICT_RETRY = 256


def is_llama_runner(command: str) -> bool:
    """A llama.cpp server or runner. Counted only when Ollama spawned it."""
    lower = command.strip().lower()
    if not lower:
        return False
    if re.search(r"(^|[\s/])llama-server(?:\.exe)?(?:\s|$)", lower):
        return True
    return re.search(r"(^|[\s/])llama(?:\.exe)?\s+runner(?:\s|$)", lower) is not None


def is_ollama_server(command: str) -> bool:
    """`ollama serve` or the bare `ollama` CLI. Not the app window, not a runner."""
    lower = command.strip().lower()
    if not lower or is_llama_runner(command):
        return False
    if re.search(r"(^|[\s/])ollama(?:\.exe)?\s+serve(?:\s|$)", lower):
        return True
    if re.search(r"(^|[\s/])ollama(?:\.exe)?\s+runner(?:\s|$)", lower):
        return False
    if ".app" in lower:
        return False
    return re.search(r"(^|[\s/])ollama(?:\.exe)?$", command.strip()) is not None


def is_ollama_worker(command: str) -> bool:
    lower = command.strip().lower()
    return re.search(r"(^|[\s/])ollama(?:\.exe)?\s+runner(?:\s|$)", lower) is not None


def is_ollama_process(command: str) -> bool:
    """Ollama's own server or runner. A standalone llama-server is not one of these."""
    return is_ollama_server(command) or is_ollama_worker(command)


def is_ollama_runner(command: str) -> bool:
    """Ollama's own server and runner. The macOS app window is not one of them.

    llama-server is intentionally not matched here. A copy from another project
    shares that name, so it counts only when its parent chain reaches Ollama.
    """
    return is_ollama_process(command)


def parse_nvidia_smi(text: str) -> int | None:
    """Sum `nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits` (MiB) into bytes."""
    values: list[int] = []
    for line in text.splitlines():
        cell = line.strip()
        if not cell or cell.lower().startswith("memory"):
            continue
        if cell.upper() in _NOT_A_NUMBER:
            continue
        token = cell.split(",")[0].strip()
        if token.upper() in _NOT_A_NUMBER:
            continue
        try:
            values.append(int(token))
        except ValueError:
            return None
    if not values:
        return None
    return sum(values) * 1024 * 1024


@dataclass(frozen=True)
class Process:
    pid: int
    ppid: int
    rss_kib: int
    command: str


def parse_processes(text: str) -> list[Process]:
    """`ps -axo pid=,ppid=,rss=,command=`."""
    rows: list[Process] = []
    for line in text.splitlines():
        parts = line.split(None, 3)
        if len(parts) < 4:
            continue
        try:
            pid = int(parts[0])
            ppid = int(parts[1])
            rss = int(parts[2])
        except ValueError:
            continue
        rows.append(Process(pid, ppid, rss, parts[3]))
    return rows


def spawned_by_ollama(proc: Process, by_pid: dict[int, Process]) -> bool:
    """Walk ppid until an Ollama server or runner is the ancestor."""
    pid = proc.ppid
    seen: set[int] = set()
    while pid > 0 and pid not in seen:
        seen.add(pid)
        parent = by_pid.get(pid)
        if parent is None:
            return False
        if is_ollama_process(parent.command):
            return True
        pid = parent.ppid
    return False


def owned_runner_pids(procs: list[Process]) -> set[int]:
    """Runners that belong to Ollama.

    `ollama runner` is Ollama's own process. `llama-server` and `llama runner`
    count only when walking their parents reaches that Ollama process.
    """
    by_pid = {proc.pid: proc for proc in procs}
    pids: set[int] = set()
    for proc in procs:
        if is_ollama_worker(proc.command):
            pids.add(proc.pid)
        elif is_llama_runner(proc.command) and spawned_by_ollama(proc, by_pid):
            pids.add(proc.pid)
    return pids


def ollama_server_pids(procs: list[Process]) -> set[int]:
    return {proc.pid for proc in procs if is_ollama_server(proc.command)}


def select_model_runners(
    before: set[int],
    after: set[int],
    reported: set[int] | None = None,
) -> tuple[set[int], str, str]:
    """Pick the runner serving the swept model.

    Returns pids, a short token recorded on the row, and a sentence for the note.
    A PID Ollama reports wins. Otherwise the PID that appeared after this load.
    A single runner left resident is used when nothing new appeared. Several
    older runners are not summed together.
    """
    reported_pids = {pid for pid in (reported or set()) if isinstance(pid, int) and pid > 0}
    if reported_pids:
        ids = ", ".join(str(pid) for pid in sorted(reported_pids))
        return reported_pids, "ollama-pid", f"PID reported by Ollama ({ids})"
    appeared = set(after) - set(before)
    if appeared:
        ids = ", ".join(str(pid) for pid in sorted(appeared))
        return appeared, "new-pid", f"new runner PID after this load ({ids})"
    if len(after) == 1:
        pid = next(iter(after))
        return set(after), "only-runner", f"the only Ollama runner still resident (pid {pid})"
    if not after:
        return set(), "unattributed", "no Ollama runner was resident after the load"
    return (
        set(),
        "unattributed",
        "several Ollama runners stayed resident and none was new, so this row does not sum them",
    )


def pids_from_running(running: dict | None) -> set[int]:
    """PID fields when Ollama's process list includes them. Many builds do not."""
    if not isinstance(running, dict):
        return set()
    found: set[int] = set()
    for key in ("pid", "runner_pid"):
        number = _int_or_none(running.get(key))
        if number and number > 0:
            found.add(number)
    return found


def parse_compute_apps(text: str, runner_pids: set[int]) -> int | None:
    """Sum `nvidia-smi --query-compute-apps=pid,used_memory` (MiB) for runner pids, as bytes.

    Used when `memory.used` comes back as [N/A], which happens on some boards.
    Other compute apps on the same GPU are left out.
    """
    total = 0
    found = False
    for line in text.splitlines():
        cell = line.strip()
        if not cell or cell.lower().startswith("pid"):
            continue
        parts = [part.strip() for part in cell.split(",")]
        if len(parts) < 2:
            continue
        if parts[0].upper() in _NOT_A_NUMBER or parts[1].upper() in _NOT_A_NUMBER:
            continue
        try:
            pid = int(parts[0])
            mib = int(parts[1])
        except ValueError:
            continue
        if pid not in runner_pids:
            continue
        total += mib
        found = True
    if not found:
        return None
    return total * 1024 * 1024


def gpu_bytes_from_smi(
    memory_used_text: str,
    compute_apps_text: str | None,
    runner_pids: set[int] | None = None,
    approach: str = "",
) -> tuple[int | None, str | None, str]:
    """Prefer memory.used. Otherwise sum compute-apps for the attributed runner pids.

    Returns bytes, a row note, and the attribution token.
    """
    parsed = parse_nvidia_smi(memory_used_text)
    if parsed is not None:
        return parsed, "GPU memory is nvidia-smi memory.used for the whole GPU.", "memory.used"
    if compute_apps_text is None:
        return None, "nvidia-smi ran but did not report a memory figure.", "unavailable"
    targets = runner_pids or set()
    if not targets:
        detail = approach or "no runner was attributed to this model"
        return (
            None,
            f"nvidia-smi memory.used was not a number, and {detail}.",
            "unattributed",
        )
    summed = parse_compute_apps(compute_apps_text, targets)
    ids = ", ".join(str(pid) for pid in sorted(targets))
    how = approach or "the runner attributed to this model"
    if summed is None:
        return (
            None,
            f"nvidia-smi memory.used was not a number. Approach: {how}. pid {ids} was not listed in compute-apps.",
            "unattributed",
        )
    return (
        summed,
        f"nvidia-smi memory.used was not a number. GPU memory is compute-apps for pid {ids}. Approach: {how}.",
        "compute-apps",
    )


def rss_for_pids(procs: list[Process], pids: set[int]) -> int | None:
    total = 0
    found = False
    for proc in procs:
        if proc.pid not in pids:
            continue
        total += proc.rss_kib
        found = True
    if not found:
        return None
    return total * 1024


def parse_ps_rss(text: str) -> int | None:
    """Sum RSS of the Ollama server and runners Ollama spawned.

    A standalone llama-server, and the macOS app window, are left out.
    On Linux the sweep omits RSS anyway, because CUDA memory is not in it.
    """
    procs = parse_processes(text)
    if not procs:
        return None
    pids = ollama_server_pids(procs) | owned_runner_pids(procs)
    return rss_for_pids(procs, pids)


def gpu_file_note(mode: str, rows: list[dict]) -> str:
    """One file-level sentence that matches the rows actually written."""
    filled = sum(1 for row in rows if row.get("gpu_memory_bytes") is not None)
    total = len(rows)
    if mode == "unavailable":
        return "No separate GPU counter was read, so the GPU column is empty."
    if mode == "missing":
        return "nvidia-smi is not on PATH, so the GPU column is empty."
    if mode == "failed":
        return "nvidia-smi failed, so the GPU column is empty."
    if mode == "timeout":
        return "nvidia-smi timed out, so the GPU column is empty."
    if mode == "memory.used":
        return f"GPU memory is nvidia-smi memory.used for the whole GPU ({filled} of {total} rows)."
    if filled:
        return (
            "nvidia-smi memory.used was not a number. "
            f"{filled} of {total} rows record compute-apps memory for the runner serving this model."
        )
    return (
        "nvidia-smi memory.used was not a number, and no row found a runner for this model in compute-apps."
    )


def safe_detail(text: str) -> str:
    """Keep a short runtime error only when it cannot carry a local path."""
    cleaned = " ".join(text.split())
    if not cleaned or len(cleaned) > 180 or "/" in cleaned or "\\" in cleaned:
        return "Ollama refused the request."
    return cleaned


def _run_command(argv: list[str]) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(argv, capture_output=True, text=True, timeout=5, check=False)
    except FileNotFoundError:
        return None
    except subprocess.TimeoutExpired:
        raise


PS_ARGV = ["ps", "-axo", "pid=,ppid=,rss=,command="]
NVIDIA_USED_ARGV = ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"]
NVIDIA_APPS_ARGV = ["nvidia-smi", "--query-compute-apps=pid,used_memory", "--format=csv,noheader,nounits"]


def nvidia_probe() -> str:
    """How this machine reports GPU memory. Does not claim a runner was missing."""
    try:
        used = _run_command(NVIDIA_USED_ARGV)
    except subprocess.TimeoutExpired:
        return "timeout"
    if used is None:
        return "missing"
    if used.returncode != 0:
        return "failed"
    if parse_nvidia_smi(used.stdout) is not None:
        return "memory.used"
    return "compute-apps"


def read_processes() -> tuple[list[Process], str | None]:
    try:
        proc = _run_command(PS_ARGV)
    except subprocess.TimeoutExpired:
        return [], "ps timed out, so the process RSS column is empty."
    if proc is None:
        return [], "ps is not available, so the process RSS column is empty."
    if proc.returncode != 0:
        return [], "ps failed, so the process RSS column is empty."
    return parse_processes(proc.stdout), None


def read_gpu_for_runners(runner_pids: set[int], approach: str, approach_token: str) -> tuple[int | None, str, str]:
    """Bytes, row note, and attribution token for one loaded model."""
    try:
        used = _run_command(NVIDIA_USED_ARGV)
    except subprocess.TimeoutExpired:
        return None, "nvidia-smi timed out, so the GPU column is empty.", "unavailable"
    if used is None:
        return None, "nvidia-smi is not on PATH, so the GPU column is empty.", "unavailable"
    if used.returncode != 0:
        return None, "nvidia-smi failed, so the GPU column is empty.", "unavailable"
    apps_text: str | None = None
    if parse_nvidia_smi(used.stdout) is None:
        try:
            apps = _run_command(NVIDIA_APPS_ARGV)
        except subprocess.TimeoutExpired:
            return None, "nvidia-smi timed out, so the GPU column is empty.", "unavailable"
        if apps is not None and apps.returncode == 0:
            apps_text = apps.stdout
    gpu_bytes, note, token = gpu_bytes_from_smi(used.stdout, apps_text, runner_pids, approach)
    if token == "memory.used":
        return gpu_bytes, note or "", "memory.used"
    return gpu_bytes, note or "", approach_token or "unattributed"


def collect_host_metrics() -> dict:
    """Static host notes. GPU bytes are filled per row, after a model is resident."""
    notes: list[str] = []
    system = platform.system()
    mode = nvidia_probe() if system != "Darwin" else "unavailable"
    if system == "Darwin":
        notes.append("macOS reports unified memory through Ollama's size. There is no separate GPU counter.")
        notes.append(
            "Process RSS sums the Ollama server and runners Ollama spawned, not the app window "
            "and not a standalone llama-server."
        )
    rss_bytes = None
    if system == "Linux":
        notes.append(
            "Process RSS is omitted on Linux. Resident memory does not include CUDA allocations, "
            "so it stays flat and is not the GPU figure."
        )
    else:
        procs, rss_note = read_processes()
        if rss_note:
            notes.append(rss_note)
        elif procs:
            rss_bytes = rss_for_pids(procs, ollama_server_pids(procs) | owned_runner_pids(procs))
    return {
        "os": system,
        "nvidia_mode": mode,
        "gpu_memory_bytes": None,
        "process_rss_bytes": rss_bytes,
        "notes": notes,
    }


def build_row(
    *,
    num_ctx: int,
    shape,
    measured_runtime_bytes: int | None,
    measured_vram_bytes: int | None,
    gpu_memory_bytes: int | None,
    process_rss_bytes: int | None,
    ttft_ms: float | None,
    load_ms: float | None,
    notes: str,
    gpu_attribution: str = "",
) -> dict:
    return {
        "num_ctx": num_ctx,
        "predicted_kv_bytes": kv_bytes_for(shape, num_ctx),
        "measured_runtime_bytes": measured_runtime_bytes,
        "measured_vram_bytes": measured_vram_bytes,
        "gpu_memory_bytes": gpu_memory_bytes,
        "gpu_attribution": gpu_attribution,
        "process_rss_bytes": process_rss_bytes,
        "ttft_ms": None if ttft_ms is None else round(ttft_ms, 1),
        "load_ms": None if load_ms is None else round(load_ms, 1),
        "notes": notes,
    }


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return path.name


def _models_from_tags(payload: dict) -> list[str]:
    models = payload.get("models")
    if not isinstance(models, list):
        return []
    names = []
    for item in models:
        if isinstance(item, dict) and isinstance(item.get("name"), str):
            names.append(item["name"])
    return names


def _find_running(payload: dict, model: str) -> dict | None:
    models = payload.get("models")
    if not isinstance(models, list):
        return None
    wanted = model.strip()
    for item in models:
        if not isinstance(item, dict):
            continue
        for key in ("name", "model"):
            value = item.get(key)
            if not isinstance(value, str):
                continue
            if value == wanted or (":" not in wanted and value == f"{wanted}:latest"):
                return item
    return None


def _int_or_none(value: object) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value >= 0:
        return int(value)
    return None


def token_text(obj: dict) -> str:
    """First visible token. Thinking models put it in `thinking` and leave `response` empty."""
    for key in ("response", "thinking"):
        value = obj.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def stopped_on_length(final: dict | None) -> bool:
    return isinstance(final, dict) and final.get("done_reason") == "length"


def think_field_rejected(exc: BaseException) -> bool:
    text = str(exc)
    return "HTTP 400" in text or "HTTP 422" in text


def build_generate_payload(model: str, num_ctx: int, num_predict: int, think: bool) -> dict:
    payload = {
        "model": model,
        "prompt": PROMPT,
        "stream": True,
        "keep_alive": "10m",
        "options": {"num_ctx": num_ctx, "num_predict": num_predict, "temperature": 0},
    }
    # think:false asks a thinking model to answer directly. Older servers reject the field.
    if think:
        payload["think"] = False
    return payload


def _stream_generate(base: str, payload: dict, timeout: float) -> tuple[float | None, dict | None]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        base + "/api/generate",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    start = time.perf_counter()
    ttft_ms: float | None = None
    final: dict | None = None
    try:
        response = urllib.request.urlopen(request, timeout=timeout)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Ollama returned HTTP {exc.code} while generating.") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Ollama stopped responding on {ollama_host_label(base)}.") from exc
    with response:
        for raw in response:
            line = raw.decode("utf-8", "replace").strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError("Ollama returned a generate line that was not JSON.") from exc
            if not isinstance(obj, dict):
                continue
            if obj.get("error"):
                raise RuntimeError(safe_detail(str(obj["error"])))
            if ttft_ms is None and token_text(obj):
                ttft_ms = (time.perf_counter() - start) * 1000
            if obj.get("done"):
                final = obj
    return ttft_ms, final


def _unload(base: str, model: str) -> None:
    try:
        ollama_json(base, "/api/generate", {"model": model, "keep_alive": 0}, timeout=60)
    except (RuntimeError, urllib.error.URLError):
        return
    deadline = time.perf_counter() + 20
    while time.perf_counter() < deadline:
        try:
            ps = ollama_json(base, "/api/ps", timeout=10)
        except RuntimeError:
            return
        if _find_running(ps, model) is None:
            return
        time.sleep(0.4)


def _read_runtime_size(base: str, model: str) -> tuple[int | None, int | None, str, set[int]]:
    notes = []
    last_runtime = None
    last_vram = None
    reported: set[int] = set()
    deadline = time.perf_counter() + 5
    while True:
        try:
            ps = ollama_json(base, "/api/ps", timeout=10)
        except RuntimeError:
            return None, None, "Ollama did not return a process list.", set()
        running = _find_running(ps, model)
        if running is not None:
            reported = pids_from_running(running)
            last_runtime = _int_or_none(running.get("size"))
            last_vram = _int_or_none(running.get("size_vram"))
            if last_runtime:
                break
        if time.perf_counter() >= deadline:
            break
        time.sleep(0.3)
    if last_runtime is None:
        notes.append("the runtime did not report a size.")
    elif last_runtime == 0:
        notes.append("the runtime reported a size of 0.")
        last_runtime = None
    if last_vram == 0:
        last_vram = None
    return last_runtime, last_vram, " ".join(notes), reported


def _resident_names(payload: dict) -> list[str]:
    models = payload.get("models")
    if not isinstance(models, list):
        return []
    names = []
    for item in models:
        if not isinstance(item, dict):
            continue
        for key in ("name", "model"):
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                names.append(value.strip())
                break
    return names


def unload_other_models(base: str, keep: str) -> list[str]:
    """Ask Ollama to drop every resident model except the one being swept."""
    try:
        ps = ollama_json(base, "/api/ps", timeout=10)
    except RuntimeError:
        return []
    unloaded: list[str] = []
    seen: set[str] = set()
    for name in _resident_names(ps):
        if name in seen or is_installed([name], keep) or name == keep:
            continue
        seen.add(name)
        _unload(base, name)
        unloaded.append(name)
    return unloaded


def unload_note(names: list[str] | None, keep_others: bool) -> str:
    if keep_others:
        return "Other resident models were left loaded (--keep-others)."
    if not names:
        return "No other models were resident, so none were unloaded."
    safe = [name for name in names if "/" not in name and "\\" not in name]
    if len(safe) != len(names):
        return f"Unloaded {len(names)} other resident models before the sweep."
    return "Unloaded other resident models before the sweep: " + ", ".join(safe) + "."


def _pull(base: str, model: str, timeout: float) -> None:
    data = json.dumps({"model": model, "stream": True}).encode("utf-8")
    request = urllib.request.Request(
        base + "/api/pull",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        response = urllib.request.urlopen(request, timeout=timeout)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Ollama returned HTTP {exc.code} while downloading.") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Ollama stopped responding on {ollama_host_label(base)}.") from exc
    seen: set[str] = set()
    with response:
        for raw in response:
            line = raw.decode("utf-8", "replace").strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(obj, dict):
                continue
            if obj.get("error"):
                raise RuntimeError(safe_detail(str(obj["error"])))
            status = obj.get("status")
            if isinstance(status, str) and status not in seen:
                seen.add(status)
                print(status, flush=True)


def _generate(base: str, model: str, num_ctx: int, timeout: float) -> tuple[float | None, dict | None]:
    """One generate. Prefer think:false, then a longer budget if the first token never arrives."""
    think = True
    try:
        ttft, final = _stream_generate(base, build_generate_payload(model, num_ctx, NUM_PREDICT, True), timeout)
    except RuntimeError as exc:
        if not think_field_rejected(exc):
            raise
        think = False
        ttft, final = _stream_generate(base, build_generate_payload(model, num_ctx, NUM_PREDICT, False), timeout)
    if ttft is None and stopped_on_length(final):
        ttft, final = _stream_generate(
            base,
            build_generate_payload(model, num_ctx, NUM_PREDICT_RETRY, think),
            timeout,
        )
    return ttft, final


def _row_rss(procs: list[Process], targets: set[int]) -> int | None:
    if platform.system() == "Linux":
        return None
    return rss_for_pids(procs, ollama_server_pids(procs) | targets)


def measure_once(base: str, model: str, num_ctx: int, host_metrics: dict, shape, timeout: float) -> dict:
    notes: list[str] = []
    _unload(base, model)
    before_procs, _ps_note = read_processes()
    before = owned_runner_pids(before_procs)
    load_ms = None
    ttft_ms = None
    try:
        load_ms, _final = _generate(base, model, num_ctx, timeout)
        if load_ms is None:
            notes.append("the load request returned no token.")
    except RuntimeError as exc:
        notes.append(str(exc))
        return build_row(
            num_ctx=num_ctx,
            shape=shape,
            measured_runtime_bytes=None,
            measured_vram_bytes=None,
            gpu_memory_bytes=None,
            process_rss_bytes=None,
            ttft_ms=None,
            load_ms=None,
            notes=" ".join(notes),
            gpu_attribution="unavailable",
        )
    runtime_bytes, vram_bytes, size_note, reported = _read_runtime_size(base, model)
    if size_note:
        notes.append(size_note)
    try:
        ttft_ms, _final = _generate(base, model, num_ctx, timeout)
        if ttft_ms is None:
            notes.append("the warm request returned no token.")
    except RuntimeError as exc:
        notes.append(str(exc))
    procs, ps_note = read_processes()
    if ps_note and platform.system() != "Linux":
        notes.append(ps_note)
    targets, token, approach = select_model_runners(before, owned_runner_pids(procs), reported)
    mode = host_metrics.get("nvidia_mode")
    if mode in {"compute-apps", "memory.used"}:
        gpu_bytes, gpu_note, attribution = read_gpu_for_runners(targets, approach, token)
        if gpu_note:
            notes.append(gpu_note)
    else:
        gpu_bytes = None
        attribution = "unavailable"
    return build_row(
        num_ctx=num_ctx,
        shape=shape,
        measured_runtime_bytes=runtime_bytes,
        measured_vram_bytes=vram_bytes,
        gpu_memory_bytes=gpu_bytes,
        process_rss_bytes=_row_rss(procs, targets),
        ttft_ms=ttft_ms,
        load_ms=load_ms,
        notes=" ".join(notes),
        gpu_attribution=attribution,
    )


def output_paths(stem: Path) -> tuple[Path, Path]:
    """Append .json and .csv.

    Path.with_suffix would turn runs/kv-sweep-qwen3.8 into kv-sweep-qwen3.json,
    because it treats .8 as a suffix. A stem that already ends in .json or .csv
    is used as the prefix without doubling the extension.
    """
    text = str(stem)
    for suffix in (".json", ".csv"):
        if text.endswith(suffix):
            text = text[: -len(suffix)]
            break
    return Path(text + ".json"), Path(text + ".csv")


def chart_props_arg(json_path: Path, chart_dir: Path) -> str:
    return Path(os.path.relpath(json_path.resolve(), chart_dir.resolve())).as_posix()


def sweep_header(shape) -> str:
    """One line for the sweep. Pipes keep the model name off the layer count."""
    return (
        f"{shape.name} | {layer_count_line(shape)} | "
        f"attention heads: {shape.attention_heads} | "
        f"KV heads: {shape.kv_heads} | head dim {shape.head_dim}"
    )


def write_results(stem: Path, payload: dict) -> tuple[Path, Path]:
    stem.parent.mkdir(parents=True, exist_ok=True)
    json_path, csv_path = output_paths(stem)
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    fields = [
        "num_ctx",
        "predicted_kv_bytes",
        "measured_runtime_bytes",
        "measured_vram_bytes",
        "gpu_memory_bytes",
        "gpu_attribution",
        "process_rss_bytes",
        "ttft_ms",
        "load_ms",
        "notes",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in payload["rows"]:
            writer.writerow(row)
    return json_path, csv_path


def _print_table(rows: list[dict]) -> None:
    print()
    print(f"{'context':>8}  {'predicted':>14}  {'runtime':>14}  {'warm ttft':>10}")
    for row in rows:
        ttft = "n/a" if row["ttft_ms"] is None else f"{row['ttft_ms']:.0f} ms"
        print(
            f"{row['num_ctx']:>8}  {format_bytes(row['predicted_kv_bytes']):>14}  "
            f"{format_bytes(row['measured_runtime_bytes']):>14}  {ttft:>10}"
        )
    print()
    print("Predicted is the KV cache only. The measured total includes the weights and compute buffers, not just the cache.")
    print("Ollama's reported model size is an estimate that moves in steps. Use the GPU or process growth between rungs for the cache.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Ollama model name (default {DEFAULT_MODEL})")
    parser.add_argument("--contexts", default=",".join(str(n) for n in DEFAULT_CONTEXTS))
    parser.add_argument("--pull", action="store_true", help="download the model if it is not installed")
    parser.add_argument(
        "--keep-others",
        action="store_true",
        help="leave other resident models loaded. By default they are unloaded so their runners are not in the GPU figure",
    )
    parser.add_argument("--host", help="Ollama base URL. Defaults to OLLAMA_HOST or localhost:11434")
    parser.add_argument("--timeout", type=float, default=300, help="seconds to wait for one generate request")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("runs") / "kv-sweep",
        help="path prefix for the JSON and CSV (default runs/kv-sweep)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        contexts = parse_contexts(args.contexts)
        base = ollama_base(args.host)
        tags = ollama_json(base, "/api/tags", timeout=10)
        plan = plan_install(args.model, _models_from_tags(tags), args.pull)
        if plan.action == "refuse":
            print(plan.reason, file=sys.stderr)
            return 1
        if plan.reason:
            print(plan.reason)
        if plan.action == "pull":
            print(f"Downloading {args.model}.")
            _pull(base, args.model, timeout=max(args.timeout, 3600))
        shape = load_ollama(args.model, args.host)
        width, label, width_note = bytes_for_kv_type(os.environ.get("OLLAMA_KV_CACHE_TYPE"))
        shape.bytes_per_value = width
        shape.dtype_name = label
        host_metrics = collect_host_metrics()
        header_notes = list(host_metrics["notes"])
        if width_note:
            header_notes.append(width_note)
        if args.keep_others:
            header_notes.append(unload_note(None, True))
        else:
            try:
                unloaded = unload_other_models(base, args.model)
            except RuntimeError:
                unloaded = None
                header_notes.append("Could not list resident models, so other models were left loaded.")
            else:
                header_notes.append(unload_note(unloaded, False))
        print(sweep_header(shape))
        if shape.layer_note:
            print(shape.layer_note)
        if shape.grouped:
            print(f"GQA group size {shape.group_size}: {shape.group_size} query heads share one KV head.")
        print(f"Predicting a {label} cache ({width:g} bytes per value).")
        rows = []
        for num_ctx in contexts:
            print(f"context {num_ctx}: loading", flush=True)
            row = measure_once(base, args.model, num_ctx, host_metrics, shape, args.timeout)
            rows.append(row)
            print(
                f"context {num_ctx}: predicted {format_bytes(row['predicted_kv_bytes'])}, "
                f"runtime {format_bytes(row['measured_runtime_bytes'])}",
                flush=True,
            )
        payload = {
            "model": args.model,
            "source": "ollama",
            "os": host_metrics["os"],
            "kv_cache_type": label,
            "shape": shape_fields(shape),
            "notes": header_notes,
            "rows": rows,
        }
        header_notes.append(gpu_file_note(host_metrics.get("nvidia_mode") or "missing", rows))
        out = args.out
        if not out.is_absolute():
            out = Path.cwd() / out
        json_path, csv_path = write_results(out, payload)
        _print_table(rows)
        print(f"wrote {display_path(json_path)}")
        print(f"wrote {display_path(csv_path)}")
        chart_dir = Path.cwd() / "chart"
        if (chart_dir / "package.json").is_file():
            props = chart_props_arg(json_path, chart_dir)
            print(f"Chart: cd chart && npm run render -- --props={props}")
        return 0
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
