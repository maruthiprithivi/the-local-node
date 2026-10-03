"""Offline acceptance for lessons 13, 14, 26: all time/effects are synthetic."""
from datetime import datetime, timedelta, timezone
import sqlite3

import pytest

from course_harness.persistence import DurableStore, StateError
from course_harness.resident import QueueFull, ResidentQueue, ResidentWorker, SafeRetry, Schedule


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


@pytest.fixture
def state(tmp_path):
    clock = Clock()
    store = DurableStore(tmp_path / "state.sqlite", clock=clock)
    yield store, clock
    store.close()


def test_completed_action_is_receipt_not_reexecution(state):
    store, _ = state
    store.create_run("coding", {"actions": 2})
    store.request_action("coding", "edit-1", {"path": "toy.txt"})
    scope = {"path": "toy.txt", "operation": "write"}
    store.approve_action("edit-1", scope)
    store.start_action("edit-1", scope)
    store.complete_action("edit-1", {"changed": True})
    assert store.recover() == []
    assert store.action("edit-1")["result"] == {"changed": True}
    with pytest.raises(StateError):
        store.start_action("edit-1", scope)


def test_crash_requires_observation_and_budget_approval_survive(tmp_path):
    path = tmp_path / "state.sqlite"
    store = DurableStore(path)
    store.create_run("sre", {"actions": 2})
    store.consume("sre", "actions")
    store.request_action("sre", "restart", {"service": "toy"})
    scope = {"service": "toy"}
    store.approve_action("restart", scope)
    with pytest.raises(StateError):
        store.start_action("restart", {"service": "production"})
    store.start_action("restart", scope)
    effects = ["toy restarted"]  # effect occurred, completion receipt was lost
    store.close()
    recovered = DurableStore(path)
    try:
        assert recovered.recover() == ["restart"]
        assert recovered.run("sre")["budgets"] == {"actions": 1}
        assert recovered.action("restart")["scope"] == scope
        with pytest.raises(StateError):
            recovered.start_action("restart", scope)
        with pytest.raises(StateError):
            recovered.reconcile("restart", effects, observed=False)
        recovered.reconcile("restart", effects, observed=True)
        assert effects == ["toy restarted"]
        assert recovered.action("restart")["status"] == "completed"
    finally:
        recovered.close()


def test_incompatible_state_version_rejected(tmp_path):
    path = tmp_path / "future.sqlite"
    db = sqlite3.connect(path)
    db.execute("PRAGMA user_version=99")
    db.close()
    with pytest.raises(StateError, match="version"):
        DurableStore(path)


def test_cancelled_run_cannot_start_approved_action(state):
    store, _ = state
    store.create_run("automation", {"actions": 1})
    store.request_action("automation", "label", {"record": "fixture"})
    store.approve_action("label", {"record": "fixture"})
    store.cancel_run("automation")
    with pytest.raises(StateError):
        store.start_action("label", {"record": "fixture"})
    with pytest.raises(StateError):
        store.consume("automation", "actions")


@pytest.mark.parametrize("scenario", ["coding", "sre", "automation"])
def test_three_paths_share_queue_and_deduplication(state, scenario):
    store, _ = state
    queue = ResidentQueue(store, capacity=1)
    task_id = queue.enqueue(scenario + ":1", {"scenario": scenario})
    assert queue.enqueue(scenario + ":1", {"scenario": scenario}) == task_id
    with pytest.raises(QueueFull):
        queue.enqueue(scenario + ":2", {"scenario": scenario})
    receipts = []
    worker = ResidentWorker(queue, lambda task: receipts.append(task["payload"]["scenario"]) or {"dry_run": True})
    assert worker.tick()
    assert not worker.tick()
    assert receipts == [scenario]
    assert queue.task(task_id)["status"] == "completed"
    assert queue.enqueue(scenario + ":1", {}) == task_id


def test_single_claim_lease_heartbeat_and_uncertain_recovery(state):
    store, clock = state
    queue = ResidentQueue(store, lease_seconds=5)
    first = queue.enqueue("a", {})
    second = queue.enqueue("b", {})
    assert queue.claim("one")["id"] == first
    assert queue.claim("two") is None
    clock.advance(4)
    queue.heartbeat(first, "one")
    clock.advance(2)
    assert queue.recover() == []
    clock.advance(4)
    assert queue.health()["stale_workers"] == [first]
    assert queue.recover() == [first]
    with pytest.raises(StateError):
        queue.complete(first, "one", {})
    assert queue.task(first)["status"] == "uncertain"
    assert queue.claim("two")["id"] == second
    queue.reconcile(first, {"observed": "already done"}, observed=True)
    assert queue.task(first)["status"] == "completed"


