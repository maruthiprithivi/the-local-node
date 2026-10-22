"""
Episode 1 — KV cache size from a model's real shape.

    KV bytes = 2 x layers x kv_heads x head_dim x bytes x tokens

The 2 is one key and one value. kv_heads is lower than the attention-head
count when the model was trained with grouped query attention. Only tokens
changes while you chat. A quantized cache changes bytes.

    python kv_cache.py --example
    python kv_cache.py --ollama llama3.2:1b
    python kv_cache.py --config config.json
    python kv_cache.py --gguf model.gguf
    python kv_cache.py --layers 32 --attention-heads 32 --kv-heads 8 --head-dim 128

Nothing here is a measurement. measure_kv.py records what a live Ollama
process actually reports.
"""

from __future__ import annotations

import argparse
import json
import os
import struct
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

GIB = 1024**3
KIB = 1024

# Byte widths used by the formula. q8_0 is half of f16. q4_0 is a quarter.
# A runtime may also store a small scale beside each block, so a live run
# can sit a little above these columns.
KV_WIDTHS = {
    "f16": 2.0,
    "bf16": 2.0,
    "f32": 4.0,
    "q8_0": 1.0,
    "q4_0": 0.5,
}

DEFAULT_CONTEXTS = (1024, 2048, 4096, 8192, 16384, 32768)
FORMULA = "2 x layers x kv_heads x head_dim x bytes x tokens"
EXAMPLE_TOKENS = 8192

_DTYPE_BYTES = {
    "float16": 2.0,
    "fp16": 2.0,
    "f16": 2.0,
    "torch.float16": 2.0,
    "bfloat16": 2.0,
    "bf16": 2.0,
    "torch.bfloat16": 2.0,
    "float32": 4.0,
    "fp32": 4.0,
    "f32": 4.0,
    "torch.float32": 4.0,
}

_GGUF_COUNT_LIMIT = 100_000
_GGUF_ARRAY_LIMIT = 2_000_000
_GGUF_STRING_LIMIT = 16_000_000


@dataclass
class ModelShape:
    layers: int
    attention_heads: int
    kv_heads: int
    head_dim: int
    bytes_per_value: float = 2.0
    dtype_name: str = "f16"
    name: str = ""
    source: str = ""
    head_dim_note: str = ""
    weight_quant: str | None = None

    @property
    def group_size(self) -> int:
        if self.kv_heads <= 0 or self.attention_heads % self.kv_heads != 0:
            raise ValueError("attention heads must be divisible by KV heads")
        return self.attention_heads // self.kv_heads

    @property
    def grouped(self) -> bool:
        return self.kv_heads != self.attention_heads


def kv_bytes(
    layers: int,
    kv_heads: int,
    head_dim: int,
    bytes_per_value: float,
    tokens: int,
    chats: int = 1,
) -> int:
    """Whole bytes for `chats` sequences of `tokens` each.

    Widths are counted in sixteenths of a byte so 0.5 and 2 stay exact.
    """
    for label, value in (
        ("layers", layers),
        ("kv_heads", kv_heads),
        ("head_dim", head_dim),
        ("tokens", tokens),
        ("chats", chats),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"{label} must be a positive integer")
    if bytes_per_value <= 0:
        raise ValueError("bytes per value must be positive")
    sixteenths = int(round(bytes_per_value * 16))
    if abs(sixteenths / 16 - bytes_per_value) > 1e-9:
        raise ValueError("bytes per value must be a multiple of 1/16")
    product = 2 * layers * kv_heads * head_dim * tokens * chats * sixteenths
    if product % 16 != 0:
        raise ValueError("the formula did not land on a whole number of bytes")
    return product // 16


def kv_bytes_for(shape: ModelShape, tokens: int, chats: int = 1, bytes_per_value: float | None = None) -> int:
    width = shape.bytes_per_value if bytes_per_value is None else bytes_per_value
    return kv_bytes(shape.layers, shape.kv_heads, shape.head_dim, width, tokens, chats)


def format_gib(n: int) -> str:
    if n % GIB == 0:
        return f"{n // GIB} GiB"
    text = f"{n / GIB:.4f}".rstrip("0").rstrip(".")
    return f"{text} GiB"


