"""Bounded structured traces; unknown usage is different from zero."""
from dataclasses import dataclass, field
import json


class TraceSink:
    def __init__(self, *, run_id, task_id, parent_id=None, clock=lambda: 0.0, secrets=(), max_events=100, max_chars=1024):
        if max_events < 1 or max_chars < 128:
            raise ValueError("invalid trace bounds")
        self.run_id, self.task_id, self.parent_id = run_id, task_id, parent_id
        self.clock, self.secrets = clock, tuple(s for s in secrets if s)
        self.max_events, self.max_chars = max_events, max_chars
        self.events = []
        self.dropped = 0

    def redact(self, value):
        if isinstance(value, dict):
            return {str(k): "[REDACTED]" if any(word in str(k).lower() for word in ("password", "api_key", "authorization", "credential")) else self.redact(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [self.redact(v) for v in value]
        if isinstance(value, str):
            for secret in self.secrets:
                value = value.replace(secret, "[REDACTED]")
            return value[:self.max_chars] + ("[TRUNCATED]" if len(value) > self.max_chars else "")
        return value

    def emit(self, event, **fields):
        if len(self.events) >= self.max_events:
            self.dropped += 1
            return
        # Caller data cannot replace correlation identifiers.
        record = self.redact(fields) | {"event": event, "run_id": self.run_id, "task_id": self.task_id, "parent_id": self.parent_id, "at": self.clock()}
        if len(json.dumps(record)) > self.max_chars * 4:
            record = {"event": event, "run_id": self.run_id, "task_id": self.task_id, "at": self.clock(), "truncated": True}
        self.events.append(record)


@dataclass
class UsageLedger:
    calls: int = 0
    retries: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    unknown_calls: int = 0

    def record(self, usage, *, retried=False):
        self.calls += 1
        self.retries += int(retried)
        if set(usage) < {"input_tokens", "output_tokens"} or not all(type(usage.get(k)) is int and usage[k] >= 0 for k in ("input_tokens", "output_tokens")):
            self.unknown_calls += 1
        for key in ("input_tokens", "output_tokens"):
            value = usage.get(key)
            if type(value) is int and value >= 0:
                setattr(self, key, getattr(self, key) + value)

    def estimate(self, *, input_per_million=None, output_per_million=None):
        if self.unknown_calls or input_per_million is None or output_per_million is None:
            return {"estimated_cost": None, "advisory": True, "unknown_calls": self.unknown_calls}
        if input_per_million < 0 or output_per_million < 0:
            raise ValueError("rates must be nonnegative")
        return {"estimated_cost": (self.input_tokens * input_per_million + self.output_tokens * output_per_million) / 1_000_000, "advisory": True, "unknown_calls": 0}
