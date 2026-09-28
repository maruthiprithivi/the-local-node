"""
felab.targets — one place that knows where every model server lives.

Every lesson script takes the same three flags:

    --target  mock | ollama | llamacpp | mlx | fireworks | spark
    --model   override the target's default model id
    --base-url override the target's URL (rarely needed)

so the SAME script measures your laptop, Fireworks and the DGX Spark. That is
the habit the course is built on: one harness, many backends, comparable numbers.

Defaults can be changed in a `.env` file at the repo root (see .env.example).
"""
from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def load_dotenv(path: Path = REPO_ROOT / ".env") -> None:
    """Tiny .env reader (KEY=value per line) so we need no extra dependency.
    Real environment variables always win over the file."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_dotenv()


@dataclass
class Target:
    name: str
    base_url: str
    model: str
    api_key: str
    note: str

    @property
    def is_paid(self) -> bool:
        return self.name == "fireworks"


def _targets() -> dict[str, Target]:
    env = os.environ.get
    spark_ip = env("SPARK_IP", "spark.local")
    return {
        # A fake server that ships with this repo (python -m felab.mock_server).
        # Lets you run every lesson on a train with no model downloaded.
        "mock": Target("mock", env("MOCK_URL", "http://localhost:9000/v1"), "mock-8b", "x",
                       "felab mock server — simulated latency, free, offline"),
        # Ollama: zero-config wrapper around llama.cpp.
        "ollama": Target("ollama", "http://localhost:11434/v1", env("OLLAMA_MODEL", "llama3.1:8b"), "x",
                         "Ollama on :11434"),
        # llama-server (llama.cpp): every knob exposed. It ignores the model field.
        "llamacpp": Target("llamacpp", "http://localhost:8080/v1", "local", "x",
                           "llama.cpp llama-server on :8080"),
        # mlx_lm.server: Apple-native. The model field must match what you served.
        "mlx": Target("mlx", env("MLX_URL", "http://localhost:8081/v1"),
                      env("MLX_MODEL", "mlx-community/Meta-Llama-3.1-8B-Instruct-4bit"), "x",
                      "mlx_lm.server on :8081"),
        # Fireworks serverless: pay per token. Check the model library for current ids.
        "fireworks": Target("fireworks", "https://api.fireworks.ai/inference/v1",
                            env("FIREWORKS_MODEL", "accounts/fireworks/models/gpt-oss-120b"),
                            env("FIREWORKS_API_KEY", ""), "Fireworks serverless (PAID)"),
        # vLLM / SGLang on the DGX Spark, reached over your LAN.
        "spark": Target("spark", env("SPARK_URL", f"http://{spark_ip}:8000/v1"),
                        env("SPARK_MODEL", "nvidia/Llama-3.1-8B-Instruct-FP8"), "x",
                        "vLLM/SGLang on the DGX Spark"),
    }


TARGETS = _targets()


def add_target_args(p: argparse.ArgumentParser, default: str | None = None) -> argparse.ArgumentParser:
    """Attach the standard --target/--model/--base-url flags to a script's parser."""
    p.add_argument("--target", default=default or os.environ.get("TARGET", "mock"), choices=TARGETS,
                   help="which server to talk to (default: $TARGET or mock)")
    p.add_argument("--model", help="override the target's default model id")
    p.add_argument("--base-url", help="override the target's URL")
    return p


def resolve(args: argparse.Namespace) -> Target:
    """Turn parsed flags into a Target, failing early with a helpful message."""
    t = TARGETS[args.target]
    t = Target(t.name, args.base_url or t.base_url, args.model or t.model, t.api_key, t.note)
    if t.is_paid and not t.api_key:
        raise SystemExit("FIREWORKS_API_KEY is not set. export it, or put it in .env (see lesson 00).")
    return t


def client(t: Target, asynchronous: bool = False):
    """An OpenAI SDK client pointed at the target. Every server here speaks the
    OpenAI chat-completions dialect, which is exactly why one harness works everywhere."""
    from openai import AsyncOpenAI, OpenAI  # imported late so --help works without the SDK
    cls = AsyncOpenAI if asynchronous else OpenAI
    return cls(base_url=t.base_url, api_key=t.api_key or "x", timeout=600)


def banner(t: Target) -> None:
    paid = "  $$ PAID ENDPOINT $$" if t.is_paid else ""
    print(f"→ target={t.name}  model={t.model}\n  {t.base_url}  ({t.note}){paid}\n")
