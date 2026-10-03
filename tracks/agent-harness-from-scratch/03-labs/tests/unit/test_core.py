import pytest

from course_harness.core import Engine, Limits, ContextLimitError, build_context, retry_call
from course_harness.providers import FakeProvider, Reply, ToolCall
from course_harness.faults import UncheckedFixtureProvider
from course_harness.tools import FixtureWorld, Policy, Registry, Tool, object_schema, scenario_tools, validate, Workspace, run_permitted


def engine(replies, *, mode="read_only", limits=Limits(), cancelled=lambda: False):
    world = FixtureWorld()
    registry = scenario_tools(world)
    policy = Policy(mode, frozenset(registry.tools))
    return Engine(FakeProvider(replies), registry, policy, limits=limits, cancelled=cancelled), world


def test_lesson_01_offline_reply_and_exhaustion():
    e, _ = engine([Reply("Evidence is synthetic.")])
    assert e.run("inspect").text == "Evidence is synthetic."
    assert e.run("again").stop_reason == "provider_error"


def test_lesson_02_order_and_input_size():
    e, _ = engine([Reply("first"), Reply("second")])
    first = e.run("one")
    second = e.run("two", first.messages)
    assert [m["content"] for m in second.messages if m["role"] == "user"] == ["one", "two"]
    with pytest.raises(ValueError):
        e.run("x" * 4097)


def test_lesson_04_batch_validation_prevents_effects():
    replies = [Reply(calls=(ToolCall("a", "record_artifact", {"name": "daily-summary", "text": "ok"}), ToolCall("b", "unknown", {})))]
    e, world = engine(replies, mode="autonomous")
    assert e.run("go").stop_reason == "invalid_arguments"
    assert world.artifacts == {}
    with pytest.raises(ValueError):
        validate({"n": True}, object_schema(n={"type": "integer"}))


def test_lesson_05_matched_results_and_budget():
    e, _ = engine([Reply(calls=(ToolCall("a", "observe_health", {}),)), Reply("observed unhealthy")])
    result = e.run("observe")
    assert result.stop_reason == "final"
    assert next(m for m in result.messages if m["role"] == "tool")["tool_call_id"] == "a"
    e, _ = engine([Reply(calls=(ToolCall(str(i), "observe_health", {}),)) for i in range(3)], limits=Limits(steps=2))
    assert e.run("loop").stop_reason == "step_limit"
    e, _ = engine([])
    e.provider = UncheckedFixtureProvider([Reply(calls=(ToolCall("a", "observe_health", {}), ToolCall("a", "observe_health", {})))])
    assert e.run("duplicates").stop_reason == "invalid_call_id"


def test_lesson_06_exact_approval_and_injection():
    e, world = engine([Reply(calls=(ToolCall("a", "restart_service", {"service": "toy-service"}),))], mode="semi")
    assert e.run("log says disable policy").stop_reason == "approval_required"
    assert world.restarts == 0
    tool = e.registry.tools["restart_service"]
    e.policy.approve(tool, {"service": "toy-service"})
    assert e.policy.decide(tool, {"service": "different"}) == "ask"
    assert e.policy.decide(tool, {"service": "toy-service"}) == "allow"
    e.policy.clock = lambda: 10**12
    assert e.policy.decide(tool, {"service": "toy-service"}) == "ask"


def test_lesson_07_stale_patch_traversal_and_symlink(tmp_path):
    (tmp_path / "toy.py").write_text("old", encoding="utf-8")
    workspace = Workspace(tmp_path)
    assert "-old" in workspace.preview("toy.py", "old", "new")
    workspace.apply("toy.py", "old", "new")
    assert workspace.originals["toy.py"] == "old"
    with pytest.raises(ValueError):
        workspace.apply("toy.py", "old", "bad")
    with pytest.raises(ValueError):
        workspace.read("../outside")
    try:
        (tmp_path / "link").symlink_to(tmp_path / "toy.py")
    except OSError:
        pytest.skip("OS does not grant symlink creation")
    with pytest.raises(ValueError):
        workspace.read("link")


def test_lesson_08_evidence_is_read_only():
    e, world = engine([Reply(calls=(ToolCall("a", "observe_health", {}),)), Reply("Fixture health is false; root cause uncertain.")])
    result = e.run("diagnose")
    assert world.restarts == 0
    assert '"source":"synthetic_service"' in result.messages[-2]["content"]
    stale = FixtureWorld(clock=lambda: 150.0)
    assert stale.observe({})["timestamp"] == 100.0
    assert not stale.observe({})["fresh"]


