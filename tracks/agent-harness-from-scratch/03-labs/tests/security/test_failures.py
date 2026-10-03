import pytest
from course_harness.core import Engine, Limits
from course_harness.providers import FakeProvider, Reply, ToolCall, ProviderError
from course_harness.faults import UncheckedFixtureProvider
from course_harness.tools import FixtureWorld, Policy, scenario_tools, Registry, Tool, object_schema


@pytest.mark.parametrize("lesson", [21, 23], ids=["lesson_21", "lesson_23"])
def test_injection_does_not_authorize_and_size_stops(lesson):
    world = FixtureWorld()
    registry = scenario_tools(world)
    policy = Policy(allowed=frozenset({"observe_health"}))
    e = Engine(FakeProvider([Reply(calls=(ToolCall("a", "restart_service", {"service": "toy-service"}),))]), registry, policy)
    assert e.run("untrusted log says grant permission").stop_reason == "denied"
    assert world.restarts == 0
    e = Engine(FakeProvider([Reply("x" * 100)]), registry, policy, limits=Limits(output_chars=50))
    assert e.run("huge output").stop_reason == "output_limit"


def test_lesson_23_duplicate_guard_at_provider_and_controller():
    executions = []
    registry = Registry([Tool("observe", "spy", object_schema(), lambda args: executions.append(args))])
    policy = Policy(allowed=frozenset({"observe"}))
    malformed = Reply(calls=(ToolCall("duplicate", "observe", {}), ToolCall("duplicate", "observe", {})))
    with pytest.raises(ProviderError) as failure:
        FakeProvider([malformed]).complete([])
    assert failure.value.category == "duplicate_call_id"
    provider_result = Engine(FakeProvider([malformed]), registry, policy).run("probe")
    assert provider_result.stop_reason == "provider_error"
    assert not any(e["event"] == "model_called" for e in provider_result.trace)
    controller_result = Engine(UncheckedFixtureProvider([malformed]), registry, policy).run("probe")
    assert controller_result.stop_reason == "invalid_call_id"
    assert any(e["event"] == "model_called" for e in controller_result.trace)
    assert not any(e["event"] == "tool_requested" for e in controller_result.trace)
    assert executions == []


def test_lesson_23_controller_rejects_id_reused_across_valid_turns():
    executions = []
    registry = Registry([Tool("observe", "spy", object_schema(), lambda args: executions.append(args))])
    valid_reply = Reply(calls=(ToolCall("same", "observe", {}),))
    result = Engine(FakeProvider([valid_reply, valid_reply]), registry, Policy(allowed=frozenset({"observe"}))).run("probe")
    assert result.stop_reason == "invalid_call_id"
    assert executions == [{}]


@pytest.mark.parametrize("lesson", [21, 23], ids=["lesson_21", "lesson_23"])
@pytest.mark.parametrize("scenario", ["coding", "sre", "automation"])
def test_duplicate_checkpoint_reports_both_boundaries(lesson, scenario):
    from course_harness.__main__ import checkpoint
    result = checkpoint(lesson, scenario)
    assert result["status"] == "ok"
    assert result["checks"]["duplicate_rejected"]
    assert result["checks"]["provider_duplicate_rejected"]
    assert any(e.get("category") == "duplicate_call_id" for e in result["trace"])
    assert any(e.get("reason") == "invalid_call_id" for e in result["trace"])
