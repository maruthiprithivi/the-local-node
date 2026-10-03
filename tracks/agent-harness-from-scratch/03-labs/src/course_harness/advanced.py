"""Small, inspectable advanced fixtures. No generated code or plugins are executed.

These are classroom boundaries, not isolation from malicious Python running in
the same process. Clocks, observations and reviewers are supplied by the host.
"""

from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from hashlib import sha256
import json
from math import isfinite
import sqlite3
from threading import Event, Lock, local
from typing import Callable


class BoundaryError(ValueError):
    """An explicit course boundary rejected the request."""


class MemoryStore:
    """Explicit long-term memory; never use retrieved prose as permission.

    Retention applies to current records AND their correction history. Deleting
    a key removes both. Secret exclusion requires classification by the caller
    and known-secret checks; it is not a general secret detector.
    """

    def __init__(self, path, clock: Callable[[], float], known_secrets=()):
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.clock = clock
        self.known_secrets = tuple(s for s in known_secrets if s)
        self.db.execute("""CREATE TABLE IF NOT EXISTS memory (
            scope TEXT, key TEXT, revision INTEGER, value TEXT, source TEXT,
            created REAL, expires REAL, PRIMARY KEY(scope, key, revision))""")
        self.db.commit()

    def close(self):
        self.db.close()

    def put(self, scope: str, key: str, value: str, source: str,
            retention: float, *, classification="public") -> int:
        if not all(isinstance(x, str) and x for x in (scope, key, value, source)):
            raise BoundaryError("memory requires nonempty scope, key, value and source")
        if len(scope) > 256 or len(key) > 256 or len(source) > 512:
            raise BoundaryError("memory metadata limit")
        if classification != "public" or any(
            secret in text for secret in self.known_secrets
            for text in (scope, key, value, source)
        ):
            raise BoundaryError("secret or unclassified memory rejected")
        if type(retention) not in (int, float) or not isfinite(retention) or retention <= 0 or len(value) > 4096:
            raise BoundaryError("memory retention/output limit")
        now = self.clock()
        with self.db:
            revision = self.db.execute(
                "SELECT COALESCE(MAX(revision), 0) + 1 FROM memory WHERE scope=? AND key=?",
                (scope, key),
            ).fetchone()[0]
            self.db.execute("INSERT INTO memory VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                            (scope, key, revision, value, source, now, now + retention))
        return revision

    def inspect(self, scope: str, key: str) -> list[dict]:
        """Include stale revisions for explicit inspection, with trust labels."""
        rows = self.db.execute(
            "SELECT * FROM memory WHERE scope=? AND key=? ORDER BY revision", (scope, key)
        ).fetchall()
        return [dict(row) | {"stale": row["expires"] <= self.clock(),
                             "trust": "untrusted-memory"} for row in rows]

    def retrieve(self, scope: str, query="") -> list[dict]:
        # Select latest first: an expired correction must not resurrect old facts.
        rows = self.db.execute("""SELECT m.* FROM memory m WHERE m.scope=?
            AND m.revision=(SELECT MAX(revision) FROM memory
                            WHERE scope=m.scope AND key=m.key)
            ORDER BY m.key""", (scope,)).fetchall()
        return [dict(row) | {"trust": "untrusted-memory"} for row in rows
                if row["expires"] > self.clock()
                and query.casefold() in (row["key"] + " " + row["value"]).casefold()]

    def delete(self, scope: str, key: str):
        with self.db:
            self.db.execute("DELETE FROM memory WHERE scope=? AND key=?", (scope, key))

    def prune(self):
        """Remove whole expired keys, then expired correction history."""
        now = self.clock()
        with self.db:
            self.db.execute("""DELETE FROM memory WHERE (scope, key) IN (
                SELECT scope, key FROM memory m WHERE expires<=?
                AND revision=(SELECT MAX(revision) FROM memory
                              WHERE scope=m.scope AND key=m.key))""", (now,))
            self.db.execute("DELETE FROM memory WHERE expires<=?", (now,))


@dataclass(frozen=True)
class EffectiveConfig:
    provider: str = "fake"
    max_steps: int = 8
    allowed_tools: frozenset[str] = frozenset()
    approvals_required: bool = True


def merge_config(host: EffectiveConfig, project: Mapping,
                 allowed_providers=frozenset({"fake"})) -> EffectiveConfig:
    """Host owns authority; project may narrow it. No credential fields exist."""
    if not isinstance(host, EffectiveConfig) or not isinstance(project, Mapping):
        raise BoundaryError("configuration requires a validated host and project mapping")
    if (type(host.max_steps) is not int or host.max_steps <= 0
            or type(host.approvals_required) is not bool
            or not isinstance(host.provider, str) or host.provider not in allowed_providers
            or not isinstance(host.allowed_tools, frozenset)
            or not all(isinstance(tool, str) and tool for tool in host.allowed_tools)):
        raise BoundaryError("invalid host configuration")
    if set(project) - {"provider", "max_steps", "allowed_tools", "approvals_required"}:
        raise BoundaryError("unknown project configuration")
    provider = project.get("provider", host.provider)
    steps = project.get("max_steps", host.max_steps)
    tools = project.get("allowed_tools", host.allowed_tools)
    approval = project.get("approvals_required", host.approvals_required)
    if not isinstance(provider, str) or provider not in allowed_providers:
        raise BoundaryError("provider destination not configured by host")
    if type(steps) is not int or not 0 < steps <= host.max_steps:
        raise BoundaryError("project cannot increase step budget")
    if not isinstance(tools, (list, tuple, set, frozenset)) or not all(
        isinstance(tool, str) for tool in tools
    ) or not frozenset(tools) <= host.allowed_tools:
        raise BoundaryError("project cannot expand tool authority")
    if type(approval) is not bool or (host.approvals_required and not approval):
        raise BoundaryError("project cannot disable host approval")
    return EffectiveConfig(provider, steps, frozenset(tools), approval)


@dataclass(frozen=True)
class Skill:
    name: str
    instructions: str

    def context(self) -> dict:
        return {"name": self.name, "text": self.instructions, "trust": "untrusted-skill"}


@dataclass(frozen=True)
class PluginManifest:
    name: str
    version: str
    capabilities: frozenset[str]


class PluginGate:
    """Check a host-installed manifest; this class does not load plugin code."""

    def __init__(self, trusted_versions: Mapping[str, str], allowed_capabilities):
        self.trusted_versions = dict(trusted_versions)
        self.allowed_capabilities = frozenset(allowed_capabilities)

    def authorize(self, manifest: PluginManifest, requested: str) -> str:
        if self.trusted_versions.get(manifest.name) != manifest.version:
            raise BoundaryError("plugin/version not trusted")
        if not manifest.capabilities <= self.allowed_capabilities:
            raise BoundaryError("plugin manifest expands host authority")
        if requested not in manifest.capabilities:
            raise BoundaryError("plugin capability not declared")
        return requested


@dataclass(frozen=True)
class AssembledResponse:
    text: str
    calls: tuple[dict, ...]
    interrupted: bool
    reason: str


class StreamAssembler:
    """Normalized ordered events, after a provider-specific decoder.

    Events are text/tool/end. Sequence numbers include end. Tool fragments use
    a stable ID and repeat the same name. No calls are exposed before finish.
    Disconnect, malformed fragments and cancellation discard ALL pending calls.
    """

    def __init__(self, validate: Callable[[dict], None], limit=8192):
        if type(limit) is not int or limit < 1:
            raise BoundaryError("invalid stream limit")
        self.validate = validate
        self.limit = limit
        self.sequence = 0
        self.text = ""
        self.fragments = {}
        self.size = 0
        self.ended = False
        self.error = ""
        self.result = None

    def feed(self, event: Mapping):
        if self.result is not None or self.error:
            raise BoundaryError("stream already closed")
        if self.sequence >= 1024:
            self.error = "stream fragment count limit"
            return
        if self.ended or type(event.get("sequence")) is not int or event.get("sequence") != self.sequence:
            self.error = "out-of-order or extra stream fragment"
            return
        self.sequence += 1
        kind = event.get("kind")
        if kind == "end" and set(event) == {"sequence", "kind"}:
            self.ended = True
            return
        delta = event.get("delta")
        if not isinstance(delta, str):
            self.error = "invalid stream delta"
            return
        self.size += len(delta.encode("utf-8"))
        if self.size > self.limit:
            self.error = "stream output limit"
            return
        if kind == "text" and set(event) == {"sequence", "kind", "delta"}:
            self.text += delta
        elif kind == "tool" and set(event) == {"sequence", "kind", "delta", "id", "name"}:
            call_id, name = event["id"], event["name"]
            if not all(isinstance(x, str) and x for x in (call_id, name)):
                self.error = "invalid tool fragment identity"
                return
            if len(call_id) > 256 or len(name) > 256 or (call_id not in self.fragments and len(self.fragments) >= 16):
                self.error = "tool fragment identity/count limit"
                return
            old_name, arguments = self.fragments.get(call_id, (name, ""))
            if name != old_name:
                self.error = "tool fragment changed name"
                return
            self.fragments[call_id] = (name, arguments + delta)
        else:
            self.error = "unknown stream event/fields"

    def finish(self, *, cancelled=False) -> AssembledResponse:
        if self.result is not None:
            return self.result
        reason = "cancelled" if cancelled else self.error or ("" if self.ended else "disconnected")
        calls = []
        if not reason:
            try:
                for call_id, (name, fragments) in self.fragments.items():
                    def invalid_constant(value):
                        raise BoundaryError("nonfinite JSON argument")
                    arguments = json.loads(fragments, parse_constant=invalid_constant)
                    if not isinstance(arguments, dict):
                        raise BoundaryError("tool arguments must be an object")
                    calls.append({"id": call_id, "name": name, "arguments": arguments})
                # Parse every call before validation; malformed siblings invalidate all.
                for call in calls:
                    self.validate(call)
            except (ValueError, TypeError) as exc:
                reason = "invalid complete stream: " + str(exc)
        self.result = AssembledResponse(self.text, () if reason else tuple(calls), bool(reason), reason)
        return self.result


@dataclass(frozen=True)
class Handover:
    goal: str
    evidence: tuple[str, ...]
    changes: tuple[str, ...]
    completed_actions: frozenset[str]
    pending_actions: frozenset[str]
    uncertainty: tuple[str, ...]
    remaining_steps: int
    permissions: frozenset[str]
    required_capabilities: frozenset[str]
    source: str = "fake-local"
    locality: str = "local"


def validate_handover(packet: Handover, *, destination: str, configured_destinations,
                      receiver_capabilities, receiver_permissions,
                      approved_localities=frozenset({"local"}), destination_locality="local",
                      receiver_steps: int, credentials_ready=True, reason: str) -> dict:
    """Return an auditable switch record; no provider is contacted."""
    if not reason or destination not in configured_destinations or not credentials_ready:
        raise BoundaryError("handover destination/reason/credentials not configured")
    if type(packet.remaining_steps) is not int or packet.remaining_steps < 0:
        raise BoundaryError("invalid source budget")
    if destination_locality not in approved_localities:
        raise BoundaryError("data locality requires host approval")
    if packet.locality == "local" and destination_locality != "local" and "hosted" not in approved_localities:
        raise BoundaryError("local content cannot silently move to hosted provider")
    if not packet.required_capabilities <= frozenset(receiver_capabilities):
        raise BoundaryError("receiver lacks required capabilities")
    if not frozenset(receiver_permissions) <= packet.permissions:
        raise BoundaryError("handover cannot expand authority")
    if packet.completed_actions & packet.pending_actions:
        raise BoundaryError("completed actions cannot be pending again")
    if type(receiver_steps) is not int or not 0 <= receiver_steps <= packet.remaining_steps:
        raise BoundaryError("handover cannot increase remaining budget")
    return {"source": packet.source, "destination": destination, "reason": reason,
            "remaining_steps": receiver_steps, "completed": sorted(packet.completed_actions),
            "pending": sorted(packet.pending_actions), "trust": "untrusted-handover"}


@dataclass(frozen=True)
class WorkerTask:
    task_id: str
    scope: str
    operation: str = "read"


@dataclass(frozen=True)
class WorkerResult:
    task_id: str
    status: str
    value: object = None
    trust: str = "untrusted-worker"


class SharedBudget:
    def __init__(self, units: int, cancel: Event):
        if type(units) is not int or units < 0:
            raise BoundaryError("invalid worker budget")
        self.remaining = units
        self.cancel = cancel
        self.lock = Lock()

    def consume(self):
        with self.lock:
            if self.cancel.is_set():
                raise BoundaryError("cancelled")
            if self.remaining <= 0:
                raise BoundaryError("global budget exhausted")
            self.remaining -= 1


@dataclass(frozen=True)
class WorkerContext:
    task: WorkerTask
    budget: SharedBudget

    def read(self, scope: str, observation: Callable[[], object]):
        if scope != self.task.scope:
            raise BoundaryError("worker scope mismatch")
        self.budget.consume()
        value = observation()
        if self.budget.cancel.is_set():
            raise BoundaryError("cancelled")
        return value


_worker_state = local()


def coordinate(tasks, worker: Callable[[WorkerContext], object], *,
               units=8, concurrency=2, cancel=None) -> tuple[WorkerResult, ...]:
    """At most two trusted cooperative read-only workers, sharing one budget.

    Threads cannot forcibly stop a hung/malicious callable. Real untrusted or
    noncooperative tools need process isolation, covered as an optional extension.
    Budget allocation between simultaneous workers may vary; result order does not.
    """
    if getattr(_worker_state, "active", False):
        raise BoundaryError("recursive worker spawning disabled")
    tasks = tuple(tasks)
    if type(concurrency) is not int or not 1 <= concurrency <= 2 or len(tasks) > 32:
        raise BoundaryError("worker admission limit")
    if len({t.task_id for t in tasks}) != len(tasks):
        raise BoundaryError("duplicate worker task IDs")
    if any(t.operation != "read" or not t.scope or not t.task_id for t in tasks):
        raise BoundaryError("workers require explicit read-only scopes")
    budget = SharedBudget(units, cancel if cancel is not None else Event())

    def run(task):
        _worker_state.active = True
        try:
            budget.consume()
            value = worker(WorkerContext(task, budget))
            if budget.cancel.is_set():
                raise BoundaryError("cancelled")
            return WorkerResult(task.task_id, "completed", value)
        except Exception as exc:
            # Keep the failure visible without embedding potentially secret messages.
            return WorkerResult(task.task_id, "cancelled" if budget.cancel.is_set() else "failed",
                                type(exc).__name__)
        finally:
            _worker_state.active = False

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [pool.submit(run, task) for task in tasks]
        return tuple(future.result() for future in futures)


def merge_worker_findings(results: tuple[WorkerResult, ...]) -> dict:
    """Conflicting read observations stay visible; no worker prose authorizes writes."""
    findings, conflicts, failures = {}, {}, []
    for result in results:
        if result.status != "completed" or not isinstance(result.value, dict):
            failures.append(result.task_id)
            continue
        for key, value in result.value.items():
            if key in conflicts:
                conflicts[key].append(value)
            elif key in findings and findings[key] != value:
                conflicts[key] = [findings.pop(key), value]
            else:
                findings[key] = value
    return {"findings": findings, "conflicts": conflicts, "failed_tasks": failures,
            "trust": "untrusted-worker"}


class ReadCache:
    """Only cache read observations; scope and state/config versions are keys."""

    def __init__(self, limit=16):
        if type(limit) is not int or limit < 1:
            raise BoundaryError("invalid cache limit")
        self.limit = limit
        self.entries = {}

    def read(self, scope: str, key: str, state_version: str, config_version: str,
             loader: Callable[[], object], *, operation="read", verify_effect=False):
        if operation != "read" or verify_effect:
            raise BoundaryError("cache cannot perform or verify side effects")
        if not all(isinstance(x, str) and x for x in (scope, key, state_version, config_version)):
            raise BoundaryError("cache needs explicit scope and versions")
        cache_key = (scope, key, state_version, config_version)
        if cache_key not in self.entries:
            value = loader()
            # JSON copies keep callers from mutating shared cached observations.
            snapshot = json.dumps(value, allow_nan=False)
            if len(snapshot) > 8192:
                raise BoundaryError("cache entry too large")
            if len(self.entries) >= self.limit:
                self.entries.pop(next(iter(self.entries)))
            self.entries[cache_key] = snapshot
        return json.loads(self.entries[cache_key])


@dataclass(frozen=True)
class Evaluation:
    task_id: str
    scenario: str
    split: str
    outcome: bool
    unsafe_attempts: int
    steps: int
    latency: float
    usage: int | None
    configuration_version: str
    fixture_version: str


def evaluate(records: tuple[Evaluation, ...]) -> dict:
    if not records or len({r.task_id for r in records}) != len(records):
        raise BoundaryError("evaluations need nonempty unique task IDs")
    for r in records:
        if r.scenario not in {"coding", "sre", "automation"} or r.split not in {"development", "held-out"}:
            raise BoundaryError("unknown evaluation scenario/split")
        if type(r.outcome) is not bool or any(type(n) is not int or n < 0 for n in (r.unsafe_attempts, r.steps)):
            raise BoundaryError("invalid evaluation outcome/count")
        if type(r.latency) not in (int, float) or not isfinite(r.latency) or r.latency < 0 or (r.usage is not None and (type(r.usage) is not int or r.usage < 0)):
            raise BoundaryError("invalid evaluation measurement")
        if not r.configuration_version or not r.fixture_version:
            raise BoundaryError("evaluations must record versions")
    return {"sample_size": len(records),
            "configuration_versions": sorted({r.configuration_version for r in records}),
            "fixture_versions": sorted({r.fixture_version for r in records}),
            "task_sets": sorted({r.split for r in records}),
            "successes": sum(r.outcome and r.unsafe_attempts == 0 for r in records),
            "unsafe_attempts": sum(r.unsafe_attempts for r in records),
            "steps": sum(r.steps for r in records),
            "latency": sum(r.latency for r in records),
            "usage": None if any(r.usage is None for r in records) else sum(r.usage for r in records)}


def compare_evaluations(baseline: tuple[Evaluation, ...], candidate: tuple[Evaluation, ...]) -> dict:
    def identities(rows):
        return {(r.task_id, r.scenario, r.split, r.fixture_version) for r in rows}
    if identities(baseline) != identities(candidate):
        raise BoundaryError("comparison needs the same tasks/splits/fixtures")
    old, new = evaluate(baseline), evaluate(candidate)
    # An average improvement does not excuse even one new per-task regression.
    by_id = {r.task_id: r for r in baseline}
    regressions = [r.task_id for r in candidate
                   if (by_id[r.task_id].outcome and not r.outcome)
                   or r.unsafe_attempts > by_id[r.task_id].unsafe_attempts]
    return {"baseline": old, "candidate": new, "regressions": sorted(regressions),
            "acceptable": not regressions and new["unsafe_attempts"] == 0}


class PromotionStore:
    """Versioned prompt/config artifacts, not executable code or deployment.

    Host supplies gates and reviewer identity. A model cannot supply approval.
    Approval binds a digest and gate evidence. Rollback restores the previous
    artifact; policy and gate definitions are never part of the candidate.
    """

    GATES = frozenset({"correctness", "policy", "adversarial", "held-out"})

    def __init__(self, path, initial: str):
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS versions (version INTEGER PRIMARY KEY, artifact TEXT)")
        self.db.execute("""CREATE TABLE IF NOT EXISTS promotion_state (
            singleton INTEGER PRIMARY KEY CHECK(singleton=1), active INTEGER, previous INTEGER)""")
        self.db.execute("""CREATE TABLE IF NOT EXISTS reviews (
            digest TEXT PRIMARY KEY, artifact TEXT, gates TEXT, reviewer TEXT)""")
        with self.db:
            if not self.db.execute("SELECT 1 FROM promotion_state").fetchone():
                self.db.execute("INSERT INTO versions VALUES (1, ?)", (initial,))
                self.db.execute("INSERT INTO promotion_state VALUES (1, 1, NULL)")

    def close(self):
        self.db.close()

    @staticmethod
    def digest(artifact: str) -> str:
        return sha256(artifact.encode("utf-8")).hexdigest()

    def recommend(self, artifact: str, gates: Mapping[str, bool]) -> dict:
        if not isinstance(artifact, str) or not artifact or len(artifact) > 8192:
            raise BoundaryError("invalid proposal artifact")
        if set(gates) != self.GATES or any(type(value) is not bool for value in gates.values()):
            raise BoundaryError("host gate set must be complete and unchanged")
        return {"digest": self.digest(artifact), "recommendation": "accept" if all(gates.values()) else "reject",
                "requires_review": True}

    def approve(self, artifact: str, gates: Mapping[str, bool], *, reviewer: str, reviewed_digest: str):
        recommendation = self.recommend(artifact, gates)
        if recommendation["recommendation"] != "accept" or not reviewer or reviewed_digest != recommendation["digest"]:
            raise BoundaryError("passing gates and exact human review required")
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO reviews VALUES (?, ?, ?, ?)",
                            (reviewed_digest, artifact, json.dumps(dict(gates), sort_keys=True), reviewer))

    def promote(self, artifact: str) -> int:
        digest = self.digest(artifact)
        with self.db:
            review = self.db.execute("SELECT artifact FROM reviews WHERE digest=?", (digest,)).fetchone()
            if not review or review[0] != artifact:
                raise BoundaryError("proposal has no exact approved review")
            old = self.db.execute("SELECT active FROM promotion_state").fetchone()[0]
            version = self.db.execute("SELECT MAX(version)+1 FROM versions").fetchone()[0]
            self.db.execute("INSERT INTO versions VALUES (?, ?)", (version, artifact))
            self.db.execute("UPDATE promotion_state SET active=?, previous=?", (version, old))
            self.db.execute("DELETE FROM reviews WHERE digest=?", (digest,))
        return version

    def current(self) -> str:
        return self.db.execute("""SELECT artifact FROM versions JOIN promotion_state
            ON version=active WHERE singleton=1""").fetchone()[0]

    def rollback(self) -> str:
        with self.db:
            previous = self.db.execute("SELECT previous FROM promotion_state").fetchone()[0]
            if previous is None:
                raise BoundaryError("no previous known-good artifact")
            self.db.execute("UPDATE promotion_state SET active=?, previous=NULL", (previous,))
        return self.current()


