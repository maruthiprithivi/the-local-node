# Lesson 10: Restricted commands and verified remediation

Lesson 9 and domain lessons 7–9. Read [setup](../../../02-lab-book/setup.md) before running commands.

## What we are building

Run only named course-owned commands, then verify effects rather than trust exit status alone. Work in one growing `course_harness` package. The checkpoint selects cumulative behavior; it does not replace your source or wipe your exercise changes.

## Picture the flow

```text
approved named action → fixed argv + limits → bounded result → postcondition check → stop/escalate
```

Text equivalent: approved named action passes into fixed argv + limits passes into bounded result passes into postcondition check passes into stop/escalate. Read the flow from left to right; a branch represents a controller decision, not a command from untrusted text.

## Read first, then make one small change

Read [the implementation](../../src/course_harness/tools.py) and locate restricted execution and synthetic SRE remediation handlers. Trace the successful path before editing.

A command runner accepts a named operation that maps to a fixed argument array and working directory. Avoid shell parsing and model-selected executables. Use a sanitized environment, output limit, timeout, and documented cleanup. Repository tests execute code, so expose only course-owned toy checks. Permit one synthetic service restart with a cooldown/attempt bound, then observe health. A zero return code is not proof that the intended state was reached.

The continuing examples remain a disposable coding repository, synthetic SRE observations/service state, and local automation events/artifacts. Reuse the same engine rather than copying it into three domain-specific loops.

## Minimal code to inspect and extend

Reject before launching. This fragment performs no subprocess work; positive/timeout tests require the approved disposable worker.

```python
from tempfile import TemporaryDirectory
from course_harness.tools import run_permitted
with TemporaryDirectory() as root:
    try:
        run_permitted(["unapproved-program", ";", "echo", "unsafe"],
                      allowed=frozenset(), cwd=root)
    except PermissionError:
        pass
    else:
        raise AssertionError("unapproved command was accepted")
```

Concrete exercise delta: Add a host-owned named-command mapping around `run_permitted`, and test a course-owned toy check on the approved worker. The delivered runner cleans the direct child on timeout; descendant cleanup and disk quotas are outside its guarantee. Keep synthetic restart verification separate from subprocess return codes.

The complete test fragment lives in the separate solution. Keep your new helper/test on your learning branch; baseline checkpoints remain available while you work.

## Run a checkpoint

From `tracks/agent-harness-from-scratch/03-labs`, with the environment installed as in setup:

```sh
python -m course_harness checkpoint 10 --scenario coding
python -m course_harness checkpoint 10 --scenario sre
python -m course_harness checkpoint 10 --scenario automation
pytest -q tests -k lesson_10
```

These are learner/approved-worker commands. Do not execute them on the source-only authoring Mac. Expected CLI output is JSON with `lesson`, `scenario`, `status`, `stop_reason`, `trace`, and `checks`. Inspect the check values and exit status; absence of selected tests is not a pass.

Only explicitly allowed work starts; captured output stays bounded; a verified recovery finishes, while failed verification stops after the attempt ceiling. The walkthrough below explains meaningful event order; helper/fixture events may be represented inside check records rather than as literal CLI event names.

Exact baseline expectation: Autonomous fixture actions remain allowlisted and bounded. Expect final termination and `verified_fixture_effect: true`; the command runner's subprocess cases are separate acceptance tests.

## Read a successful trace

```text
tool_requested -> policy_allowed -> action_started -> tool_completed -> verification -> final | escalation
```

At each transition, state what was requested, what trusted code decided, and what effect was observed. Engine trace events include `run_started`, `model_called`, `tool_requested`, `tool_completed`, and `run_stopped`; denial and approval paths add `tool_denied` or `approval_required`. A recorded final answer is not evidence an unrecorded side effect occurred.

## Break it on purpose

Supply shell metacharacters as an argument, then a command alias not in the allowlist. The metacharacters must never be interpreted by a shell; the unknown command must not start. Simulate restart success with unhealthy verification and require escalation.

Keep the failure fixture separate from the reference fixture. Record the first violated contract, the last completed event, and whether any side effect happened. Restore the controlled input before comparing a successful run.

## Your exercise

Run a course-owned toy function check after the approved edit from lesson 7. For SRE, permit one restart of the disposable fixture service and verify health. For automation, route a local check through the same gate. Add failure cases for unknown commands and failed postconditions.

Before opening the solution, write one learner test in a separate `test_learner_10.py`. Include one success assertion, one deliberate failure assertion, and one assertion about the boundary/effect. Choose state, identifiers, call counts, and stop reasons rather than incidental model wording.

Progressive hints:

1. Map a symbolic operation to argv; do not split arbitrary model text.
2. Test handler launch count for denial.
3. Inject a failing health fixture instead of restarting a real service.

[Reference solution and test reasoning](../../solutions/10.md). Try the first hint and your own test before reading it.

## Acceptance checks

Unknown command zero launches; fixed argv; time/output limits; cooldown/attempt ceiling; verification failure escalates. Add a nonzero-command-exit test.

The selected delivered checks are a baseline. Your extra test should fail when your exercise change is removed and pass when it is restored. Use controlled fixtures and injected time; required checks need no network or real infrastructure. Record unimplemented or unvalidated assertions honestly.

## Explain it back

Why do timeouts need cleanup? Why is an allowlisted interpreter still powerful? How does verification differ from a command returning zero?

Plain-language explanation: Authorization establishes permission to attempt an action. Observation after the action establishes what happened.

Use the course rubric: needs guidance means you can follow the solution; independent means you can complete the edit and write a useful test; advanced means you can diagnose an unfamiliar failure and compare alternatives using evidence.

## Optional next extension

Document/test platform-specific subprocess cleanup on an approved disposable worker.

Keep this extension small and reversible. Commit your reviewed exercise diff on your learning branch before moving on. There is no capstone or separate final project.
