# Lesson 9: Automation plans, dry-run, and bounded autonomy

Lesson 8. Read [setup](../../../02-lab-book/setup.md) before running commands.

## What we are building

Make three modes of execution observable on the same local event. Work in one growing `course_harness` package. The checkpoint selects cumulative behavior; it does not replace your source or wipe your exercise changes.

## Picture the flow

```text
fixture event → plan → dry-run / approval wait / allowlisted action → local artifact
```

Text equivalent: fixture event passes into plan passes into dry-run / approval wait / allowlisted action passes into local artifact. Read the flow from left to right; a branch represents a controller decision, not a command from untrusted text.

## Read first, then make one small change

Read [the implementation](../../src/course_harness/tools.py) and locate automation fixture handlers and `Policy` modes. Trace the successful path before editing.

Translate a fixture event into a proposed action, not immediate execution. Dry-run records a plan without effects; semi mode waits at approval gates; autonomous mode still checks allowlist, target, argument contracts, and action budget. Use a temporary artifact, not notifications or external applications. Keep pending action identity so lesson 13 can persist it. Compare all modes against the same event and fake response.

The continuing examples remain a disposable coding repository, synthetic SRE observations/service state, and local automation events/artifacts. Reuse the same engine rather than copying it into three domain-specific loops.

## Minimal code to inspect and extend

Preview is a distinct policy decision, not an executed result.

```python
from course_harness.tools import FixtureWorld, scenario_tools, Policy
world = FixtureWorld()
tool = scenario_tools(world).tools["record_artifact"]
args = {"name": "event-plan", "text": "proposed"}
policy = Policy("dry_run", frozenset({tool.name}))
assert policy.decide(tool, args) == "preview"
assert not world.artifacts
```

Concrete exercise delta: Add a fixture-event planner that returns the same structured action under each mode. Keep routing in ordinary Python. Test that the executor is called only for allow, never for preview/ask/deny, and that the action ceiling applies across the event plan.

The complete test fragment lives in the separate solution. Keep your new helper/test on your learning branch; baseline checkpoints remain available while you work.

## Run a checkpoint

From `tracks/agent-harness-from-scratch/03-labs`, with the environment installed as in setup:

```sh
python -m course_harness checkpoint 9 --scenario coding
python -m course_harness checkpoint 9 --scenario sre
python -m course_harness checkpoint 9 --scenario automation
pytest -q tests -k lesson_09
```

These are learner/approved-worker commands. Do not execute them on the source-only authoring Mac. Expected CLI output is JSON with `lesson`, `scenario`, `status`, `stop_reason`, `trace`, and `checks`. Inspect the check values and exit status; absence of selected tests is not a pass.

Dry-run has zero effects; allowlisted autonomous action changes only its target; semi reports approval_required and can continue only with an exact approval. The walkthrough below explains meaningful event order; helper/fixture events may be represented inside check records rather than as literal CLI event names.

Exact baseline expectation: The scenario run stops as `final` with preview results; `dry_run_no_effect` confirms no fixture mutations.

## Read a successful trace

```text
event_observed -> plan_proposed -> tool_requested -> approval_required | tool_completed | tool_denied
```

At each transition, state what was requested, what trusted code decided, and what effect was observed. Engine trace events include `run_started`, `model_called`, `tool_requested`, `tool_completed`, and `run_stopped`; denial and approval paths add `tool_denied` or `approval_required`. A recorded final answer is not evidence an unrecorded side effect occurred.

## Break it on purpose

Choose an artifact outside allowed scope or exhaust action count. No file should be created. In semi mode, an unapproved action must remain pending rather than be reported completed.

Keep the failure fixture separate from the reference fixture. Record the first violated contract, the last completed event, and whether any side effect happened. Restore the controlled input before comparing a successful run.

## Your exercise

Route a harmless fixture event to one allowed artifact update and a second event to an approval-required update. Run both under dry-run, semi, and autonomous policies. Write a test that a confident final model statement cannot convert denial into permission.

Before opening the solution, write one learner test in a separate `test_learner_09.py`. Include one success assertion, one deliberate failure assertion, and one assertion about the boundary/effect. Choose state, identifiers, call counts, and stop reasons rather than incidental model wording.

Progressive hints:

1. Measure effects by inspecting fixture state.
2. Use identical proposals when comparing modes.
3. Carry action identity separately from a display string.

[Reference solution and test reasoning](../../solutions/09.md). Try the first hint and your own test before reading it.

## Acceptance checks

Dry-run no effects; bounded allowlisted action; semi waiting; persistent support added later; denial independent of wording. Add a budget-boundary test for the next action.

The selected delivered checks are a baseline. Your extra test should fail when your exercise change is removed and pass when it is restored. Use controlled fixtures and injected time; required checks need no network or real infrastructure. Record unimplemented or unvalidated assertions honestly.

## Explain it back

What exactly is autonomous here? Is a dry-run tool result evidence that an effect occurred? What state must survive an approval pause?

Plain-language explanation: The mode changes how a policy handles valid requests. It never gives the model permission to invent operations or targets.

Use the course rubric: needs guidance means you can follow the solution; independent means you can complete the edit and write a useful test; advanced means you can diagnose an unfamiliar failure and compare alternatives using evidence.

## Optional next extension

Add a preview showing exact arguments and relevant preconditions.

Keep this extension small and reversible. Commit your reviewed exercise diff on your learning branch before moving on. There is no capstone or separate final project.
