"""
Episode 1 — sweep Ollama context length and record what the runtime reports.

The prompt stays short on purpose. Ollama sizes the KV cache from num_ctx
when the model loads, so this script unloads the model between rungs and
reads /api/ps after each load. predicted_kv_bytes is the formula from
kv_cache.py. measured_runtime_bytes is the size Ollama reports. That
total includes the weights and compute buffers, not just the KV cache.
The growth from one context rung to the next is the part that tracks the cache.

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
    load_ollama,
    ollama_base,
    ollama_host_label,
    ollama_json,
    parse_contexts,
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


def is_ollama_runner(command: str) -> bool:
    """Server and runner processes only. The macOS app window is not one of them."""
    lower = command.strip().lower()
    if not lower:
        return False
    if re.search(r"(^|[\s/])llama-server(?:\.exe)?(?:\s|$)", lower):
        return True
    if re.search(r"(^|[\s/])llama(?:\.exe)?\s+runner(?:\s|$)", lower):
        return True
    if re.search(r"(^|[\s/])ollama(?:\.exe)?\s+serve(?:\s|$)", lower):
        return True
    if re.search(r"(^|[\s/])ollama(?:\.exe)?\s+runner(?:\s|$)", lower):
        return True
    # The GUI binary is `Ollama` inside Ollama.app and has no serve or runner argument.
    # Match the lowercase CLI name only, so a bare `Ollama` window is left out.
    if ".app" in lower:
        return False
    return re.search(r"(^|[\s/])ollama(?:\.exe)?$", command.strip()) is not None


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


def parse_ps_pids(text: str) -> set[int]:
    """PIDs from `ps -axo pid=,command=` that are an Ollama server or a llama runner."""
    pids: set[int] = set()
    for line in text.splitlines():
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        pid_text, command = parts
        if not is_ollama_runner(command):
            continue
        try:
            pids.add(int(pid_text))
        except ValueError:
            continue
    return pids


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


def gpu_bytes_from_smi(memory_used_text: str, compute_apps_text: str | None, ps_text: str) -> tuple[int | None, str | None]:
    """Prefer memory.used. Fall back to the sum of Ollama and llama runner compute apps."""
    parsed = parse_nvidia_smi(memory_used_text)
    if parsed is not None:
        return parsed, None
    if compute_apps_text is None:
        return None, "nvidia-smi ran but did not report a memory figure."
    summed = parse_compute_apps(compute_apps_text, parse_ps_pids(ps_text))
    if summed is None:
        return None, (
            "nvidia-smi memory.used was not a number, and no Ollama or llama runner was listed in compute-apps."
        )
    return summed, (
        "nvidia-smi memory.used was not a number. GPU memory is the sum of Ollama and llama runner processes from compute-apps."
    )


def parse_ps_rss(text: str) -> int | None:
    """Sum RSS (KiB) of the Ollama server and runner processes, as bytes.

    A command that only contains the app name, such as the macOS GUI, is not included.
    On Linux this figure stays flat because CUDA memory is not in the resident set,
    so the sweep omits it there.
    """
    total = 0
    found = False
    for line in text.splitlines():
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        rss, command = parts
        if not is_ollama_runner(command):
            continue
        try:
            total += int(rss)
        except ValueError:
            continue
        found = True
    if not found:
        return None
    return total * 1024


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


def _read_gpu_memory() -> tuple[int | None, list[str]]:
    try:
        used = _run_command(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"])
    except subprocess.TimeoutExpired:
        return None, ["nvidia-smi timed out, so the GPU column is empty."]
    if used is None:
        return None, ["nvidia-smi is not on PATH, so the GPU column is empty."]
    if used.returncode != 0:
        return None, ["nvidia-smi failed, so the GPU column is empty."]
    apps_text: str | None = None
    ps_text = ""
    if parse_nvidia_smi(used.stdout) is None:
        try:
            apps = _run_command(
                ["nvidia-smi", "--query-compute-apps=pid,used_memory", "--format=csv,noheader,nounits"]
            )
        except subprocess.TimeoutExpired:
            return None, ["nvidia-smi timed out, so the GPU column is empty."]
        if apps is not None and apps.returncode == 0:
            apps_text = apps.stdout
            try:
                ps = _run_command(["ps", "-axo", "pid=,command="])
            except subprocess.TimeoutExpired:
                ps = None
            if ps is not None and ps.returncode == 0:
                ps_text = ps.stdout
    gpu_bytes, note = gpu_bytes_from_smi(used.stdout, apps_text, ps_text)
    return gpu_bytes, [] if note is None else [note]


def _read_rss() -> tuple[int | None, list[str]]:
    try:
        proc = _run_command(["ps", "-axo", "rss=,command="])
    except subprocess.TimeoutExpired:
        return None, ["ps timed out, so the process RSS column is empty."]
    if proc is None:
        return None, ["ps is not available, so the process RSS column is empty."]
    if proc.returncode != 0:
        return None, ["ps failed, so the process RSS column is empty."]
    return parse_ps_rss(proc.stdout), []


def collect_host_metrics() -> dict:
    """Optional counters. Missing tools become nulls and a note, never a crash."""
    notes: list[str] = []
    system = platform.system()
    gpu_bytes: int | None = None
    if system == "Darwin":
        notes.append("macOS reports unified memory through Ollama's size. There is no separate GPU counter.")
        notes.append("Process RSS sums the Ollama server and runner only, not the app window.")
    else:
        gpu_bytes, gpu_notes = _read_gpu_memory()
        notes.extend(gpu_notes)
    if system == "Linux":
        rss_bytes = None
        notes.append(
            "Process RSS is omitted on Linux. Resident memory does not include CUDA allocations, "
            "so it stays flat and is not the GPU figure."
        )
    else:
        rss_bytes, rss_notes = _read_rss()
        notes.extend(rss_notes)
    return {
        "os": system,
        "gpu_memory_bytes": gpu_bytes,
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
) -> dict:
    return {
        "num_ctx": num_ctx,
        "predicted_kv_bytes": kv_bytes_for(shape, num_ctx),
        "measured_runtime_bytes": measured_runtime_bytes,
        "measured_vram_bytes": measured_vram_bytes,
        "gpu_memory_bytes": gpu_memory_bytes,
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


def _read_runtime_size(base: str, model: str) -> tuple[int | None, int | None, str]:
    notes = []
    last_runtime = None
    last_vram = None
    deadline = time.perf_counter() + 5
    while True:
        try:
            ps = ollama_json(base, "/api/ps", timeout=10)
        except RuntimeError:
            return None, None, "Ollama did not return a process list."
        running = _find_running(ps, model)
        if running is not None:
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
    return last_runtime, last_vram, " ".join(notes)


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


def measure_once(base: str, model: str, num_ctx: int, host_metrics: dict, shape, timeout: float) -> dict:
    notes: list[str] = []
    _unload(base, model)
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
            gpu_memory_bytes=host_metrics.get("gpu_memory_bytes"),
            process_rss_bytes=host_metrics.get("process_rss_bytes"),
            ttft_ms=None,
            load_ms=None,
            notes=" ".join(notes),
        )
    runtime_bytes, vram_bytes, size_note = _read_runtime_size(base, model)
    if size_note:
        notes.append(size_note)
    try:
        ttft_ms, _final = _generate(base, model, num_ctx, timeout)
        if ttft_ms is None:
            notes.append("the warm request returned no token.")
    except RuntimeError as exc:
        notes.append(str(exc))
    # Refresh optional counters after the model is resident. Failures stay in the header notes.
    fresh = collect_host_metrics()
    return build_row(
        num_ctx=num_ctx,
        shape=shape,
        measured_runtime_bytes=runtime_bytes,
        measured_vram_bytes=vram_bytes,
        gpu_memory_bytes=fresh.get("gpu_memory_bytes"),
        process_rss_bytes=fresh.get("process_rss_bytes"),
        ttft_ms=ttft_ms,
        load_ms=load_ms,
        notes=" ".join(notes),
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
    print("The growth between context rungs is the part that tracks the cache. Do not expect the two columns to be equal.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Ollama model name (default {DEFAULT_MODEL})")
    parser.add_argument("--contexts", default=",".join(str(n) for n in DEFAULT_CONTEXTS))
    parser.add_argument("--pull", action="store_true", help="download the model if it is not installed")
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
        print(f"{shape.name}: {shape.layers} layers, {shape.attention_heads} attention heads, {shape.kv_heads} KV heads, head dim {shape.head_dim}")
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
            "shape": {
                "layers": shape.layers,
                "attention_heads": shape.attention_heads,
                "kv_heads": shape.kv_heads,
                "head_dim": shape.head_dim,
                "bytes_per_value": shape.bytes_per_value,
            },
            "notes": header_notes,
            "rows": rows,
        }
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
