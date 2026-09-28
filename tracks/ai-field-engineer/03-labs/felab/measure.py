"""
felab.measure — the two numbers every inference conversation is about.

    TTFT  time to first token   = queue + PREFILL (reading the whole prompt)
    ITL   inter-token latency   = one DECODE step (writing one more token)

Users feel TTFT as "is it thinking?" and ITL as "how fast does it type?".
They are driven by different things (compute vs memory bandwidth), so we
ALWAYS report them separately — an average "latency" hides both.

Note: we count streamed chunks as tokens. Most servers send one token per
chunk; a few batch several. For exact counts use `usage` (non-streaming).
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field


@dataclass
class Sample:
    ttft_ms: float                 # prompt sent → first visible token
    itl_ms: list[float] = field(default_factory=list)  # gap between consecutive tokens
    tokens: int = 0                # streamed chunks with content
    total_s: float = 0.0           # whole request wall time
    text: str = ""

    @property
    def itl_median(self) -> float:
        return percentile(self.itl_ms, 50) if self.itl_ms else 0.0

    @property
    def decode_tps(self) -> float:
        """Tokens per second for ONE user once text starts flowing."""
        return 1000.0 / self.itl_median if self.itl_median else 0.0


def percentile(xs: list[float], p: float) -> float:
    """Nearest-rank percentile. p95 of 10 samples is the worst one — that is
    deliberate: tails are what customers complain about."""
    if not xs:
        return float("nan")
    s = sorted(xs)
    k = max(0, min(len(s) - 1, math.ceil(p / 100 * len(s)) - 1))
    return s[k]


def _content(chunk) -> str:
    """Pull visible text out of a streamed chunk. Reasoning models may stream
    `reasoning_content` first; we count that too because the user waits for it."""
    if not chunk.choices:
        return ""
    d = chunk.choices[0].delta
    return (getattr(d, "content", None) or getattr(d, "reasoning_content", None) or "")


def stream_once(cli, model: str, messages: list[dict], max_tokens: int = 192, **extra) -> Sample:
    """Send one streaming request and time every token (sync client)."""
    t0 = time.perf_counter()
    stamps: list[float] = []
    parts: list[str] = []
    for ch in cli.chat.completions.create(model=model, messages=messages, max_tokens=max_tokens,
                                          stream=True, **extra):
        piece = _content(ch)
        if piece:
            stamps.append(time.perf_counter())
            parts.append(piece)
    return _to_sample(t0, stamps, parts)


async def astream_once(cli, model: str, messages: list[dict], max_tokens: int = 128, **extra) -> Sample:
    """Same as stream_once for an AsyncOpenAI client (used by the concurrency sweep)."""
    t0 = time.perf_counter()
    stamps: list[float] = []
    parts: list[str] = []
    stream = await cli.chat.completions.create(model=model, messages=messages, max_tokens=max_tokens,
                                               stream=True, **extra)
    async for ch in stream:
        piece = _content(ch)
        if piece:
            stamps.append(time.perf_counter())
            parts.append(piece)
    return _to_sample(t0, stamps, parts)


def _to_sample(t0: float, stamps: list[float], parts: list[str]) -> Sample:
    end = time.perf_counter()
    if not stamps:  # server returned nothing visible
        return Sample(ttft_ms=(end - t0) * 1000, total_s=end - t0)
    itl = [(b - a) * 1000 for a, b in zip(stamps, stamps[1:])]
    return Sample(ttft_ms=(stamps[0] - t0) * 1000, itl_ms=itl, tokens=len(stamps),
                  total_s=end - t0, text="".join(parts))


def user(prompt: str, system: str | None = None) -> list[dict]:
    """Build a chat message list."""
    msgs = [{"role": "system", "content": system}] if system else []
    return msgs + [{"role": "user", "content": prompt}]
