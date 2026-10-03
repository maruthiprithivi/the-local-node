import pytest

from course_harness.extensions import FrameworkProvider, FrameworkToolBridge, FakeGitHub, MentionReceiver, checkpoint
from course_harness.providers import Reply, ProviderError
from course_harness.persistence import DurableStore
from course_harness.tools import FixtureWorld, Policy, scenario_tools, canonical


def test_lesson_29_no_sdk_nested_policy_cancel_and_budget():
    world = FixtureWorld()
    bridge = FrameworkToolBridge(scenario_tools(world), Policy(allowed=frozenset({"observe_health"})), max_calls=1)
    assert bridge.invoke("restart_service", {"service": "toy-service"}).stop_reason == "denied"
    assert world.restarts == 0
    with pytest.raises(PermissionError):
        bridge.invoke("observe_health", {})
    provider = FrameworkProvider(lambda m, t: Reply("unused"), cancelled=lambda: True)
    with pytest.raises(InterruptedError):
        provider.complete([])


def test_lesson_29_optional_sdk_import_is_inactive_and_absence_clear(monkeypatch):
    import runpy
    import importlib.metadata
    from pathlib import Path
    example = Path(__file__).resolve().parents[2] / "examples/framework/bridge.py"
    namespace = runpy.run_path(str(example))
    with pytest.raises(PermissionError):
        namespace["require_sdk"](enabled=False)
    def absent(name):
        raise importlib.metadata.PackageNotFoundError(name)
    # The helper captured this function in its run_path globals.
    namespace["require_sdk"].__globals__["version"] = absent
    with pytest.raises(RuntimeError, match="absent"):
        namespace["require_sdk"](enabled=True)


@pytest.fixture
def mention():
    store = DurableStore(":memory:", clock=lambda: 100.0)
    client = FakeGitHub()
    receiver = MentionReceiver(store, client, secret=b"fixture-only")
    event = {"repository": client.repo, "comment_id": 1, "revision": 1, "base": client.head, "fork": False, "action": "created"}
    yield receiver, client, event
    store.close()


def send(receiver, event):
    raw = canonical(event).encode()
    return receiver.receive(raw, receiver.sign(raw))


def test_lesson_30_one_logical_task_draft_and_ambiguous_effect(mention):
    receiver, client, event = mention
    admitted = send(receiver, event)
    assert send(receiver, event)["status"] == "duplicate"
    prepared = receiver.prepare_next()
    client.ambiguous_publish = True
    with pytest.raises(TimeoutError):
        receiver.publish(admitted["task_id"], approval_digest=prepared["digest"], approval_expires=101)
    assert receiver.queue.task(admitted["task_id"])["status"] == "uncertain"
    receipt = receiver.reconcile_publication(admitted["task_id"])
    assert receipt["draft"] and not receipt["merged"]
    assert send(receiver, event)["status"] == "duplicate"
    assert len(client.prs) == 1


def test_lesson_30_signature_actor_fork_and_exact_parser(mention):
    receiver, client, event = mention
    with pytest.raises(PermissionError):
        receiver.receive(canonical(event).encode(), "sha256=forged")
    with pytest.raises(PermissionError):
        send(receiver, event | {"fork": True})
    client.comments[1]["actor"] = "bob"
    with pytest.raises(PermissionError):
        send(receiver, event)
    client.comments[1]["actor"] = "alice"
    client.comments[1]["body"] = "x@course-harness fix; rm -rf /"
    with pytest.raises(ValueError):
        send(receiver, event)
    assert receiver.queue.inspect() == []


def test_lesson_30_stale_base_approval_expiry_revoke_cancel(mention):
    receiver, client, event = mention
    with pytest.raises(ValueError):
        send(receiver, event | {"base": "stale"})
    admitted = send(receiver, event)
    prepared = receiver.prepare_next()
    with pytest.raises(PermissionError):
        receiver.publish(admitted["task_id"], approval_digest=prepared["digest"], approval_expires=99)
    with pytest.raises(PermissionError):
        receiver.publish(admitted["task_id"], approval_digest="changed", approval_expires=101)
    client.permissions["alice"] = "read"
    with pytest.raises(PermissionError):
        receiver.publish(admitted["task_id"], approval_digest=prepared["digest"], approval_expires=101)
    client.permissions["alice"] = "write"
    receiver.queue.cancel(admitted["task_id"])
    with pytest.raises(PermissionError):
        receiver.publish(admitted["task_id"], approval_digest=prepared["digest"], approval_expires=101)
    assert not client.prs


def test_lesson_30_edit_invalidates_and_bot_does_not_loop(mention):
    receiver, client, event = mention
    admitted = send(receiver, event)
    client.comments[1]["revision"] = 2
    assert send(receiver, event | {"action": "edited", "revision": 2})["status"] == "invalidated"
    assert receiver.queue.task(admitted["task_id"])["cancelled"]
    client.comments[1]["bot"] = True
    with pytest.raises(PermissionError):
        send(receiver, event | {"revision": 2})


def test_lesson_30_deleted_body_does_not_prevent_invalidation(mention):
    receiver, client, event = mention
    admitted = send(receiver, event)
    client.comments[1]["deleted"] = True
    assert send(receiver, event | {"action": "deleted"})["status"] == "invalidated"
    assert receiver.queue.task(admitted["task_id"])["cancelled"]


def test_lesson_30_revoked_before_claim_is_terminal(mention):
    receiver, client, event = mention
    admitted = send(receiver, event)
    client.permissions["alice"] = "read"
    with pytest.raises(PermissionError):
        receiver.prepare_next()
    assert receiver.queue.task(admitted["task_id"])["status"] == "dead_letter"


def test_lesson_30_plan_is_read_only_terminal_then_fix_can_claim(mention):
    receiver, client, event = mention
    client.comments[1]["body"] = "@course-harness plan"
    planned = send(receiver, event)
    result = receiver.prepare_next()
    assert result["completed"] and result["plan"]["kind"] == "plan"
    assert receiver.queue.task(planned["task_id"])["status"] == "completed"
    assert not client.branches and not client.prs and not client.trace
    assert "digest" not in result and "branch" not in result
    client.comments[2] = dict(client.comments[1], body="@course-harness fix")
    fixed = send(receiver, event | {"comment_id": 2})
    prepared = receiver.prepare_next()
    assert prepared["task"]["id"] == fixed["task_id"]
    assert len(client.branches) == 1 and not client.prs


@pytest.mark.parametrize("lesson", [29, 30], ids=["lesson_29", "lesson_30"])
@pytest.mark.parametrize("scenario", ["coding", "sre", "automation"])
def test_extension_checkpoints(lesson, scenario):
    result = checkpoint(lesson, scenario)
    assert result["checks"] and all(result["checks"].values())