def format_kib(n: int) -> str:
    if n % KIB == 0:
        return f"{n // KIB} KiB"
    return f"{n / KIB:.2f} KiB"


def format_bytes(n: int | None) -> str:
    if n is None:
        return "not reported"
    if n < KIB:
        return f"{n} bytes"
    if n < 1024**2:
        return format_kib(n)
    if n < GIB:
        if n % (1024**2) == 0:
            return f"{n // (1024**2)} MiB"
        return f"{n / (1024**2):.1f} MiB"
    return format_gib(n)


def _positive_int(value: object, label: str) -> int:
    if isinstance(value, float):
        if not value.is_integer():
            raise ValueError(f"{label} is not a whole number")
        value = int(value)
    if isinstance(value, bool) or isinstance(value, list):
        if isinstance(value, list):
            if not value:
                raise ValueError(f"{label} is empty")
            ints = [_positive_int(item, label) for item in value]
            if any(item != ints[0] for item in ints):
                raise ValueError(f"{label} changes from layer to layer; this formula uses one shape for every layer")
            return ints[0]
        raise ValueError(f"{label} is missing")
    if value is None or isinstance(value, str):
        raise ValueError(f"{label} is missing")
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} is not an integer") from exc
    if number <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return number


def _check_shape(layers: int, attention_heads: int, kv_heads: int, head_dim: int) -> None:
    if kv_heads > attention_heads:
        raise ValueError("KV heads cannot be greater than attention heads")
    if attention_heads % kv_heads != 0:
        raise ValueError("attention heads must be divisible by KV heads")
    if head_dim <= 0 or layers <= 0:
        raise ValueError("layers and head dim must be positive")


def shape_from_counts(
    *,
    layers: int,
    attention_heads: int,
    kv_heads: int,
    head_dim: int,
    bytes_per_value: float = 2.0,
    dtype_name: str = "f16",
    name: str = "",
    source: str = "",
    head_dim_note: str = "",
    weight_quant: str | None = None,
) -> ModelShape:
    _check_shape(layers, attention_heads, kv_heads, head_dim)
    if bytes_per_value <= 0:
        raise ValueError("bytes per value must be positive")
    return ModelShape(
        layers=layers,
        attention_heads=attention_heads,
        kv_heads=kv_heads,
        head_dim=head_dim,
        bytes_per_value=bytes_per_value,
        dtype_name=dtype_name,
        name=name,
        source=source,
        head_dim_note=head_dim_note,
        weight_quant=weight_quant,
    )


def _meta_value(meta: dict, arch: str, *suffixes: str) -> object | None:
    for suffix in suffixes:
        key = f"{arch}.{suffix}"
        if key in meta and meta[key] is not None:
            return meta[key]
    return None


def shape_from_gguf_metadata(
    meta: dict,
    *,
    name: str = "",
    source: str = "gguf",
    weight_quant: str | None = None,
) -> ModelShape:
    arch = meta.get("general.architecture")
    if not isinstance(arch, str) or not arch:
        raise ValueError("model info has no general.architecture")
    layers = _positive_int(_meta_value(meta, arch, "block_count"), "layers")
    attention_heads = _positive_int(_meta_value(meta, arch, "attention.head_count"), "attention heads")
    kv_raw = _meta_value(meta, arch, "attention.head_count_kv")
    kv_heads = attention_heads if kv_raw is None else _positive_int(kv_raw, "KV heads")
    key_length = _meta_value(meta, arch, "attention.key_length", "attention.value_length")
    note = ""
    if key_length is None:
        embedding = _positive_int(_meta_value(meta, arch, "embedding_length"), "embedding length")
        if embedding % attention_heads != 0:
            raise ValueError("embedding length is not divisible by attention heads, and no key length is set")
        head_dim = embedding // attention_heads
        note = "embedding length / attention heads"
    else:
        head_dim = _positive_int(key_length, "head dim")
    return shape_from_counts(
        layers=layers,
        attention_heads=attention_heads,
        kv_heads=kv_heads,
        head_dim=head_dim,
        name=name,
        source=source,
        head_dim_note=note,
        weight_quant=weight_quant,
    )


