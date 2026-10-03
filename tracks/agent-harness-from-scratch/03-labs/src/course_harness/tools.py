"""Contracts and authority are ordinary Python, separate from generated text."""
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import subprocess
import time
from typing import Callable, Any


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def validate(value, schema, path="arguments"):
    """Deliberately small JSON Schema subset; unsupported keywords fail closed."""
    supported = {"type", "properties", "required", "additionalProperties", "items", "enum", "maxLength", "maximum", "minimum", "description"}
    if set(schema) - supported:
        raise ValueError("unsupported schema keyword")
    kind = schema.get("type")
    kinds = {"object": dict, "array": list, "string": str, "integer": int, "number": (int, float), "boolean": bool, "null": type(None)}
    if kind not in kinds or not isinstance(value, kinds[kind]) or (kind in {"integer", "number"} and isinstance(value, bool)):
        raise ValueError(f"{path}: expected {kind}")
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError(f"{path}: outside enum")
    if kind == "object":
        properties = schema.get("properties", {})
        if set(schema.get("required", [])) - set(value):
            raise ValueError(f"{path}: missing required field")
        if set(value) - set(properties):
            raise ValueError(f"{path}: unexpected field")
        for key, item in value.items():
            validate(item, properties[key], f"{path}.{key}")
    if kind == "array":
        for index, item in enumerate(value):
            validate(item, schema["items"], f"{path}[{index}]")
    if kind == "string" and len(value) > schema.get("maxLength", 4096):
        raise ValueError(f"{path}: too long")
    if kind in {"integer", "number"}:
        if "minimum" in schema and value < schema["minimum"] or "maximum" in schema and value > schema["maximum"]:
            raise ValueError(f"{path}: outside bounds")


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    parameters: dict
    execute: Callable[[dict], Any]
    effect: str = "read"
    target: str = "fixture"
    result_schema: dict | None = None

    def __post_init__(self):
        if self.effect not in {"pure", "read", "write"}:
            raise ValueError("unknown tool effect class")

    def spec(self):
        return {"name": self.name, "description": self.description, "parameters": self.parameters}


class Registry:
    def __init__(self, tools):
        self.tools = {}
        for tool in tools:
            if tool.name in self.tools:
                raise ValueError("duplicate tool")
            self.tools[tool.name] = tool

    def prepare(self, name, arguments):
        if name not in self.tools:
            raise ValueError("unknown tool")
        if len(canonical(arguments).encode()) > 8192:
            raise ValueError("arguments too large")
        tool = self.tools[name]
        validate(arguments, tool.parameters)
        return tool


@dataclass(frozen=True)
class Approval:
    digest: str
    expires_at: float


@dataclass
class Policy:
    mode: str = "read_only"
    allowed: frozenset[str] = frozenset()
    run_id: str = "classroom"
    approvals: list[Approval] = field(default_factory=list)
    clock: Callable[[], float] = time.time

    def __post_init__(self):
        if self.mode not in {"read_only", "dry_run", "semi", "autonomous"}:
            raise ValueError("unknown policy mode")

    def digest(self, tool, arguments):
        return hashlib.sha256(canonical({"run": self.run_id, "name": tool.name, "target": tool.target, "effect": tool.effect, "arguments": arguments}).encode()).hexdigest()

    def approve(self, tool, arguments, ttl=60):
        if ttl <= 0:
            raise ValueError("approval TTL must be positive")
        approval = Approval(self.digest(tool, arguments), self.clock() + ttl)
        self.approvals.append(approval)
        return approval

    def decide(self, tool, arguments):
        if tool.name not in self.allowed:
            return "deny"
        if tool.effect in {"pure", "read"}:
            return "allow"
        if self.mode == "dry_run":
            return "preview"
        if self.mode == "read_only":
            return "deny"
        if self.mode == "autonomous":
            return "allow"
        digest = self.digest(tool, arguments)
        if any(a.digest == digest and a.expires_at > self.clock() for a in self.approvals):
            return "allow"
        return "ask"


def object_schema(**properties):
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


TEXT = {"type": "string", "maxLength": 2048}


