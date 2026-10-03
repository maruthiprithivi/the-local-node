"""Your growing, standard-library harness. Implement TODOs in lesson order.

No imports from the finished course_harness package: you construct these boundaries.
One reply contains either final text or one tool call. This deliberately small
teaching contract grows into the richer reference protocol later.
"""
from copy import deepcopy
import json


def make_message(role, content):
    """L01: return {role, content}; reject unknown roles/non-string/oversized text."""
    raise NotImplementedError("L01: implement the message boundary")


def validate_reply(reply):
    """L01: require exactly text/call; validate final or one id/name/arguments call."""
    raise NotImplementedError("L01: validate a reply, then return a deep copy")


class ScriptedProvider:
    def __init__(self, replies):
        self.replies = iter(deepcopy(list(replies)))
        self.requests = []

    def complete(self, messages):
        """L01: capture isolated request; validate next reply; fail on exhaustion."""
        raise NotImplementedError("L01: obtain one scripted reply")


def dispatch_once(provider, history, tools, *, permission):
    """L05: model -> named tool -> result, or final; L06: gate BEFORE effects.

    tools maps an explicit name to a handler taking a dictionary.
    permission(name, arguments) is trusted external code: allow/deny/ask.
    Return status, text, used_calls, and trace; mutate only this run's history.
    """
    raise NotImplementedError("L05: one dispatch; L06: external permission gate")


def run(provider, prompt, tools, *, permission, max_steps=3, max_calls=2):
    """L05: controller owns ceilings; stop BEFORE work once a ceiling is reached.

    Return stop_reason, text, history, trace, steps, calls.
    Start a fresh history; every provider invocation consumes a step.
    Calls count only executed handlers; deny/ask stop immediately.
    """
    raise NotImplementedError("L05: bounded termination")

