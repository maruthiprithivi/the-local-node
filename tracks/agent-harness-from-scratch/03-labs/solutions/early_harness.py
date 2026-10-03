"""Completed version of exercises/harness.py; stdlib only, offline by construction."""
from copy import deepcopy
import json


def make_message(role, content):
    if not isinstance(role, str) or role not in {"system", "user", "assistant", "tool"}:
        raise ValueError("unknown message role")
    if not isinstance(content, str) or len(content) > 1024:
        raise ValueError("message content must be a bounded string")
    return {"role": role, "content": content}


def validate_reply(reply):
    if not isinstance(reply, dict) or set(reply) != {"text", "call"}:
        raise ValueError("reply requires exactly text and call")
    make_message("assistant", reply["text"])
    call = reply["call"]
    if call is not None:
        if reply["text"]:
            raise ValueError("reply cannot mix final text and a tool request")
        if not isinstance(call, dict) or set(call) != {"id", "name", "arguments"}:
            raise ValueError("invalid call shape")
        if any(not isinstance(call[key], str) or not call[key] or
               len(call[key]) > 128 for key in ("id", "name")):
            raise ValueError("invalid call identifier or name")
        if not isinstance(call["arguments"], dict):
            raise ValueError("arguments must be an object")
        try:
            encoded = json.dumps(call["arguments"], allow_nan=False)
        except (TypeError, ValueError, RecursionError) as error:
            raise ValueError("arguments must be JSON data") from error
        if len(encoded.encode("utf-8")) > 512:
            raise ValueError("arguments exceed limit")
    return deepcopy(reply)


class ScriptedProvider:
    def __init__(self, replies):
        self.replies = iter(deepcopy(list(replies)))
        self.requests = []

    def complete(self, messages):
        request = [make_message(message["role"], message["content"])
                   for message in messages]
        self.requests.append(deepcopy(request))
        try:
            reply = next(self.replies)
        except StopIteration as error:
            raise ValueError("script exhausted") from error
        return validate_reply(reply)


def dispatch_once(provider, history, tools, *, permission):
    reply = provider.complete(history)
    call = reply["call"]
    trace = ["model_called"]
    if call is None:
        history.append(make_message("assistant", reply["text"]))
        return {"status": "final", "text": reply["text"],
                "used_calls": 0, "trace": trace}
    name, arguments = call["name"], call["arguments"]
    if name not in tools:
        raise ValueError("unknown tool")
    trace.append("tool_requested")
    decision = permission(name, deepcopy(arguments))
    if decision not in {"allow", "deny", "ask"}:
        raise ValueError("unknown permission decision")
    if decision != "allow":
        trace.append("tool_denied" if decision == "deny" else "approval_required")
        return {"status": "denied" if decision == "deny" else "approval_required",
                "text": "", "used_calls": 0, "trace": trace}
    # Request text is data; only this external decision can permit execution.
    result = tools[name](deepcopy(arguments))
    content = json.dumps({"call_id": call["id"], "result": result},
                         allow_nan=False, sort_keys=True)
    history.append(make_message("assistant", json.dumps(call, sort_keys=True)))
    history.append(make_message("tool", content))
    trace.append("tool_completed")
    return {"status": "continue", "text": "", "used_calls": 1, "trace": trace}


def run(provider, prompt, tools, *, permission, max_steps=3, max_calls=2):
    if type(max_steps) is not int or type(max_calls) is not int or min(max_steps, max_calls) < 1:
        raise ValueError("limits must be positive integers")
    history = [make_message("user", prompt)]
    trace, steps, calls = ["run_started"], 0, 0

    def finish(reason, text=""):
        return {"stop_reason": reason, "text": text, "history": history,
                "trace": trace + ["run_stopped"], "steps": steps, "calls": calls}

    while True:
        if steps >= max_steps:
            return finish("step_limit")
        if calls >= max_calls:
            return finish("call_limit")
        steps += 1
        try:
            outcome = dispatch_once(provider, history, tools, permission=permission)
        except ValueError:
            # Shape/unknown tool failures are visible and never treated as success.
            return finish("invalid_request")
        calls += outcome["used_calls"]
        trace.extend(outcome["trace"])
        if outcome["status"] != "continue":
            return finish(outcome["status"], outcome["text"])