def _config_block(cfg: dict) -> dict:
    if any(key in cfg and cfg[key] is not None for key in ("num_hidden_layers", "n_layer", "num_layers")):
        return cfg
    for key in ("text_config", "llm_config", "language_config"):
        nested = cfg.get(key)
        if isinstance(nested, dict):
            try:
                return _config_block(nested)
            except ValueError:
                continue
    raise ValueError("config.json has no layer count (looked at the top level and text_config)")


def _config_value(block: dict, *keys: str) -> object | None:
    for key in keys:
        if key in block and block[key] is not None:
            return block[key]
    return None


def shape_from_config(cfg: dict, *, name: str = "config.json", source: str = "config.json") -> ModelShape:
    if not isinstance(cfg, dict):
        raise ValueError("config.json must be a JSON object")
    block = _config_block(cfg)
    layers = _positive_int(_config_value(block, "num_hidden_layers", "n_layer", "num_layers"), "layers")
    attention_heads = _positive_int(
        _config_value(block, "num_attention_heads", "n_head", "num_heads"),
        "attention heads",
    )
    kv_raw = _config_value(block, "num_key_value_heads", "num_kv_heads", "n_head_kv")
    kv_heads = attention_heads if kv_raw is None else _positive_int(kv_raw, "KV heads")
    head_dim_raw = _config_value(block, "head_dim", "attention_head_dim")
    note = ""
    if head_dim_raw is None:
        hidden = _positive_int(_config_value(block, "hidden_size", "n_embd", "d_model"), "hidden size")
        if hidden % attention_heads != 0:
            raise ValueError("hidden size is not divisible by attention heads, and head_dim is not set")
        head_dim = hidden // attention_heads
        note = "hidden size / attention heads"
    else:
        head_dim = _positive_int(head_dim_raw, "head dim")
    dtype_raw = _config_value(block, "torch_dtype", "dtype")
    if dtype_raw is None:
        dtype_raw = cfg.get("torch_dtype") or cfg.get("dtype")
    dtype_name = "f16"
    width = 2.0
    if isinstance(dtype_raw, str) and dtype_raw.strip():
        key = dtype_raw.strip().lower()
        if key not in _DTYPE_BYTES:
            raise ValueError(f"unsupported dtype {dtype_raw}")
        width = _DTYPE_BYTES[key]
        dtype_name = "bf16" if "bfloat" in key or key == "bf16" else ("f32" if width == 4 else "f16")
    return shape_from_counts(
        layers=layers,
        attention_heads=attention_heads,
        kv_heads=kv_heads,
        head_dim=head_dim,
        bytes_per_value=width,
        dtype_name=dtype_name,
        name=name,
        source=source,
        head_dim_note=note,
    )


def load_config(path: Path) -> ModelShape:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError("could not read config.json") from exc
    except json.JSONDecodeError as exc:
        raise ValueError("config.json is not valid JSON") from exc
    return shape_from_config(payload, name=path.name)


def _read_exact(handle, size: int) -> bytes:
    buf = handle.read(size)
    if len(buf) != size:
        raise ValueError("GGUF file ended before the shape keys were found")
    return buf


def _read_gguf_string(handle) -> str:
    length = struct.unpack("<Q", _read_exact(handle, 8))[0]
    if length > _GGUF_STRING_LIMIT:
        raise ValueError("GGUF string is too large to scan for shape keys")
    return _read_exact(handle, length).decode("utf-8")


def _read_gguf_value(handle, value_type: int):
    if value_type == 8:
        return _read_gguf_string(handle)
    if value_type == 9:
        item_type = struct.unpack("<I", _read_exact(handle, 4))[0]
        count = struct.unpack("<Q", _read_exact(handle, 8))[0]
        if count > _GGUF_ARRAY_LIMIT:
            raise ValueError("GGUF array is too large to scan for shape keys")
        return [_read_gguf_value(handle, item_type) for _ in range(count)]
    formats = {
        0: "<B",
        1: "<b",
        2: "<H",
        3: "<h",
        4: "<I",
        5: "<i",
        6: "<f",
        7: "<?",
        10: "<Q",
        11: "<q",
        12: "<d",
    }
    fmt = formats.get(value_type)
    if fmt is None:
        raise ValueError(f"unsupported GGUF value type {value_type}")
    return struct.unpack(fmt, _read_exact(handle, struct.calcsize(fmt)))[0]