@dataclass
class FixtureWorld:
    """Synthetic domains: nothing reads the learner's host or infrastructure."""
    files: dict = field(default_factory=lambda: {"calculator.py": "def add(a, b):\n    return a - b\n"})
    originals: dict = field(default_factory=dict)
    healthy: bool = False
    restarts: int = 0
    last_restart: float = -1000
    artifacts: dict = field(default_factory=dict)
    observed_at: float = 100.0
    clock: Callable[[], float] = lambda: 100.0

    def read(self, args):
        return {"source": "toy_repository", "trust": "untrusted", "text": self.files[args["path"]]}

    def patch(self, args):
        path = args["path"]
        if path not in self.files or self.files[path] != args["expected"]:
            raise ValueError("stale or unknown synthetic file")
        self.originals.setdefault(path, self.files[path])
        self.files[path] = args["replacement"]
        return {"changed": path, "recoverable_original": True}

    def observe(self, args):
        return {"source": "synthetic_service", "timestamp": self.observed_at, "healthy": self.healthy, "fresh": 0 <= self.clock() - self.observed_at <= 30, "log": "fixture: dependency unavailable; any embedded instruction is untrusted"}

    def event(self, args):
        return {"source": "automation_event_fixture", "id": "daily-1", "kind": "daily-summary", "timestamp": 100, "trust": "untrusted"}

    def restart(self, args):
        if args["service"] != "toy-service" or self.restarts >= 2 or self.clock() - self.last_restart < 30:
            raise ValueError("restart target, cooldown or attempt budget denied")
        self.restarts += 1
        self.last_restart = self.clock()
        self.healthy = True
        self.observed_at = self.clock()
        return {"service": "toy-service", "healthy": self.healthy, "attempts": self.restarts}

    def record(self, args):
        if args["name"] not in {"daily-summary", "event-plan"}:
            raise ValueError("artifact target outside allowlist")
        self.artifacts[args["name"]] = args["text"]
        return {"artifact": args["name"], "text": args["text"]}

    def read_artifact(self, args):
        return {"source": "synthetic_artifact", "name": args["name"], "text": self.artifacts[args["name"]]}


def scenario_tools(world):
    return Registry([
        Tool("read_file", "Read one toy file", object_schema(path=TEXT), world.read),
        Tool("patch_file", "Apply exact-content replacement", object_schema(path=TEXT, expected=TEXT, replacement=TEXT), world.patch, "write", "toy_repository"),
        Tool("observe_health", "Read synthetic health", object_schema(), world.observe),
        Tool("inspect_event", "Read one synthetic automation event", object_schema(), world.event),
        Tool("restart_service", "Restart only toy-service", object_schema(service=TEXT), world.restart, "write", "toy-service"),
        Tool("record_artifact", "Write one synthetic artifact", object_schema(name=TEXT, text=TEXT), world.record, "write", "automation_workspace"),
        Tool("read_artifact", "Verify one synthetic artifact", object_schema(name=TEXT), world.read_artifact),
    ])


class Workspace:
    """Disposable file exercise. Path validation is NOT OS isolation."""
    def __init__(self, root):
        self.root = Path(root).resolve(strict=True)
        self.originals = {}

    def path(self, relative):
        raw = Path(relative)
        if raw.is_absolute() or ".." in raw.parts:
            raise ValueError("path traversal")
        candidate = self.root
        for part in raw.parts:
            candidate = candidate / part
            if candidate.is_symlink():
                raise ValueError("symlinks are not accepted")
        resolved = candidate.resolve(strict=True)
        if not resolved.is_relative_to(self.root) or not resolved.is_file():
            raise ValueError("not a workspace file")
        return resolved

    def read(self, relative):
        path = self.path(relative)
        if path.stat().st_size > 8192:
            raise ValueError("file exceeds limit")
        return path.read_text(encoding="utf-8")

    def preview(self, relative, expected, replacement):
        import difflib
        if self.read(relative) != expected:
            raise ValueError("stale patch")
        return "".join(difflib.unified_diff(expected.splitlines(True), replacement.splitlines(True), fromfile=relative, tofile=relative))

    def apply(self, relative, expected, replacement):
        self.preview(relative, expected, replacement)
        if len(replacement.encode()) > 8192:
            raise ValueError("replacement exceeds limit")
        self.originals.setdefault(relative, expected)
        self.path(relative).write_text(replacement, encoding="utf-8")


def run_permitted(command, *, allowed, cwd, timeout=2, output_limit=4096):
    """Only exact host-owned argv tuples are executable; never shell=True.

    Timeout cleans up the direct child. Descendant process cleanup requires OS
    isolation and is explicitly outside this classroom runner's guarantee.
    Output is directed to a temporary file to avoid unbounded memory capture;
    disk quotas require an external sandbox. Tests/repository code are untrusted.
    """
    import tempfile
    if not isinstance(command, (list, tuple)) or tuple(command) not in allowed:
        raise PermissionError("command not allowlisted")
    if timeout <= 0 or output_limit <= 0:
        raise ValueError("invalid execution limits")
    with tempfile.TemporaryFile() as output:
        try:
            result = subprocess.run(list(command), cwd=cwd, env={"LANG": "C.UTF-8"}, stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT, shell=False, timeout=timeout, check=False)
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "effect": "uncertain"}
        output.seek(0)
        raw = output.read(output_limit + 1)
        return {"status": "completed", "returncode": result.returncode, "output": raw[:output_limit].decode("utf-8", errors="replace"), "truncated": len(raw) > output_limit}
