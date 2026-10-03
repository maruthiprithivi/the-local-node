from course_harness.core import Engine, Limits
from course_harness.providers import FakeProvider, Reply, ToolCall
from course_harness.tools import FixtureWorld, Policy, Registry, Tool, object_schema, scenario_tools
from course_harness.persistence import DurableStore


def test_lesson_13_engine_receipts_prevent_duplicate_effect(tmp_path):
    world = FixtureWorld()
    registry = scenario_tools(world)
    policy = Policy("autonomous", frozenset(registry.tools), run_id="durable")
    store = DurableStore(tmp_path / "state.db")
    call = ToolCall("fixed-id", "restart_service", {"service": "toy-service"})
    def run():
        return Engine(FakeProvider([Reply(calls=(call,)), Reply("done")]), registry, policy, state_store=store).run("restart once")
    assert run().stop_reason == "final"
    assert run().stop_reason == "final"
    assert world.restarts == 1
    assert store.run("durable")["budgets"]["steps"] == 2
    store.close()


def test_lesson_13_engine_failure_is_uncertain_not_retried(tmp_path):
    effects = []
    def ambiguous(args):
        effects.append("effect happened")
        raise TimeoutError
    registry = Registry([Tool("mutate", "fixture", object_schema(), ambiguous, "write")])
    policy = Policy("autonomous", frozenset({"mutate"}), run_id="ambiguous")
    store = DurableStore(tmp_path / "state.db")
    def run():
        return Engine(FakeProvider([Reply(calls=(ToolCall("a", "mutate", {}),))]), registry, policy, state_store=store).run("mutate")
    assert run().stop_reason == "uncertain_effect"
    assert run().stop_reason == "uncertain_effect"
    assert effects == ["effect happened"]
    assert store.action("ambiguous:a")["status"] == "uncertain"
    store.close()


def test_lesson_13_restart_does_not_renew_deadline(tmp_path):
    now = [100.0]
    store = DurableStore(tmp_path / "state.db", clock=lambda: now[0])
    world = FixtureWorld()
    registry = scenario_tools(world)
    policy = Policy(allowed=frozenset(registry.tools), run_id="deadline")
    assert Engine(FakeProvider([Reply("first")]), registry, policy, state_store=store).run("observe").stop_reason == "final"
    now[0] = 111.0
    provider = FakeProvider([Reply("must not call")])
    assert Engine(provider, registry, policy, state_store=store).run("resume").stop_reason == "deadline"
    assert provider.requests == []
    store.close()