def read_gguf_metadata(path: Path) -> dict:
    """Read GGUF metadata only. Tensor bytes stay on disk."""
    try:
        handle = path.open("rb")
    except OSError as exc:
        raise ValueError("could not read the GGUF file") from exc
    with handle:
        magic = _read_exact(handle, 4)
        if magic != b"GGUF":
            raise ValueError("this file is not a GGUF")
        version = struct.unpack("<I", _read_exact(handle, 4))[0]
        if version < 2 or version > 3:
            raise ValueError(f"GGUF version {version} is not supported (this reader expects version 2 or 3)")
        _tensor_count, kv_count = struct.unpack("<QQ", _read_exact(handle, 16))
        if kv_count > _GGUF_COUNT_LIMIT:
            raise ValueError("GGUF metadata is too large to scan")
        meta: dict = {}
        for _ in range(kv_count):
            key = _read_gguf_string(handle)
            value_type = struct.unpack("<I", _read_exact(handle, 4))[0]
            meta[key] = _read_gguf_value(handle, value_type)
        return meta


def load_gguf(path: Path) -> ModelShape:
    return shape_from_gguf_metadata(read_gguf_metadata(path), name=path.name, source="gguf")


def ollama_base(host: str | None = None) -> str:
    raw = (host or os.environ.get("OLLAMA_HOST") or "http://localhost:11434").strip()
    if not raw:
        raw = "http://localhost:11434"
    if "://" not in raw:
        raw = "http://" + raw
    return raw.rstrip("/")


def ollama_host_label(base: str) -> str:
    if base == "http://localhost:11434":
        return "localhost:11434"
    return "the configured Ollama host"


def ollama_json(base: str, path: str, payload: dict | None = None, timeout: float = 30) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"} if data is not None else {}
    request = urllib.request.Request(base + path, data=data, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Ollama returned HTTP {exc.code} for {path}.") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Ollama is not responding on {ollama_host_label(base)}. Start Ollama and run this again."
        ) from exc
    try:
        parsed = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError("Ollama returned a response that was not JSON.") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError("Ollama returned a response that was not a JSON object.")
    return parsed


def shape_from_ollama_show(payload: dict, *, name: str) -> ModelShape:
    info = payload.get("model_info")
    if not isinstance(info, dict) or not info:
        raise ValueError("Ollama did not return model info for this model")
    details = payload.get("details") if isinstance(payload.get("details"), dict) else {}
    quant = details.get("quantization_level")
    weight_quant = quant if isinstance(quant, str) and quant else None
    return shape_from_gguf_metadata(info, name=name, source="ollama", weight_quant=weight_quant)


def load_ollama(model: str, host: str | None = None) -> ModelShape:
    base = ollama_base(host)
    payload = ollama_json(base, "/api/show", {"model": model}, timeout=60)
    return shape_from_ollama_show(payload, name=model)


def apply_width(shape: ModelShape, kv: str | None, raw_bytes: float | None) -> ModelShape:
    if raw_bytes is not None:
        if raw_bytes <= 0:
            raise ValueError("bytes per value must be positive")
        shape.bytes_per_value = raw_bytes
        shape.dtype_name = "custom"
        return shape
    if kv is not None:
        shape.bytes_per_value = KV_WIDTHS[kv]
        shape.dtype_name = kv
    return shape


def _width_label(name: str, width: float) -> str:
    unit = "byte" if width == 1 else "bytes"
    text = f"{width:g}"
    return f"{name} ({text} {unit})"


def _gqa_lines(shape: ModelShape, tokens: int, chats: int) -> list[str]:
    group = shape.group_size
    if not shape.grouped:
        return [
            "GQA: KV heads match attention heads, so each query head has its own key and value.",
            "When a model is trained with grouped query attention, several query heads share one KV head,",
            "kv_heads drops below the attention-head count, and the cache shrinks by that same factor.",
        ]
    kind = "multi-query attention" if shape.kv_heads == 1 else "grouped query attention"
    full = kv_bytes(shape.layers, shape.attention_heads, shape.head_dim, shape.bytes_per_value, tokens, chats)
    actual = kv_bytes_for(shape, tokens, chats)
    return [
        f"GQA: {kind}. {shape.attention_heads} attention heads share {shape.kv_heads} KV heads.",
        f"group size: {group} query heads share one KV head.",
        f"if kv_heads were {shape.attention_heads} (one per attention head), this context would be {format_gib(full)}.",
        f"with {shape.kv_heads} KV heads it is {format_gib(actual)}.",
    ]