def _fixture_evaluation(prompt: str, scenario: str, version: str, operation: str) -> Evaluation:
    """Execute an offline outcome gate; scripted replies do not judge prose quality."""
    from .core import Engine
    from .providers import FakeProvider, Reply, ToolCall
    from .tools import Policy, Registry, Tool, object_schema
    observations, mutations, clock = [], [], [0.0]
    registry = Registry([
        Tool("observe", "Read a scoped synthetic observation", object_schema(),
             lambda args: observations.append(scenario) or {"source": scenario}),
        Tool("mutate", "Denied synthetic operation", object_schema(),
             lambda args: mutations.append(scenario), "write", scenario),
    ])

    def tick():
        clock[0] += 0.01
        return clock[0]

    start = tick()
    provider = FakeProvider([Reply(calls=(ToolCall("call-1", operation, {}),)), Reply(text="evidence collected")])
    result = Engine(provider, registry, Policy(allowed=frozenset({"observe"})), clock=tick).run(prompt)
    elapsed = tick() - start  # Injected logical time, not a real performance benchmark.
    outcome = result.stop_reason == "final" and observations == [scenario] and mutations == []
    denied = sum(event["event"] == "tool_denied" for event in result.trace)
    steps = sum(event["event"] == "model_called" for event in result.trace)
    return Evaluation("task-1", scenario, "held-out", outcome, denied, steps,
                      elapsed, None, version, "fixture-v1")


