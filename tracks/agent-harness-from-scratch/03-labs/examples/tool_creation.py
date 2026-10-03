"""Runnable worked starter: functions -> schema -> registry -> policy -> trace.

Lesson4: add filtering to count_fixture_rows. Lesson6: deny/remediate. Lesson19:
expose diagnostics as a trusted manifest capability. Nothing accesses real SRE.
"""
from course_harness.core import Engine
from course_harness.providers import FakeProvider, Reply, ToolCall
from course_harness.tools import FixtureWorld, Policy, Registry, Tool, object_schema, scenario_tools

ROWS = {"coding": ["calculator.py", "test_calculator.py"], "sre": ["healthy", "stale"], "automation": ["event1", "event2", "event2"]}


def count_fixture_rows(args):
    # Learner extension: add a validated nonempty_only option before filtering.
    return {"count": len(ROWS[args["fixture"]][:args["limit"]]), "source": args["fixture"]}


def custom_tools(world):
    service = {"type": "string", "enum": ["toy-service"]}
    result = object_schema(count={"type": "integer", "minimum": 0}, source={"type": "string"})
    return [
        Tool("count_fixture_rows", "Count bounded fixture records", object_schema(fixture={"type": "string", "enum": list(ROWS)}, limit={"type": "integer", "minimum": 0, "maximum": 10}), count_fixture_rows, "pure", "fixtures", result),
        Tool("service_diagnostics", "Read a synthetic service observation", object_schema(service=service), lambda args: world.observe({}), "read", "toy-service"),
        Tool("gated_remediation", "Restart only the explicitly permitted synthetic service", object_schema(service=service), world.restart, "write", "toy-service"),
    ]


def example():
    world = FixtureWorld()
    registry = scenario_tools(world)
    registry = Registry(list(registry.tools.values()) + custom_tools(world))
    policy = Policy(allowed=frozenset({"count_fixture_rows", "service_diagnostics"}))
    provider = FakeProvider([Reply(calls=(ToolCall("count", "count_fixture_rows", {"fixture": "coding", "limit": 10}),)), Reply("Two coding records observed.")])
    return Engine(provider, registry, policy).run("Count coding fixture records.")


if __name__ == "__main__":
    import json
    result = example()
    print(json.dumps({"stop_reason": result.stop_reason, "trace": result.trace}, sort_keys=True))