def render_report(
    shape: ModelShape,
    *,
    tokens: int,
    contexts: tuple[int, ...] = DEFAULT_CONTEXTS,
    chats: int = 1,
) -> str:
    if tokens <= 0 or chats <= 0:
        raise ValueError("tokens and chats must be positive")
    ladder = tuple(sorted({*contexts, tokens}))
    lines: list[str] = []
    title = shape.name or "model"
    lines.append(title)
    if shape.source:
        lines.append(f"source: {shape.source}")
    lines.append(f"layers: {shape.layers}")
    lines.append(f"attention heads: {shape.attention_heads}")
    lines.append(f"kv_heads: {shape.kv_heads}")
    head = f"head dim: {shape.head_dim}"
    if shape.head_dim_note:
        head += f" ({shape.head_dim_note})"
    lines.append(head)
    if shape.weight_quant:
        lines.append(f"weights: {shape.weight_quant}")
        lines.append(
            f"KV cache width: {shape.dtype_name} ({shape.bytes_per_value:g} bytes per value). "
            "The weight type does not set the cache width."
        )
    else:
        lines.append(f"bytes per value: {shape.bytes_per_value:g} ({shape.dtype_name})")
    lines.append("")
    lines.extend(_gqa_lines(shape, tokens, chats))
    lines.append("")
    lines.append(f"formula: {FORMULA}")
    per_token = kv_bytes(shape.layers, shape.kv_heads, shape.head_dim, shape.bytes_per_value, 1, 1)
    lines.append(
        f"per token: 2 x {shape.layers} x {shape.kv_heads} x {shape.head_dim} x {shape.bytes_per_value:g}"
        f" = {per_token} bytes ({format_kib(per_token)})"
    )
    total = kv_bytes_for(shape, tokens, 1)
    lines.append(
        f"at {tokens} tokens: 2 x {shape.layers} x {shape.kv_heads} x {shape.head_dim}"
        f" x {shape.bytes_per_value:g} x {tokens} = {format_gib(total)}"
    )
    if chats > 1:
        all_chats = kv_bytes_for(shape, tokens, chats)
        lines.append(f"x {chats} chats: {format_gib(all_chats)}")
    lines.append("")
    columns = [("f16", 2.0), ("q8_0", 1.0), ("q4_0", 0.5)]
    if shape.dtype_name == "bf16" and shape.bytes_per_value == 2:
        columns[0] = ("bf16", 2.0)
    elif shape.dtype_name not in {name for name, _width in columns} or all(
        abs(shape.bytes_per_value - width) > 1e-9 for _name, width in columns
    ):
        columns = [(shape.dtype_name, shape.bytes_per_value), *columns]
    chat_label = "1 chat" if chats == 1 else f"{chats} chats"
    labels = [_width_label(name, width) for name, width in columns]
    body = []
    for ctx in ladder:
        cells = [
            format_gib(kv_bytes(shape.layers, shape.kv_heads, shape.head_dim, width, ctx, chats))
            for _name, width in columns
        ]
        body.append((f"{ctx:,}", cells))
    first_width = max(len("context"), *(len(ctx) for ctx, _cells in body)) + 2
    col_widths = [
        max(len(label), *(len(cells[index]) for _ctx, cells in body)) + 2 for index, label in enumerate(labels)
    ]
    lines.append(f"cache at each context ({chat_label})")
    lines.append("context".ljust(first_width) + "".join(label.rjust(width) for label, width in zip(labels, col_widths)))
    for ctx, cells in body:
        lines.append(ctx.ljust(first_width) + "".join(cell.rjust(width) for cell, width in zip(cells, col_widths)))
    lines.append("")
    lines.append("q8_0 is half the bytes of f16. q4_0 is a quarter. These columns are the formula, not a measurement.")
    lines.append("On Ollama, set OLLAMA_KV_CACHE_TYPE before starting the server, then run measure_kv.py and compare.")
    lines.append("q8_0 on Ollama needs flash attention.")
    return "\n".join(lines) + "\n"


