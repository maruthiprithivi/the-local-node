# Lesson 13: Durable state and reconciliation: narration script

This is a readable recording script, not a published recording. It is adapted
from the canonical lesson text; keep that lab open for exact source snippets,
commands and separate solutions. Caption future recordings and describe arrows
and state changes aloud. The examples use synthetic fixtures and an offline fake
provider. Do not run demonstrations on the source-only authoring Mac.

## Opening and purpose

Recover after interruption without inventing certainty or repeating effects blindly. Work in one growing `course_harness` package. The checkpoint selects cumulative behavior; it does not replace your source or wipe your exercise changes.

## Describe the diagram aloud

```text
requested → approved → started → completed; crash after started → uncertain → observe → resolve
```

Text equivalent: requested passes into approved passes into started passes into completed; crash after started passes into uncertain passes into observe passes into resolve. Read the flow from left to right; a branch represents a controller decision, not a command from untrusted text.

Read each arrow in order. Explain what enters the boundary, which trusted
component decides, and what evidence comes out. Pause before displaying code.

## Source walkthrough

Read [the implementation](../../src/course_harness/persistence.py) and locate persisted state schema, action identity/transitions, and reconciliation. Trace the successful path before editing.

Use versioned SQLite state with stable run/event/action identifiers. Record intention and relevant approval before execution, started before an effect, and completed only after its observed result. A crash between effect and completion record creates ambiguity. Replaying a recorded result feeds evidence back into context; re-executing an action makes a new effect. Preserve remaining limits and scope on restart. Reject incompatible schema/state instead of treating it as empty.

The continuing examples remain a disposable coding repository, synthetic SRE observations/service state, and local automation events/artifacts. Reuse the same engine rather than copying it into three domain-specific loops.

Open the lesson's minimal snippet. Narrate arguments, preconditions and return
values before typing the learner change. Keep the reference implementation intact
on its branch; learner tests should expose an unfinished TODO or missing guard.

## Demonstration and successful trace

Use the checkpoint commands from the lab on an approved execution host. Capture
actual terminal output; the following trace is a semantic narration, not a claim
that these exact event names are printed by every helper.

```text
action_requested -> action_approved -> action_started -> [crash] -> recovery -> action_uncertain -> reconciled
```

At each transition, state what was requested, what trusted code decided, and what effect was observed. Engine trace events include `run_started`, `model_called`, `tool_requested`, `tool_completed`, and `run_stopped`; denial and approval paths add `tool_denied` or `approval_required`. A recorded final answer is not evidence an unrecorded side effect occurred.

Pause to inspect identifiers, stop reasons and effect counts. A fixture result
is evidence about this classroom mechanism, not production security or live
model quality.

## Controlled failure walkthrough

Tamper a persisted version or reopen a started action without confirming its effect. The first must fail clearly; the second must remain inspectable and uncertain rather than silently repeat.

Keep the failure fixture separate from the reference fixture. Record the first violated contract, the last completed event, and whether any side effect happened. Restore the controlled input before comparing a successful run.

Ask the learner to predict the last completed event, state and permitted effect
count before showing the result. Show the smallest violated boundary; restore the
controlled input before demonstrating success again.

## Learner pause and explanation

Simulate a crash after the toy patch, synthetic restart, or artifact mutation but before the completion record. Reopen the database, inspect the real fixture postcondition, and resolve the action as completed or still uncertain. Add a test that restart does not automatically invoke the effect handler again.

Before opening the solution, write one learner test in a separate `test_learner_13.py`. Include one success assertion, one deliberate failure assertion, and one assertion about the boundary/effect. Choose state, identifiers, call counts, and stop reasons rather than incidental model wording.

Progressive hints:

1. Use one temporary database per test.
2. Simulate the crash at a deterministic boundary, not by randomly killing a process.
3. Compare expected postconditions before deciding completion.

[Reference solution and test reasoning](../../solutions/13.md). Try the first hint and your own test before reading it.

Wait before revealing the separate worked solution. Then ask the learner to
explain the boundary in their own words:

Why does SQLite not guarantee every external effect exactly once? What can a persisted 'started' row prove? Who may resolve an ambiguous effect?

Plain-language explanation: Durable records preserve what the harness knew. Reconciliation checks what the world actually contains when a record is incomplete.

Use the course rubric: needs guidance means you can follow the solution; independent means you can complete the edit and write a useful test; advanced means you can diagnose an unfamiliar failure and compare alternatives using evidence.

## Continue the same engine

Represent an unknown outcome explicitly when observation cannot determine completion.

Keep this extension small and reversible. Commit your reviewed exercise diff on your learning branch before moving on. There is no capstone or separate final project.
