import pytest

from course_harness.core import Engine
from course_harness.providers import FakeProvider, Reply, ToolCall
from course_harness.tools import FixtureWorld, Policy, Registry
from examples.tool_creation import custom_tools, example


def test_lesson_04_worked_tool_contract_and_result():
    result = example()
    assert result.stop_reason == "final"
    assert '"count":2' in next(m["content"] for m in result.messages if m["role"] == "tool")


@pytest.mark.parametrize("name", ["service_diagnostics", "gated_remediation"])
def test_lesson_06_both_custom_tools_invalid_and_denied(name):
    world = FixtureWorld()
    registry = Registry(custom_tools(world))
    with pytest.raises(ValueError):
        registry.prepare(name, {"service": "production"})
    with pytest.raises(ValueError):
        registry.prepare(name, {"service": "toy-service", "extra": True})
    policy = Policy(allowed=frozenset())
    e = Engine(FakeProvider([Reply(calls=(ToolCall("a", name, {"service": "toy-service"}),))]), registry, policy)
    assert e.run("request").stop_reason == "denied"
    assert world.restarts == 0


def test_lesson_19_fourth_tool_needs_no_controller_change():
    world = FixtureWorld()
    registry = Registry(custom_tools(world))
    policy = Policy("semi", frozenset(registry.tools))
    tool = registry.tools["gated_remediation"]
    policy.approve(tool, {"service": "toy-service"})
    script = [Reply(calls=(ToolCall("a", "gated_remediation", {"service": "toy-service"}),)), Reply("observed restart")]
    assert Engine(FakeProvider(script), registry, policy).run("restart fixture").stop_reason == "final"
    assert world.restarts == 1