def example_shapes() -> tuple[ModelShape, ModelShape]:
    plain = shape_from_counts(
        layers=32,
        attention_heads=32,
        kv_heads=32,
        head_dim=128,
        bytes_per_value=2.0,
        dtype_name="f16",
        name="example shape",
        source="teaching example, not a specific model",
    )
    grouped = shape_from_counts(
        layers=32,
        attention_heads=32,
        kv_heads=8,
        head_dim=128,
        bytes_per_value=2.0,
        dtype_name="f16",
        name="same shape with grouped query attention",
        source="teaching example, not a specific model",
    )
    return plain, grouped


def render_example(tokens: int = EXAMPLE_TOKENS, contexts: tuple[int, ...] = DEFAULT_CONTEXTS, chats: int = 1) -> str:
    plain, grouped = example_shapes()
    parts = [
        render_report(plain, tokens=tokens, contexts=contexts, chats=chats).rstrip(),
        "",
        render_report(grouped, tokens=tokens, contexts=(tokens,), chats=chats).rstrip(),
        "",
    ]
    return "\n".join(parts) + "\n"


def parse_contexts(text: str) -> tuple[int, ...]:
    values = []
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            number = int(part)
        except ValueError as exc:
            raise ValueError(f"context length {part!r} is not an integer") from exc
        if number <= 0:
            raise ValueError("context length must be positive")
        values.append(number)
    if not values:
        raise ValueError("pass at least one context length")
    return tuple(sorted(set(values)))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--example", action="store_true", help="print the 32-layer teaching shape, including the GQA case")
    parser.add_argument("--ollama", metavar="MODEL", help="read shape from a local Ollama model's info")
    parser.add_argument("--config", type=Path, help="read shape from a config.json")
    parser.add_argument("--gguf", type=Path, help="read shape from a GGUF file")
    parser.add_argument("--layers", type=int)
    parser.add_argument("--attention-heads", type=int)
    parser.add_argument("--kv-heads", type=int)
    parser.add_argument("--head-dim", type=int)
    parser.add_argument("--kv", choices=sorted(KV_WIDTHS), help="KV cache width. Default is f16 (2 bytes) unless the config names a dtype")
    parser.add_argument("--bytes", type=float, help="bytes per value, if you want a width that is not in --kv")
    parser.add_argument("--tokens", type=int, default=EXAMPLE_TOKENS, help="context length for the worked line (default 8192)")
    parser.add_argument("--contexts", help="comma-separated context lengths for the table")
    parser.add_argument("--chats", type=int, default=1, help="parallel sequences (default 1)")
    parser.add_argument("--host", help="Ollama base URL. Defaults to OLLAMA_HOST or localhost:11434")
    return parser


def shape_from_args(args: argparse.Namespace) -> ModelShape:
    chosen = [bool(args.ollama), bool(args.config), bool(args.gguf), args.layers is not None]
    if sum(chosen) != 1:
        raise ValueError("choose one of --example, --ollama, --config, --gguf, or --layers")
    if args.ollama:
        shape = load_ollama(args.ollama, args.host)
    elif args.config:
        shape = load_config(args.config)
    elif args.gguf:
        shape = load_gguf(args.gguf)
    else:
        if None in (args.attention_heads, args.kv_heads, args.head_dim):
            raise ValueError("manual shape needs --layers, --attention-heads, --kv-heads, and --head-dim")
        shape = shape_from_counts(
            layers=args.layers,
            attention_heads=args.attention_heads,
            kv_heads=args.kv_heads,
            head_dim=args.head_dim,
            name="manual shape",
            source="flags",
        )
    return apply_width(shape, args.kv, args.bytes)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        contexts = parse_contexts(args.contexts) if args.contexts else DEFAULT_CONTEXTS
        if args.example:
            if any((args.ollama, args.config, args.gguf, args.layers is not None)):
                raise ValueError("--example does not take a model source")
            sys.stdout.write(render_example(tokens=args.tokens, contexts=contexts, chats=args.chats))
            return 0
        shape = shape_from_args(args)
        sys.stdout.write(render_report(shape, tokens=args.tokens, contexts=contexts, chats=args.chats))
        return 0
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
