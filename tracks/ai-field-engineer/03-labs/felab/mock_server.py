"""
felab.mock_server — a fake OpenAI-compatible LLM server with realistic *shape*.

    python -m felab.mock_server            # listens on :9000
    python -m felab.mock_server --slots 4 --itl-ms 25

It generates no real language. What it does simulate, on purpose, is the
behaviour each lesson teaches, so you can run every script offline first
and know what "right" looks like before spending time or money:

  * PREFILL cost grows with prompt length            → lesson 01 (TTFT vs prompt size)
  * DECODE slows a little as more users share a step → lesson 03 (concurrency curve)
  * only N "slots" (batch size); extra users queue   → lesson 03 (the TTFT knee)
  * a PREFIX CACHE in 64-token blocks                → lesson 06 (shared prefixes)
  * JSON: constrained decoding always valid,
    prompt-only JSON sometimes breaks                → lesson 07 (structured output)
  * a "-lora" model id classifies tickets better     → lessons 09–11 (eval delta)

Standard library only. Not a benchmark of anything real — the numbers are made up.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CFG = {"slots": 8, "itl_ms": 18.0, "prefill_tok_per_s": 2500.0, "block": 64}
SLOTS: threading.Semaphore
ACTIVE = 0
LOCK = threading.Lock()
PREFIX_CACHE: set[str] = set()   # hashes of cached prompt blocks

WORDS = ("the cache keeps keys and values so each new token only reads what it needs while "
         "bandwidth sets the ceiling and batching shares one pass across many users").split()

# The "ground truth" the mock uses to answer ticket-triage prompts (lesson 07/09).
KEYWORDS = {  # checked in this order — abuse first so "fake invoices" is abuse, not billing
    "abuse": ["spam", "phishing", "abuse", "fraud", "stolen", "scraping"],
    "billing": ["invoice", "card", "charge", "refund", "billing", "payment", "declined"],
    "outage": ["down", "500", "timeout", "time out", "outage", "unreachable", "latency spike", "error rate"],
    "how-to": ["how do i", "how to", "where can i", "docs", "configure", "set up"],
}


def approx_tokens(text: str) -> int:
    return max(1, len(text) // 4)          # ~4 characters per token for English


def prompt_text(messages: list[dict]) -> str:
    out = []
    for m in messages:
        c = m.get("content", "")
        out.append(c if isinstance(c, str) else json.dumps(c))
    return "\n".join(out)


def uncached_tokens(text: str) -> int:
    """Walk the prompt in fixed blocks; blocks whose whole prefix was seen before are free.
    Mirrors how vLLM/SGLang/llama.cpp hash KV blocks. One changed character early on
    invalidates every block after it — that is why prompt ORDER matters."""
    block_chars = CFG["block"] * 4
    h = hashlib.sha1()
    cached_chars = 0
    new_hashes = []
    for i in range(0, len(text) - block_chars + 1, block_chars):
        h.update(text[i:i + block_chars].encode())
        key = h.hexdigest()
        if key in PREFIX_CACHE and cached_chars == i:
            cached_chars = i + block_chars
        new_hashes.append(key)
    PREFIX_CACHE.update(new_hashes)
    return approx_tokens(text[cached_chars:]) if cached_chars < len(text) else 0


def classify(text: str, model: str) -> tuple[str, int]:
    """Pretend-model: finds the true label by keyword, then is sometimes wrong.
    Base model is right ~75% of the time, a '-lora' model ~93%. Deterministic per input."""
    low = text.lower()
    truth = next((c for c, kws in KEYWORDS.items() if any(k in low for k in kws)), "how-to")
    rng = random.Random(hashlib.md5((low + model).encode()).hexdigest())
    acc = 0.93 if "lora" in model else 0.75
    label = truth if rng.random() < acc else rng.choice([c for c in KEYWORDS if c != truth])
    sev = {"outage": 4, "abuse": 4, "billing": 3, "how-to": 2}[label]
    if any(w in low for w in ("urgent", "tomorrow", "all users", "production")):
        sev = min(5, sev + 1)
    return label, sev


def fake_json(messages: list[dict], model: str, schema: dict | None) -> str:
    user_text = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")
    label, sev = classify(user_text, model)
    obj = {"category": label, "severity": sev, "next_action": f"route to {label} queue"}
    if schema and "properties" in schema:  # only keep fields the schema asks for
        obj = {k: v for k, v in obj.items() if k in schema["properties"]} or obj
    return json.dumps(obj)


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):  # keep the terminal quiet
        pass

    def _json(self, code: int, obj: dict) -> None:
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.rstrip("/") in ("/health", "/v1/health"):
            return self._json(200, {"status": "ok"})
        if self.path.startswith("/v1/models"):
            return self._json(200, {"object": "list", "data": [{"id": "mock-8b", "object": "model"},
                                                              {"id": "mock-8b-lora", "object": "model"}]})
        self._json(404, {"error": "not found"})

    def do_POST(self):
        if not self.path.endswith("/chat/completions"):
            return self._json(404, {"error": "only /v1/chat/completions is mocked"})
        req = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        global ACTIVE
        SLOTS.acquire()                      # queue here if all batch slots are busy
        with LOCK:
            ACTIVE += 1
        try:
            self._complete(req)
        finally:
            with LOCK:
                ACTIVE -= 1
            SLOTS.release()

    def _complete(self, req: dict) -> None:
        messages = req.get("messages", [])
        model = req.get("model", "mock-8b")
        max_tokens = int(req.get("max_tokens") or 256)
        text = prompt_text(messages)
        prompt_toks = approx_tokens(text)

        # ---- PREFILL: pay only for the part of the prompt that is not cached ----
        todo = uncached_tokens(text)
        time.sleep(0.015 + todo / CFG["prefill_tok_per_s"])

        # ---- choose what to "generate" ----
        rf = req.get("response_format") or {}
        wants_json = "json" in text.lower() or rf.get("type") in ("json_object", "json_schema")
        if "rubric" in text.lower():          # acting as an LLM judge (lesson 09)
            # score high if the proposed action routes to the ticket's true category
            ticket = text.split("Ticket:")[-1].split("Proposed next_action:")[0].lower()
            action = text.split("Proposed next_action:")[-1].split("Rubric:")[0].lower()
            truth = next((c for c, kws in KEYWORDS.items() if any(k in ticket for k in kws)), "how-to")
            rng = random.Random(text)
            score = rng.choice([4, 5, 5]) if truth in action else rng.choice([1, 2, 3])
            pieces = [json.dumps({"score": score})]
        elif wants_json:
            schema = (rf.get("json_schema") or {}).get("schema")
            out = fake_json(messages, model, schema)
            constrained = rf.get("type") in ("json_object", "json_schema")
            # Without constrained decoding a small model sometimes wraps or truncates JSON.
            if not constrained and random.Random(text).random() < 0.12:
                out = "Sure! Here is the JSON:\n" + out[:-3]
            pieces = [out[i:i + 4] for i in range(0, len(out), 4)]
        else:
            rng = random.Random(text)
            n = min(max_tokens, rng.randint(60, 200))
            pieces = [(" " if i else "") + rng.choice(WORDS) for i in range(n)]
        pieces = pieces[:max_tokens]

        if not req.get("stream"):
            time.sleep(len(pieces) * self._itl())
            return self._json(200, {
                "id": "mock-1", "object": "chat.completion", "model": model,
                "choices": [{"index": 0, "finish_reason": "stop",
                             "message": {"role": "assistant", "content": "".join(pieces)}}],
                "usage": {"prompt_tokens": prompt_toks, "completion_tokens": len(pieces),
                          "total_tokens": prompt_toks + len(pieces),
                          "prompt_tokens_details": {"cached_tokens": prompt_toks - todo}}})

        # ---- DECODE: stream one piece per step, like a real server ----
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()
        try:
            for p in pieces:
                chunk = {"id": "mock-1", "object": "chat.completion.chunk", "model": model,
                         "choices": [{"index": 0, "delta": {"content": p}, "finish_reason": None}]}
                self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
                self.wfile.flush()
                time.sleep(self._itl())
            done = {"id": "mock-1", "object": "chat.completion.chunk", "model": model,
                    "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}
            self.wfile.write(f"data: {json.dumps(done)}\n\ndata: [DONE]\n\n".encode())
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        self.close_connection = True

    @staticmethod
    def _itl() -> float:
        """One decode step. Each extra user in the batch adds ~6% — the step is
        memory-bound, so sharing it is cheap. That is why batching raises throughput."""
        return CFG["itl_ms"] / 1000 * (1 + 0.06 * max(0, ACTIVE - 1))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=9000)
    ap.add_argument("--slots", type=int, default=CFG["slots"], help="max concurrent sequences (batch size)")
    ap.add_argument("--itl-ms", type=float, default=CFG["itl_ms"], help="single-user decode step")
    a = ap.parse_args()
    CFG.update(slots=a.slots, itl_ms=a.itl_ms)
    global SLOTS
    SLOTS = threading.Semaphore(a.slots)
    print(f"mock LLM on http://localhost:{a.port}/v1  slots={a.slots}  itl={a.itl_ms}ms  (Ctrl-C to stop)")
    ThreadingHTTPServer(("0.0.0.0", a.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
