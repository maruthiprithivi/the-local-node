import pytest
from course_harness.core import Engine, Limits
from course_harness.providers import FakeProvider, Reply, ToolCall
from course_harness.tools import FixtureWorld, Policy, scenario_tools


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