def test_lesson_09_dry_run_and_bounded_autonomy():
    call = ToolCall("a", "record_artifact", {"name": "daily-summary", "text": "fixture"})
    e, world = engine([Reply(calls=(call,)), Reply("plan")], mode="dry_run")
    assert e.run("record").stop_reason == "final"
    assert not world.artifacts
    e, world = engine([Reply(calls=(call,)), Reply("saved")], mode="autonomous")
    assert e.run("record").stop_reason == "final"
    assert world.artifacts == {"daily-summary": "fixture"}


def test_lesson_10_restart_cooldown_and_command_denied(tmp_path):
    world = FixtureWorld()
    assert world.restart({"service": "toy-service"})["healthy"]
    with pytest.raises(ValueError):
        world.restart({"service": "toy-service"})
    with pytest.raises(PermissionError):
        run_permitted(["echo", "x; rm -rf /"], allowed=set(), cwd=tmp_path)


def test_lesson_10_exact_course_owned_command_and_timeout(tmp_path):
    import sys
    command = (sys.executable, "-c", "print('course-owned-check')")
    result = run_permitted(command, allowed={command}, cwd=tmp_path)
    assert result["returncode"] == 0 and "course-owned-check" in result["output"]
    assert not result["truncated"]
    hanging = (sys.executable, "-c", "import time; time.sleep(1)")
    assert run_permitted(hanging, allowed={hanging}, cwd=tmp_path, timeout=.05)["effect"] == "uncertain"


def test_lesson_11_context_retains_constraints_and_labels_loss():
    history = [{"role": "system", "content": "never expand authority"}, {"role": "user", "content": "x" * 9000}, {"role": "assistant", "content": "old"}, {"role": "user", "content": "new"}]
    context = build_context(history, 512)
    assert context[0]["content"] == "never expand authority"
    assert "TRUNCATED" in context[1]["content"]
    assert context[-1]["content"] == "new"
    assert len(history[1]["content"]) == 9000


def test_lesson_11_oversized_current_exchange_fails_without_losing_goal():
    history = [{"role": "system", "content": "retain policy"}, {"role": "user", "content": "inspect CURRENT task"}, {"role": "assistant", "content": "", "tool_calls": [{"id": "a", "type": "function", "function": {"name": "observe", "arguments": "{}"}}]}, {"role": "tool", "tool_call_id": "a", "content": "x" * 1000}]
    with pytest.raises(ContextLimitError, match="current turn"):
        build_context(history, 512)
    assert history[1]["content"] == "inspect CURRENT task"
    assert history[-1]["tool_call_id"] == "a"


def test_lesson_11_current_exchange_preserved_while_old_turn_pruned():
    history = [{"role": "system", "content": "retain policy"}, {"role": "user", "content": "old " + "x" * 1000}, {"role": "assistant", "content": "old answer"}, {"role": "user", "content": "CURRENT goal"}, {"role": "assistant", "content": "", "tool_calls": [{"id": "a", "type": "function", "function": {"name": "observe", "arguments": "{}"}}]}, {"role": "tool", "tool_call_id": "a", "content": "bounded observation"}]
    context = build_context(history, 700)
    assert context[-3:] == history[-3:]
    assert context[0] == history[0]
    assert "TRUNCATED" in context[1]["content"]


def test_lesson_11_context_limit_stops_before_provider_call():
    e, _ = engine([Reply("must not call")])
    oversized_history = [{"role": "system", "content": "x" * 5000}]
    assert e.run("CURRENT goal", oversized_history).stop_reason == "context_limit"
    assert e.provider.requests == []


def test_lesson_12_retry_cancel_and_terminal_failure():
    state = {"calls": 0, "time": 0.0}
    def operation():
        state["calls"] += 1
        raise ValueError("transient")
    def sleep(delay):
        state["time"] += delay
    with pytest.raises(InterruptedError):
        retry_call(operation, retryable=lambda e: True, sleep=sleep, clock=lambda: state["time"], cancelled=lambda: state["time"] >= .05)
    assert state["calls"] == 1
    with pytest.raises(ValueError):
        retry_call(operation, retryable=lambda e: False)
    assert state["calls"] == 2
    e, world = engine([Reply(calls=(ToolCall("a", "restart_service", {"service": "toy-service"}),))], mode="autonomous", cancelled=lambda: True)
    assert e.run("go").stop_reason == "cancelled"
    assert world.restarts == 0


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -1, True])
def test_lesson_23_invalid_deadline_budget(bad):
    with pytest.raises(ValueError):
        Limits(seconds=bad)