def test_retry_backoff_and_dead_letter_are_bounded(state):
    store, clock = state
    queue = ResidentQueue(store, max_attempts=2)
    task_id = queue.enqueue("outage", {})

    def outage(task):
        raise SafeRetry("no effect occurred")

    worker = ResidentWorker(queue, outage)
    assert worker.tick()
    assert not worker.tick()  # delayed, no retry storm
    clock.advance(1)
    assert worker.tick()
    assert queue.task(task_id)["status"] == "dead_letter"
    assert queue.task(task_id)["attempts"] == 2


def test_unknown_failure_never_blindly_retries(state):
    store, _ = state
    queue = ResidentQueue(store)
    task_id = queue.enqueue("ambiguous", {})
    effects = []

    def interrupted(task):
        effects.append("mutation")
        raise RuntimeError("receipt lost")

    worker = ResidentWorker(queue, interrupted)
    assert worker.tick()
    assert not worker.tick()
    assert queue.task(task_id)["status"] == "uncertain"
    assert effects == ["mutation"]


def test_drain_pause_cancel_and_persistent_human_stop(tmp_path):
    path = tmp_path / "resident.sqlite"
    store = DurableStore(path)
    queue = ResidentQueue(store)
    first, second = queue.enqueue("a", {}), queue.enqueue("b", {})
    queue.pause()
    assert queue.claim("worker") is None
    queue.resume()
    queue.cancel(second)
    queue.drain()
    with pytest.raises(StateError, match="admission"):
        queue.enqueue("c", {})
    assert queue.claim("worker")["id"] == first
    queue.complete(first, "worker", {"ok": True})
    assert queue.claim("worker") is None
    queue.stop()
    store.close()
    restarted = DurableStore(path)
    try:
        queue = ResidentQueue(restarted)
        assert queue.health()["human_stop"]
        with pytest.raises(StateError, match="explicit"):
            queue.resume()
        assert queue.claim("worker") is None
        queue.resume(clear_human_stop=True)
        assert queue.enqueue("c", {}) > second
    finally:
        restarted.close()


def test_stop_blocks_new_action_but_records_existing_receipt(state):
    store, _ = state
    queue = ResidentQueue(store)
    task_id = queue.enqueue("one", {})
    queue.claim("worker")
    queue.stop()
    with pytest.raises(StateError, match="stop"):
        queue.heartbeat(task_id, "worker")
    queue.complete(task_id, "worker", {"effect": "already occurred"})
    assert queue.task(task_id)["status"] == "completed"


def test_schedule_requires_timezone_and_policies(state):
    store, _ = state
    queue = ResidentQueue(store)
    anchor = datetime(2026, 1, 1, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="aware"):
        Schedule("bad", anchor.replace(tzinfo=None), 60, "UTC")
    schedule = Schedule("daily", anchor, 60, "UTC", missed="latest", overlap="skip")
    first = schedule.admit(queue, anchor + timedelta(minutes=5), {"scenario": "automation"})
    assert first is not None
    assert len(queue.inspect()) == 1  # latest catch-up, no backlog burst
    assert schedule.admit(queue, anchor + timedelta(minutes=5), {}) is None
    assert schedule.admit(queue, anchor + timedelta(minutes=6), {}) is None  # overlap skipped
    assert queue.task(first)["payload"]["timezone"] == "UTC"


def test_schedule_skip_missed_queue_overlap_and_backpressure(state):
    store, _ = state
    queue = ResidentQueue(store, capacity=1)
    anchor = datetime(2026, 1, 1, tzinfo=timezone.utc)
    skipped = Schedule("skip", anchor, 60, "UTC", missed="skip")
    assert skipped.admit(queue, anchor + timedelta(minutes=5), {}) is None
    queued = Schedule("queue", anchor, 60, "UTC", overlap="queue")
    assert queued.admit(queue, anchor, {}) is not None
    with pytest.raises(QueueFull):
        queued.admit(queue, anchor + timedelta(minutes=1), {})
    # Failed admission must not advance schedule bookkeeping.
    assert store.db.execute("SELECT last_due FROM schedules WHERE name='queue'").fetchone()[0] == anchor.timestamp()


