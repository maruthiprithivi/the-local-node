"""Deterministic single-worker resident primitives; no daemon or real services.

Wall time is persisted for leases/schedules so restart retains their meaning.
Real process timeout enforcement belongs to the authorized executor and uses a
monotonic clock. This cooperative worker cannot kill a hung callback.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable
from zoneinfo import ZoneInfo

from .persistence import DurableStore, StateError


class QueueFull(StateError):
    pass


class SafeRetry(Exception):
    """A callback declares it failed before effects, or is safely idempotent."""


class ResidentQueue:
    ACTIVE = ("queued", "running", "uncertain")

    def __init__(self, store: DurableStore, *, capacity: int = 8,
                 lease_seconds: float = 30, max_attempts: int = 3):
        if capacity < 1 or lease_seconds <= 0 or max_attempts < 1:
            raise ValueError("queue bounds must be positive")
        self.store, self.capacity = store, capacity
        self.lease_seconds, self.max_attempts = lease_seconds, max_attempts

    def task(self, task_id: int) -> dict:
        row = self.store.db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        if row is None:
            raise StateError("unknown task")
        return dict(row) | {"payload": json.loads(row["payload"]),
                            "result": json.loads(row["result"]) if row["result"] else None}

    def inspect(self) -> list[dict]:
        return [self.task(row[0]) for row in self.store.db.execute("SELECT id FROM tasks ORDER BY id")]

    def enqueue(self, key: str, payload: dict, *, ready_at: float | None = None) -> int:
        """Reject overflow. Deduplicate forever within this database; no pruning."""
        if not key or len(key) > 256 or len(json.dumps(payload)) > 16384:
            raise StateError("invalid event key or oversized payload")
        with self.store.transaction():
            existing = self.store.db.execute("SELECT id FROM tasks WHERE dedup_key=?", (key,)).fetchone()
            if existing:
                return existing[0]
            if any(self.store.control(name, False) for name in ("human_stop", "paused", "draining")):
                raise StateError("admission stopped")
            count = self.store.db.execute(
                "SELECT count(*) FROM tasks WHERE status IN ('queued','running','uncertain')").fetchone()[0]
            if count >= self.capacity:
                raise QueueFull("bounded queue full; event rejected")
            cursor = self.store.db.execute(
                "INSERT INTO tasks(dedup_key,payload,status,ready_at) VALUES(?,?,'queued',?)",
                (key, json.dumps(payload), self.store.clock() if ready_at is None else ready_at))
            self.store.event("task.admitted", str(cursor.lastrowid), {"key": key})
            return cursor.lastrowid

    def claim(self, worker: str) -> dict | None:
        with self.store.transaction():
            if self.store.control("human_stop", False) or self.store.control("paused", False):
                return None
            # One active worker is supported. Expiration needs explicit recovery.
            if self.store.db.execute("SELECT 1 FROM tasks WHERE status='running'").fetchone():
                return None
            row = self.store.db.execute(
                "SELECT id FROM tasks WHERE status='queued' AND cancelled=0 AND ready_at<=? ORDER BY id LIMIT 1",
                (self.store.clock(),)).fetchone()
            if row is None:
                return None
            self.store.db.execute(
                "UPDATE tasks SET status='running',attempts=attempts+1,owner=?,lease_until=? WHERE id=?",
                (worker, self.store.clock() + self.lease_seconds, row[0]))
            self.store.event("task.claimed", str(row[0]), {"worker": worker})
            return self.task(row[0])

    def _owned(self, task_id: int, worker: str) -> dict:
        task = self.task(task_id)
        if (task["status"] != "running" or task["owner"] != worker
                or task["lease_until"] <= self.store.clock()):
            raise StateError("worker has no valid task lease")
        return task

    def heartbeat(self, task_id: int, worker: str) -> None:
        with self.store.transaction():
            task = self._owned(task_id, worker)
            if task["cancelled"] or self.store.control("human_stop", False):
                raise StateError("worker must stop")
            self.store.db.execute("UPDATE tasks SET lease_until=? WHERE id=?",
                                  (self.store.clock() + self.lease_seconds, task_id))
            self.store.set_control("last_heartbeat", self.store.clock())

    def complete(self, task_id: int, worker: str, result: Any) -> None:
        with self.store.transaction():
            self._owned(task_id, worker)
            # A stop cannot undo an effect. Save its receipt even if stop arrived.
            self.store.db.execute("UPDATE tasks SET status='completed',result=?,owner=NULL,lease_until=NULL WHERE id=?",
                                  (json.dumps(result), task_id))
            self.store.event("task.completed", str(task_id), result)

    def fail(self, task_id: int, worker: str, *, safe_to_retry: bool = False,
             delay: float = 1) -> None:
        if delay < 0:
            raise ValueError("retry delay must be nonnegative")
        with self.store.transaction():
            task = self._owned(task_id, worker)
            status = "uncertain"
            if safe_to_retry:
                status = "queued" if task["attempts"] < self.max_attempts and not task["cancelled"] else "dead_letter"
            self.store.db.execute("UPDATE tasks SET status=?,ready_at=?,owner=NULL,lease_until=NULL WHERE id=?",
                                  (status, self.store.clock() + delay, task_id))
            self.store.event("task." + status, str(task_id))

    def reject(self, task_id: int, worker: str, reason: str = "terminal") -> None:
        """Dead-letter a terminal failure known to happen before any effect.

        The caller owns that assertion: an arbitrary ValueError or PermissionError
        after an effect must use uncertain failure instead. Expired ownership
        cannot resolve work; explicit recovery/reconciliation handles that case.
        """
        if not isinstance(reason, str) or not reason or len(reason) > 256:
            raise ValueError("terminal reason must be a bounded nonempty string")
        with self.store.transaction():
            self._owned(task_id, worker)
            self.store.db.execute(
                "UPDATE tasks SET status='dead_letter',owner=NULL,lease_until=NULL,result=? WHERE id=?",
                (json.dumps({"terminal_reason": reason, "effects": "not_started"}), task_id))
            self.store.event("task.dead_letter", str(task_id), {"reason": reason, "effects": "not_started"})

    def recover(self) -> list[int]:
        """Expired claims become uncertain, never automatically eligible for retry."""
        with self.store.transaction():
            ids = [row[0] for row in self.store.db.execute(
                "SELECT id FROM tasks WHERE status='running' AND lease_until<=?", (self.store.clock(),))]
            for task_id in ids:
                self.store.db.execute("UPDATE tasks SET status='uncertain',owner=NULL,lease_until=NULL WHERE id=?", (task_id,))
                self.store.event("task.uncertain", str(task_id))
            return ids

    def reconcile(self, task_id: int, result: Any, *, observed: bool) -> None:
        with self.store.transaction():
            if not observed or self.task(task_id)["status"] != "uncertain":
                raise StateError("observation required for uncertain task")
            self.store.db.execute("UPDATE tasks SET status='completed',result=? WHERE id=?", (json.dumps(result), task_id))
            self.store.event("task.reconciled", str(task_id), result)

    def cancel(self, task_id: int) -> None:
        with self.store.transaction():
            task = self.task(task_id)
            status = "cancelled" if task["status"] == "queued" else task["status"]
            self.store.db.execute("UPDATE tasks SET cancelled=1,status=? WHERE id=?", (status, task_id))
            self.store.event("task.cancelled", str(task_id))

    def pause(self) -> None:
        with self.store.transaction():
            self.store.set_control("paused", True)
            self.store.event("resident.paused", "resident")

    def drain(self) -> None:
        """Stop admission but keep claiming accepted work until empty."""
        with self.store.transaction():
            self.store.set_control("draining", True)
            self.store.event("resident.draining", "resident")

    def stop(self) -> None:
        with self.store.transaction():
            self.store.set_control("human_stop", True)
            self.store.event("resident.human_stop", "resident")

    def resume(self, *, clear_human_stop: bool = False) -> None:
        """Only an explicit operator request clears the persistent human stop."""
        with self.store.transaction():
            if self.store.control("human_stop", False) and not clear_human_stop:
                raise StateError("human stop requires explicit operator reset")
            for name in ("paused", "draining"):
                self.store.set_control(name, False)
            if clear_human_stop:
                self.store.set_control("human_stop", False)
            self.store.event("resident.resumed", "resident")

    def health(self) -> dict:
        tasks = self.inspect()
        stale = [task["id"] for task in tasks if task["status"] == "running" and task["lease_until"] <= self.store.clock()]
        return {"human_stop": self.store.control("human_stop", False),
                "paused": self.store.control("paused", False), "draining": self.store.control("draining", False),
                "stale_workers": stale, "uncertain": [task["id"] for task in tasks if task["status"] == "uncertain"],
                "pending": sum(task["status"] in self.ACTIVE for task in tasks),
                "last_heartbeat": self.store.control("last_heartbeat")}

    def restart_permitted(self, *, limit: int = 2) -> bool:
        """Authorize a bounded supervisor restart, not a subprocess launch.

        Stale or ambiguous claims require recovery/observation first. The restart
        count is durable; reopening the service does not replenish this budget.
        """
        with self.store.transaction():
            health = self.health()
            count = self.store.control("restarts", 0)
            running = any(task["status"] == "running" for task in self.inspect())
            if (limit < 1 or count >= limit or health["human_stop"] or health["paused"]
                    or health["draining"] or health["uncertain"] or running):
                return False
            self.store.set_control("restarts", count + 1)
            self.store.event("resident.restart_permitted", "resident", {"count": count + 1})
            return True


class ResidentWorker:
    def __init__(self, queue: ResidentQueue, callback: Callable[[dict], Any], *, worker: str = "worker-1"):
        self.queue, self.callback, self.worker = queue, callback, worker

    def tick(self) -> bool:
        """One bounded unit; callback must enforce tool gates and cooperate with stop."""
        task = self.queue.claim(self.worker)
        if task is None:
            return False
        try:
            result = self.callback(task)
        except SafeRetry:
            self.queue.fail(task["id"], self.worker, safe_to_retry=True, delay=2 ** (task["attempts"] - 1))
        except Exception:
            self.queue.fail(task["id"], self.worker)
        else:
            self.queue.complete(task["id"], self.worker, result)
        return True


@dataclass(frozen=True)
class Schedule:
    """UTC-elapsed interval, with explicit timezone for presentation.

    This is not a cron expression or a '9am daily' civil-time scheduler. Across
    DST the elapsed interval stays fixed; local display time can change.
    Missed policy is 'skip' or 'latest' (at most one catch-up). Overlap is
    'skip' or 'queue'; all admission uses the same capacity and duplicate gate.
    """
    name: str
    anchor: datetime
    interval_seconds: int
    timezone_name: str
    missed: str = "latest"
    overlap: str = "skip"

    def __post_init__(self):
        ZoneInfo(self.timezone_name)
        if self.anchor.tzinfo is None or self.interval_seconds <= 0:
            raise ValueError("schedule requires aware anchor and positive interval")
        if self.missed not in ("skip", "latest") or self.overlap not in ("skip", "queue"):
            raise ValueError("unknown scheduling policy")

    def admit(self, queue: ResidentQueue, now: datetime, payload: dict) -> int | None:
        if now.tzinfo is None:
            raise ValueError("schedule now must be timezone aware")
        epoch, anchor = now.timestamp(), self.anchor.timestamp()
        if epoch < anchor:
            return None
        slot = int((epoch - anchor) // self.interval_seconds)
        due = anchor + slot * self.interval_seconds
        row = queue.store.db.execute("SELECT last_due FROM schedules WHERE name=?", (self.name,)).fetchone()
        previous = row[0] if row else anchor - self.interval_seconds
        if due <= previous:
            return None
        missed = due - previous > self.interval_seconds
        overlapping = any(task["payload"].get("schedule") == self.name and task["status"] in queue.ACTIVE
                          for task in queue.inspect())
        admitted = None
        if not (missed and self.missed == "skip") and not (overlapping and self.overlap == "skip"):
            admitted = queue.enqueue(f"schedule:{self.name}:{due}", payload | {
                "schedule": self.name, "scheduled_at": datetime.fromtimestamp(due, timezone.utc).isoformat(),
                "timezone": self.timezone_name})
        # Advance only after successful admission (or an explicit skip).
        queue.store.db.execute("INSERT INTO schedules VALUES(?,?) ON CONFLICT(name) DO UPDATE SET last_due=excluded.last_due",
                               (self.name, due))
        return admitted


def execute_fixture_task(task: dict) -> dict:
    """Run one resident task through the same bounded, read-only core engine."""
    from .core import Engine
    from .providers import FakeProvider, Reply, ToolCall
    from .tools import FixtureWorld, Policy, scenario_tools

    scenario = task["payload"]["scenario"]
    if scenario not in ("coding", "sre", "automation"):
        raise ValueError("unknown resident scenario")
    world = FixtureWorld()
    name = "read_file" if scenario == "coding" else "observe_health"
    arguments = {"path": "calculator.py"} if scenario == "coding" else {}
    provider = FakeProvider([
        Reply(calls=(ToolCall("fixture-read", name, arguments),)),
        Reply(text=f"Observed {scenario} fixture; no changes requested."),
    ])
    policy = Policy(mode="read_only", allowed=frozenset({name}), run_id=f"resident-{task['id']}")
    run = Engine(provider, scenario_tools(world), policy, clock=lambda: 100.0).run(
        f"Inspect the {scenario} fixture and report evidence before proposing an action.")
    no_effects = not world.restarts and not world.artifacts and not world.originals
    if run.stop_reason != "final" or not no_effects:
        raise StateError("fixture engine did not finish safely")
    return {"scenario": scenario, "dry_run": True, "no_effects": no_effects,
            "stop_reason": run.stop_reason, "trace": run.trace, "usage": run.usage}


def checkpoint(lesson: int, scenario: str) -> dict:
    """Runnable fixture receipts for durable recovery and resident operations."""
    from pathlib import Path
    from tempfile import TemporaryDirectory

    if lesson not in (13, 14, 26) or scenario not in ("coding", "sre", "automation"):
        raise ValueError("resident checkpoint requires lesson 13, 14, or 26 and a known scenario")
    with TemporaryDirectory(prefix="harness-resident-") as directory:
        path = Path(directory) / "state.sqlite"
        now = [1000.0]
        store = DurableStore(path, clock=lambda: now[0])
        checks = {}
        try:
            if lesson == 13:
                store.create_run(scenario, {"actions": 2})
                store.consume(scenario, "actions")
                store.request_action(scenario, "fixture-effect", {"scenario": scenario})
                scope = {"scenario": scenario, "target": "disposable-fixture"}
                store.approve_action("fixture-effect", scope)
                store.start_action("fixture-effect", scope)
                effects = ["fixture effect observed"]
                store.close()
                store = DurableStore(path, clock=lambda: now[0])
                checks["uncertain_after_restart"] = store.recover() == ["fixture-effect"]
                checks["budget_survives"] = store.run(scenario)["budgets"]["actions"] == 1
                checks["approval_survives"] = store.action("fixture-effect")["scope"] == scope
                store.reconcile("fixture-effect", effects, observed=True)
                checks["observed_without_replay"] = (store.action("fixture-effect")["status"] == "completed"
                                                     and effects == ["fixture effect observed"])
            else:
                queue = ResidentQueue(store, capacity=2, lease_seconds=5)
                first = queue.enqueue("fixture:1", {"scenario": scenario})
                checks["duplicate_suppressed"] = queue.enqueue("fixture:1", {}) == first
                second = queue.enqueue("fixture:2", {"scenario": scenario})
                try:
                    queue.enqueue("fixture:overflow", {})
                except QueueFull:
                    checks["backpressure"] = True
                else:
                    checks["backpressure"] = False
                worker = ResidentWorker(queue, execute_fixture_task)
                assert worker.tick()
                receipt = queue.task(first)["result"]
                checks["shared_engine"] = any(event["event"] == "tool_completed" for event in receipt["trace"])
                checks["no_effects"] = receipt["no_effects"]
                queue.claim("crashed-worker")
                now[0] += 6
                checks["expired_lease_uncertain"] = queue.recover() == [second]
                checks["no_blind_replay"] = queue.claim("new-worker") is None
                queue.reconcile(second, {"observed": "fixture unchanged"}, observed=True)
                queue.stop()
                store.close()
                store = DurableStore(path, clock=lambda: now[0])
                queue = ResidentQueue(store, capacity=2, lease_seconds=5)
                checks["human_stop_survives"] = queue.health()["human_stop"] and queue.claim("new-worker") is None
                checks["watchdog_respects_stop"] = not queue.restart_permitted()
                if lesson == 26:
                    queue.resume(clear_human_stop=True)
                    queue.pause()
                    checks["paused_admission"] = queue.claim("new-worker") is None
                    queue.resume()
                    anchor = datetime(2026, 1, 1, tzinfo=timezone.utc)
                    schedule = Schedule("fixture", anchor, 60, "UTC", missed="latest", overlap="skip")
                    from datetime import timedelta
                    scheduled = schedule.admit(queue, anchor + timedelta(minutes=5), {"scenario": scenario})
                    checks["latest_catch_up"] = scheduled is not None
                    checks["overlap_skipped"] = schedule.admit(queue, anchor + timedelta(minutes=6), {}) is None
                    queue.drain()
                    assert ResidentWorker(queue, execute_fixture_task).tick()
                    checks["drained"] = queue.health()["pending"] == 0
                    queue.resume()
                    checks["bounded_restart"] = (queue.restart_permitted(limit=1)
                                                  and not queue.restart_permitted(limit=1))
            if not all(checks.values()):
                raise AssertionError(f"resident checkpoint failed: {checks}")
            trace = store.events()
            if lesson != 13:
                trace += [event for task in queue.inspect() if isinstance(task["result"], dict)
                          for event in task["result"].get("trace", [])]
            return {"lesson": lesson, "scenario": scenario, "status": "completed",
                    "stop_reason": "checkpoint_passed", "trace": trace, "checks": checks}
        finally:
            store.close()