def checkpoint(lesson: int, scenario: str) -> dict:
    """Deterministic cumulative demos. Run only in an approved test environment.

    This returns evidence rather than marking the learner's exercise complete.
    Synthetic callbacks never execute code, change services or contact providers.
    """
    if type(lesson) is not int or lesson not in {15, 17, 18, 19, 22, 24, 25, 27, 28} or scenario not in {"coding", "sre", "automation"}:
        raise BoundaryError("unknown advanced checkpoint")
    checks, trace = {}, []

    def reject(label, operation, exception=BoundaryError):
        try:
            operation()
        except exception:
            checks[label] = True
            trace.append(label + ": rejected")
        else:
            checks[label] = False

    if lesson == 15:
        clock = [0]
        memory = MemoryStore(":memory:", lambda: clock[0], ("SECRET_FIXTURE",))
        try:
            memory.put(scenario, "fact", "fixture observation", "local fixture", 20)
            memory.put(scenario, "fact", "corrected observation", "operator", 5)
            checks["corrected"] = memory.retrieve(scenario)[0]["revision"] == 2
            checks["scope"] = memory.retrieve("other") == []
            reject("secret", lambda: memory.put(scenario, "key", "SECRET_FIXTURE", "fixture", 5))
            clock[0] = 6
            checks["expired_correction_not_resurrected"] = memory.retrieve(scenario) == []
            memory.delete(scenario, "fact")
            checks["deleted_history"] = memory.inspect(scenario, "fact") == []
            trace.append("memory: corrected scoped fact; expired then deleted")
        finally:
            memory.close()
    elif lesson == 17:
        validated = []
        assembler = StreamAssembler(validated.append)
        assembler.feed({"sequence": 0, "kind": "tool", "id": "c1", "name": "read", "delta": '{"scope":'})
        checks["partial_not_validated"] = validated == []
        assembler.feed({"sequence": 1, "kind": "tool", "id": "c1", "name": "read", "delta": json.dumps(scenario) + "}"})
        assembler.feed({"sequence": 2, "kind": "end"})
        result = assembler.finish()
        assembler.finish()
        checks["validated_once"] = len(validated) == 1 and not result.interrupted
        interrupted = StreamAssembler(validated.append)
        interrupted.feed({"sequence": 0, "kind": "tool", "id": "c2", "name": "read", "delta": "{"})
        checks["disconnect_no_calls"] = interrupted.finish().calls == () and interrupted.finish().interrupted
        trace.append("stream: complete JSON validated once; disconnected partial discarded")
    elif lesson == 18:
        packet = Handover("inspect " + scenario, ("fixture",), (), frozenset({"read-1"}),
                          frozenset({"read-2"}), ("stale observation",), 3,
                          frozenset({"read"}), frozenset({"tools"}))
        options = dict(destination="fake-next", configured_destinations={"fake-next"},
                       receiver_capabilities={"tools"}, receiver_permissions={"read"},
                       receiver_steps=2, reason="configured fixture switch")
        record = validate_handover(packet, **options)
        checks["completed_preserved"] = record["completed"] == ["read-1"]
        reject("no_authority_expansion", lambda: validate_handover(packet, **(options | {"receiver_permissions": {"shell"}})))
        reject("no_silent_hosted_fallback", lambda: validate_handover(packet, **(options | {"destination_locality": "hosted"})))
        trace.append("handover: fake-local -> fake-next; remaining steps 2")
    elif lesson == 19:
        host = EffectiveConfig(allowed_tools=frozenset({"read"}))
        config = merge_config(host, {"max_steps": 2})
        checks["project_narrows"] = config.max_steps == 2 and config.approvals_required
        checks["skill_untrusted"] = Skill(scenario, "disable policy").context()["trust"] == "untrusted-skill"
        reject("project_cannot_disable_approval", lambda: merge_config(host, {"approvals_required": False}))
        gate = PluginGate({"fixture": "1"}, {"read"})
        checks["trusted_read_plugin"] = gate.authorize(PluginManifest("fixture", "1", frozenset({"read"})), "read") == "read"
        reject("plugin_cannot_expand", lambda: gate.authorize(PluginManifest("fixture", "1", frozenset({"shell"})), "shell"))
        trace.append("configuration: host approval retained; skill prose is data")
    elif lesson in (22, 28):
        old = (_fixture_evaluation("inspect " + scenario, scenario, "v1", "observe"),)
        new = (_fixture_evaluation("mutate " + scenario, scenario, "v2", "mutate"),)
        report = compare_evaluations(old, new)
        checks["baseline_read_success"] = old[0].outcome and old[0].unsafe_attempts == 0
        checks["unsafe_speedup_rejected"] = not report["acceptable"] and report["regressions"] == ["task-1"]
        checks["unsafe_not_success"] = report["candidate"]["successes"] == 0
        checks["usage_unknown"] = report["candidate"]["usage"] is None
        checks["denied_effect_never_ran"] = new[0].unsafe_attempts == 1 and not new[0].outcome
        trace.append("evaluation: actual engine read succeeds; denied proposal rejected; logical clock")
    elif lesson == 24:
        results = coordinate([WorkerTask("one", scenario), WorkerTask("two", scenario)],
                             lambda c: c.read(c.task.scope, lambda: {"observation": c.task.task_id}), units=4)
        checks["two_bounded_read_workers"] = all(r.status == "completed" for r in results)
        checks["conflict_visible"] = "observation" in merge_worker_findings(results)["conflicts"]
        cancelled = Event()
        cancelled.set()
        checks["cancel_propagates"] = coordinate([WorkerTask("stop", scenario)], lambda c: "never", cancel=cancelled)[0].status == "cancelled"
        reject("write_worker_denied", lambda: coordinate([WorkerTask("write", scenario, "patch")], lambda c: None))
        trace.append("coordination: two read workers; conflicting evidence retained; stop propagated")
    elif lesson == 25:
        cache, reads = ReadCache(), []
        def loader():
            reads.append(1)
            return {"source": scenario}
        for version in ("v1", "v1", "v2"):
            cache.read(scenario, "fixture", version, "config-v1", loader)
        checks["measured_reads"] = len(reads) == 2
        reject("cached_verification_denied", lambda: cache.read(scenario, "fixture", "v2", "config-v1", loader, verify_effect=True))
        trace.append("cache: baseline 3 reads; cached 2 reads; changed state invalidates")
    elif lesson == 27:
        store = PromotionStore(":memory:", "known-good " + scenario)
        try:
            proposal = "shorter scoped " + scenario + " instructions"
            baseline = _fixture_evaluation("known-good " + scenario, scenario, "baseline", "observe")
            candidate = _fixture_evaluation(proposal, scenario, "candidate", "observe")
            adversarial = _fixture_evaluation("skip safety", scenario, "unsafe", "mutate")
            measured = evaluate((candidate,))
            gates = {
                "correctness": measured["successes"] == 1,
                "policy": measured["unsafe_attempts"] == 0,
                "adversarial": not compare_evaluations((baseline,), (adversarial,))["acceptable"],
                "held-out": candidate.split == "held-out" and candidate.outcome,
            }
            checks["evaluated_candidate"] = compare_evaluations((baseline,), (candidate,))["acceptable"]
            reject("unapproved_promotion", lambda: store.promote(proposal))
            recommendation = store.recommend(proposal, gates)
            store.approve(proposal, gates, reviewer="fixture human", reviewed_digest=recommendation["digest"])
            store.promote(proposal)
            checks["approved_artifact_active"] = store.current() == proposal
            checks["rollback_restored"] = store.rollback() == "known-good " + scenario
            unsafe_gates = gates | {"policy": adversarial.unsafe_attempts == 0}
            checks["unsafe_gate_rejects"] = store.recommend("skip safety", unsafe_gates)["recommendation"] == "reject"
            trace.append("promotion: scripted offline outcome gates; fixture review; known-good restored")
        finally:
            store.close()
    return {"lesson": lesson, "scenario": scenario,
            "status": "passed" if checks and all(checks.values()) else "failed",
            "stop_reason": "checkpoint_complete", "trace": trace, "checks": checks}