def test_schedule_elapsed_interval_across_dst(state):
    from zoneinfo import ZoneInfo
    store, _ = state
    queue = ResidentQueue(store)
    anchor = datetime(2026, 3, 7, 9, tzinfo=ZoneInfo("America/New_York"))
    schedule = Schedule("dst", anchor, 86400, "America/New_York", overlap="queue")
    task_id = schedule.admit(queue, datetime(2026, 3, 8, 14, tzinfo=timezone.utc), {})
    assert queue.task(task_id)["payload"]["scheduled_at"] == "2026-03-08T14:00:00+00:00"


@pytest.mark.parametrize("scenario", ["coding", "sre", "automation"])
def test_lesson_13_checkpoint(scenario):
    from course_harness.resident import checkpoint
    assert all(checkpoint(13, scenario)["checks"].values())


@pytest.mark.parametrize("scenario", ["coding", "sre", "automation"])
def test_lesson_14_checkpoint(scenario):
    from course_harness.resident import checkpoint
    assert all(checkpoint(14, scenario)["checks"].values())


@pytest.mark.parametrize("scenario", ["coding", "sre", "automation"])
def test_lesson_26_checkpoint(scenario):
    from course_harness.resident import checkpoint
    assert all(checkpoint(26, scenario)["checks"].values())


def test_restart_budget_and_uncertainty_stop_watchdog(state):
    store, clock = state
    queue = ResidentQueue(store, lease_seconds=1)
    task_id = queue.enqueue("a", {})
    queue.claim("worker")
    clock.advance(2)
    queue.recover()
    assert not queue.restart_permitted()
    queue.reconcile(task_id, {"observed": True}, observed=True)
    assert queue.restart_permitted(limit=1)
    assert not queue.restart_permitted(limit=1)


def test_nonfinite_budget_cannot_bypass_limits(state):
    store, _ = state
    with pytest.raises(StateError):
        store.create_run("bad", {"actions": float("nan")})
    store.create_run("bounded", {"actions": 1})
    with pytest.raises(StateError):
        store.consume("bounded", "actions", float("nan"))
    assert store.run("bounded")["budgets"] == {"actions": 1}


@pytest.mark.parametrize("scenario", ["coding", "sre", "automation"])
def test_resident_task_uses_shared_engine_without_effects(state, scenario):
    from course_harness.resident import execute_fixture_task
    store, _ = state
    queue = ResidentQueue(store)
    task_id = queue.enqueue("fixture", {"scenario": scenario})
    assert ResidentWorker(queue, execute_fixture_task).tick()
    receipt = queue.task(task_id)["result"]
    events = [event["event"] for event in receipt["trace"]]
    assert "model_called" in events
    assert "tool_completed" in events
    assert receipt["stop_reason"] == "final"
    assert receipt["no_effects"]


def test_terminal_reject_dead_letters_without_retry_or_uncertainty(state):
    store, _ = state
    queue = ResidentQueue(store)
    task_id = queue.enqueue("invalid-before-effect", {})
    queue.claim("worker")
    queue.reject(task_id, "worker", reason="scope_denied_before_execution")
    task = queue.task(task_id)
    assert task["status"] == "dead_letter"
    assert task["owner"] is None and task["lease_until"] is None
    assert task["attempts"] == 1
    assert task["result"]["effects"] == "not_started"
    assert queue.claim("worker") is None
    assert store.events()[-1]["data"]["reason"] == "scope_denied_before_execution"


def test_terminal_reject_requires_valid_owned_lease(state):
    store, clock = state
    queue = ResidentQueue(store, lease_seconds=1)
    task_id = queue.enqueue("owned", {})
    queue.claim("worker")
    with pytest.raises(StateError, match="lease"):
        queue.reject(task_id, "other-worker")
    assert queue.task(task_id)["status"] == "running"
    clock.advance(1)
    with pytest.raises(StateError, match="lease"):
        queue.reject(task_id, "worker")
    assert queue.recover() == [task_id]
    assert queue.task(task_id)["status"] == "uncertain"
