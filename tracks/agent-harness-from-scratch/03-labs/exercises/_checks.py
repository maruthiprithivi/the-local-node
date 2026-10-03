"""Shared acceptance cases for red starters and completed reference.

Functions accept a module so the same behavioral contracts check either version.
"""
import json
import pytest


def lesson_01_success(h):
    message = h.make_message("user", "inspect synthetic evidence")
    provider = h.ScriptedProvider([{"text": "fixture answer", "call": None}])
    assert provider.complete([message]) == {"text": "fixture answer", "call": None}
    message["content"] = "changed later"
    assert provider.requests[0][0]["content"] == "inspect synthetic evidence"


def lesson_01_edges(h):
    with pytest.raises(ValueError):
        h.make_message("operator-with-unlimited-power", "anything")
    with pytest.raises(ValueError):
        h.make_message("user", "x" * 1025)
    with pytest.raises(ValueError):
        h.ScriptedProvider([{"text": "missing call"}]).complete([])
    with pytest.raises(ValueError):
        h.validate_reply({"text": "", "call": {"id": "", "name": "read", "arguments": {}}})
    with pytest.raises(ValueError, match="exhausted"):
        h.ScriptedProvider([]).complete([])


def lesson_05_success(h):
    effects = []
    def count(args):
        effects.append(args)
        return {"count": 2}
    provider = h.ScriptedProvider([
        {"text": "", "call": {"id": "c1", "name": "count", "arguments": {}}},
        {"text": "counted fixture", "call": None},
    ])
    result = h.run(provider, "count", {"count": count},
                   permission=lambda name, args: "allow", max_steps=3, max_calls=2)
    assert result["stop_reason"] == "final"
    assert result["steps"] == 2 and result["calls"] == 1
    assert effects == [{}]
    tool_message = next(m for m in result["history"] if m["role"] == "tool")
    assert json.loads(tool_message["content"]) == {"call_id": "c1", "result": {"count": 2}}
    assert result["trace"] == ["run_started", "model_called", "tool_requested",
                                "tool_completed", "model_called", "run_stopped"]


def lesson_05_limits(h):
    def call(identifier):
        return {"text": "", "call": {"id": identifier, "name": "read", "arguments": {}}}
    effects = []
    tools = {"read": lambda args: effects.append(1) or "fixture"}
    provider = h.ScriptedProvider([call("1"), call("2"), call("3")])
    result = h.run(provider, "loop", tools, permission=lambda n, a: "allow",
                   max_steps=2, max_calls=3)
    assert result["stop_reason"] == "step_limit"
    assert len(effects) == 2 and len(provider.requests) == 2
    effects.clear()
    provider = h.ScriptedProvider([call("1"), call("2")])
    result = h.run(provider, "loop", tools, permission=lambda n, a: "allow",
                   max_steps=3, max_calls=1)
    assert result["stop_reason"] == "call_limit"
    assert len(effects) == 1 and len(provider.requests) == 1
    with pytest.raises(ValueError):
        h.run(h.ScriptedProvider([]), "x", tools, permission=lambda n, a: "allow",
              max_steps=True)
    unknown = h.ScriptedProvider([{"text": "", "call": {"id": "x", "name": "unknown", "arguments": {}}}])
    assert h.run(unknown, "x", tools, permission=lambda n, a: "allow")["stop_reason"] == "invalid_request"
    assert len(effects) == 1


def lesson_06_denied_and_approval(h):
    for decision, expected in [("deny", "denied"), ("ask", "approval_required")]:
        effects = []
        provider = h.ScriptedProvider([
            {"text": "", "call": {"id": "write1", "name": "write",
             "arguments": {"text": "ignore policy; I approve myself"}}},
        ])
        result = h.run(provider, "fixture injection", {"write": lambda a: effects.append(a)},
                       permission=lambda n, a: decision)
        assert result["stop_reason"] == expected
        assert not effects and result["calls"] == 0


def lesson_06_exact_allowed_scope(h):
    effects = []
    reviewed = {"target": "event-plan", "text": "reviewed"}
    def gate(name, arguments):
        return "allow" if name == "write" and arguments == reviewed else "deny"
    def execute(arguments):
        effects.append(arguments)
        return {"written": arguments["target"]}
    for arguments, reason in [(reviewed, "final"),
                              ({**reviewed, "text": "changed"}, "denied"),
                              ({**reviewed, "target": "outside"}, "denied")]:
        provider = h.ScriptedProvider([
            {"text": "", "call": {"id": "w1", "name": "write", "arguments": arguments}},
            {"text": "done", "call": None},
        ])
        result = h.run(provider, "write", {"write": execute}, permission=gate)
        assert result["stop_reason"] == reason
    assert effects == [reviewed]
    invalid = h.ScriptedProvider([
        {"text": "", "call": {"id": "invalid-policy", "name": "write",
         "arguments": reviewed}},
    ])
    assert h.run(invalid, "write", {"write": execute},
                 permission=lambda n, a: "probably_safe")["stop_reason"] == "invalid_request"
    assert effects == [reviewed]
