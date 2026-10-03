# Lesson 13: Durable state and reconciliation

Lesson 12. Read [setup](../../../02-lab-book/setup.md) before running commands.

## What we are building

Recover after interruption without inventing certainty or repeating effects blindly. Work in one growing `course_harness` package. The checkpoint selects cumulative behavior; it does not replace your source or wipe your exercise changes.

## Picture the flow

```text
requested → approved → started → completed; crash after started → uncertain → observe → resolve
```

Text equivalent: requested passes into approved passes into started passes into completed; crash after started passes into uncertain passes into observe passes into resolve. Read the flow from left to right; a branch represents a controller decision, not a command from untrusted text.

## Read first, then make one small change

Read [the implementation](../../src/course_harness/persistence.py) and locate persisted state schema, action identity/transitions, and reconciliation. Trace the successful path before editing.

Use versioned SQLite state with stable run/event/action identifiers. Record intention and relevant approval before execution, started before an effect, and completed only after its observed result. A crash between effect and completion record creates ambiguity. Replaying a recorded result feeds evidence back into context; re-executing an action makes a new effect. Preserve remaining limits and scope on restart. Reject incompatible schema/state instead of treating it as empty.

The continuing examples remain a disposable coding repository, synthetic SRE observations/service state, and local automation events/artifacts. Reuse the same engine rather than copying it into three domain-specific loops.

## Minimal code to inspect and extend

Persist intention/approval/start before effects. Approval scope is caller-provided metadata: bind the real policy digest and expiry and validate them before `start_action`.

```python
from tempfile import TemporaryDirectory
from pathlib import Path
from course_harness.persistence import DurableStore
with TemporaryDirectory() as root:
    store = DurableStore(Path(root) / "state.sqlite", clock=lambda: 100)
    store.create_run("run-1", {"actions": 2})
    store.request_action("run-1", "action-1", {"target": "fixture"})
    scope = {"target": "fixture", "policy_digest": "reviewed-fixture"}
    store.approve_action("action-1", scope)
    store.start_action("action-1", scope)
    assert store.recover() == ["action-1"]
    assert store.action("action-1")["status"] == "uncertain"
    store.close()
```

Concrete exercise delta: Add a synthetic executor seam that crashes after mutation but before `complete_action`. Reopen state, call recovery only with exclusive startup ownership, observe the postcondition, and reconcile. The journal checks matching scope; it does not independently grant or validate host-policy approval.

The complete test fragment lives in the separate solution. Keep your new helper/test on your learning branch; baseline checkpoints remain available while you work.

## Run a checkpoint

From `tracks/agent-harness-from-scratch/03-labs`, with the environment installed as in setup:

```sh
python -m course_harness checkpoint 13 --scenario coding
python -m course_harness checkpoint 13 --scenario sre
python -m course_harness checkpoint 13 --scenario automation
pytest -q tests -k lesson_13
```

These are learner/approved-worker commands. Do not execute them on the source-only authoring Mac. Expected CLI output is JSON with `lesson`, `scenario`, `status`, `stop_reason`, `trace`, and `checks`. Inspect the check values and exit status; absence of selected tests is not a pass.

Recorded completed actions replay results without repeat effects; started ambiguous actions require observation/resolution; approval scope and remaining budgets survive. The walkthrough below explains meaningful event order; helper/fixture events may be represented inside check records rather than as literal CLI event names.

Exact baseline expectation: Expected recovery events use the journal's literal names: `run.created`, `budget.consumed`, `action.requested`, `action.approved`, `action.started`, `action.uncertain`, and `action.reconciled`. The checkpoint stop reason is `checkpoint_passed`.

## Read a successful trace

```text
action_requested -> action_approved -> action_started -> [crash] -> recovery -> action_uncertain -> reconciled
```

At each transition, state what was requested, what trusted code decided, and what effect was observed. Engine trace events include `run_started`, `model_called`, `tool_requested`, `tool_completed`, and `run_stopped`; denial and approval paths add `tool_denied` or `approval_required`. A recorded final answer is not evidence an unrecorded side effect occurred.

## Break it on purpose

Tamper a persisted version or reopen a started action without confirming its effect. The first must fail clearly; the second must remain inspectable and uncertain rather than silently repeat.

Keep the failure fixture separate from the reference fixture. Record the first violated contract, the last completed event, and whether any side effect happened. Restore the controlled input before comparing a successful run.

## Your exercise

Simulate a crash after the toy patch, synthetic restart, or artifact mutation but before the completion record. Reopen the database, inspect the real fixture postcondition, and resolve the action as completed or still uncertain. Add a test that restart does not automatically invoke the effect handler again.

Before opening the solution, write one learner test in a separate `test_learner_13.py`. Include one success assertion, one deliberate failure assertion, and one assertion about the boundary/effect. Choose state, identifiers, call counts, and stop reasons rather than incidental model wording.

Progressive hints:

1. Use one temporary database per test.
2. Simulate the crash at a deterministic boundary, not by randomly killing a process.
3. Compare expected postconditions before deciding completion.

[Reference solution and test reasoning](../../solutions/13.md). Try the first hint and your own test before reading it.

## Acceptance checks

Version rejection; durable identifiers; completed no-repeat; uncertain reconciliation; preserved scope/budget. Add a restart after requested but before started.

The selected delivered checks are a baseline. Your extra test should fail when your exercise change is removed and pass when it is restored. Use controlled fixtures and injected time; required checks need no network or real infrastructure. Record unimplemented or unvalidated assertions honestly.

## Explain it back

Why does SQLite not guarantee every external effect exactly once? What can a persisted 'started' row prove? Who may resolve an ambiguous effect?

Plain-language explanation: Durable records preserve what the harness knew. Reconciliation checks what the world actually contains when a record is incomplete.

Use the course rubric: needs guidance means you can follow the solution; independent means you can complete the edit and write a useful test; advanced means you can diagnose an unfamiliar failure and compare alternatives using evidence.

## Optional next extension

Represent an unknown outcome explicitly when observation cannot determine completion.

Keep this extension small and reversible. Commit your reviewed exercise diff on your learning branch before moving on. There is no capstone or separate final project.
