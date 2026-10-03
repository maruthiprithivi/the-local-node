# Lesson 9: Automation plans, dry-run, and bounded autonomy: narration script

This is a readable recording script, not a published recording. It is adapted
from the canonical lesson text; keep that lab open for exact source snippets,
commands and separate solutions. Caption future recordings and describe arrows
and state changes aloud. The examples use synthetic fixtures and an offline fake
provider. Do not run demonstrations on the source-only authoring Mac.

## Opening and purpose

Make three modes of execution observable on the same local event. Work in one growing `course_harness` package. The checkpoint selects cumulative behavior; it does not replace your source or wipe your exercise changes.

## Describe the diagram aloud

```text
fixture event → plan → dry-run / approval wait / allowlisted action → local artifact
```

Text equivalent: fixture event passes into plan passes into dry-run / approval wait / allowlisted action passes into local artifact. Read the flow from left to right; a branch represents a controller decision, not a command from untrusted text.

Read each arrow in order. Explain what enters the boundary, which trusted
component decides, and what evidence comes out. Pause before displaying code.

## Source walkthrough

Read [the implementation](../../src/course_harness/tools.py) and locate automation fixture handlers and `Policy` modes. Trace the successful path before editing.

Translate a fixture event into a proposed action, not immediate execution. Dry-run records a plan without effects; semi mode waits at approval gates; autonomous mode still checks allowlist, target, argument contracts, and action budget. Use a temporary artifact, not notifications or external applications. Keep pending action identity so lesson 13 can persist it. Compare all modes against the same event and fake response.

The continuing examples remain a disposable coding repository, synthetic SRE observations/service state, and local automation events/artifacts. Reuse the same engine rather than copying it into three domain-specific loops.

Open the lesson's minimal snippet. Narrate arguments, preconditions and return
values before typing the learner change. Keep the reference implementation intact
on its branch; learner tests should expose an unfinished TODO or missing guard.

## Demonstration and successful trace

Use the checkpoint commands from the lab on an approved execution host. Capture
actual terminal output; the following trace is a semantic narration, not a claim
that these exact event names are printed by every helper.

```text
event_observed -> plan_proposed -> tool_requested -> approval_required | tool_completed | tool_denied
```

At each transition, state what was requested, what trusted code decided, and what effect was observed. Engine trace events include `run_started`, `model_called`, `tool_requested`, `tool_completed`, and `run_stopped`; denial and approval paths add `tool_denied` or `approval_required`. A recorded final answer is not evidence an unrecorded side effect occurred.

Pause to inspect identifiers, stop reasons and effect counts. A fixture result
is evidence about this classroom mechanism, not production security or live
model quality.

## Controlled failure walkthrough

Choose an artifact outside allowed scope or exhaust action count. No file should be created. In semi mode, an unapproved action must remain pending rather than be reported completed.

Keep the failure fixture separate from the reference fixture. Record the first violated contract, the last completed event, and whether any side effect happened. Restore the controlled input before comparing a successful run.

Ask the learner to predict the last completed event, state and permitted effect
count before showing the result. Show the smallest violated boundary; restore the
controlled input before demonstrating success again.

## Learner pause and explanation

Route a harmless fixture event to one allowed artifact update and a second event to an approval-required update. Run both under dry-run, semi, and autonomous policies. Write a test that a confident final model statement cannot convert denial into permission.

Before opening the solution, write one learner test in a separate `test_learner_09.py`. Include one success assertion, one deliberate failure assertion, and one assertion about the boundary/effect. Choose state, identifiers, call counts, and stop reasons rather than incidental model wording.

Progressive hints:

1. Measure effects by inspecting fixture state.
2. Use identical proposals when comparing modes.
3. Carry action identity separately from a display string.

[Reference solution and test reasoning](../../solutions/09.md). Try the first hint and your own test before reading it.

Wait before revealing the separate worked solution. Then ask the learner to
explain the boundary in their own words:

What exactly is autonomous here? Is a dry-run tool result evidence that an effect occurred? What state must survive an approval pause?

Plain-language explanation: The mode changes how a policy handles valid requests. It never gives the model permission to invent operations or targets.

Use the course rubric: needs guidance means you can follow the solution; independent means you can complete the edit and write a useful test; advanced means you can diagnose an unfamiliar failure and compare alternatives using evidence.

## Continue the same engine

Add a preview showing exact arguments and relevant preconditions.

Keep this extension small and reversible. Commit your reviewed exercise diff on your learning branch before moving on. There is no capstone or separate final project.
