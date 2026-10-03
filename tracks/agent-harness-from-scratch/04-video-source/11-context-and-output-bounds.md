# Lesson 11: Context building and bounded outputs: narration script

This is a readable recording script, not a published recording. It is adapted
from the canonical lesson text; keep that lab open for exact source snippets,
commands and separate solutions. Caption future recordings and describe arrows
and state changes aloud. The examples use synthetic fixtures and an offline fake
provider. Do not run demonstrations on the source-only authoring Mac.

## Opening and purpose

Bound model input while retaining constraints and evidence relationships. Work in one growing `course_harness` package. The checkpoint selects cumulative behavior; it does not replace your source or wipe your exercise changes.

## Describe the diagram aloud

```text
durable history → select + bound + label → model-call context; original history retained
```

Text equivalent: durable history passes into select + bound + label passes into model-call context; original history retained. Read the flow from left to right; a branch represents a controller decision, not a command from untrusted text.

Read each arrow in order. Explain what enters the boundary, which trusted
component decides, and what evidence comes out. Pause before displaying code.

## Source walkthrough

Read [the implementation](../../src/course_harness/core.py) and locate `build_context` and history handling around `Engine.run`. Trace the successful path before editing.

Keep full recorded history separate from the selected request context. Bound individual excerpts and the aggregate request. Preserve host constraints and trust labels. If a tool result is truncated, show a marker and the amount omitted; do not present an incomplete result as full evidence. Keep call/result pairs valid during selection. Summaries are lossy model/data artifacts, not permission to replace host rules. Label character-derived token counts as estimates.

The continuing examples remain a disposable coding repository, synthetic SRE observations/service state, and local automation events/artifacts. Reuse the same engine rather than copying it into three domain-specific loops.

Open the lesson's minimal snippet. Narrate arguments, preconditions and return
values before typing the learner change. Keep the reference implementation intact
on its branch; learner tests should expose an unfinished TODO or missing guard.

## Demonstration and successful trace

Use the checkpoint commands from the lab on an approved execution host. Capture
actual terminal output; the following trace is a semantic narration, not a claim
that these exact event names are printed by every helper.

```text
history_recorded -> context_selected -> output_truncated -> model_called -> run_stopped(final)
```

At each transition, state what was requested, what trusted code decided, and what effect was observed. Engine trace events include `run_started`, `model_called`, `tool_requested`, `tool_completed`, and `run_stopped`; denial and approval paths add `tool_denied` or `approval_required`. A recorded final answer is not evidence an unrecorded side effect occurred.

Pause to inspect identifiers, stop reasons and effect counts. A fixture result
is evidence about this classroom mechanism, not production security or live
model quality.

## Controlled failure walkthrough

Trim away a tool request but retain its result, or omit a critical constraint. Use the acceptance test to expose the invalid context. Then fix selection by retaining/dropping related messages together.

Keep the failure fixture separate from the reference fixture. Record the first violated contract, the last completed event, and whether any side effect happened. Restore the controlled input before comparing a successful run.

Ask the learner to predict the last completed event, state and permitted effect
count before showing the result. Show the smallest violated boundary; restore the
controlled input before demonstrating success again.

## Learner pause and explanation

Feed a large toy file, SRE log, and automation event record. Implement an inspectable selection rule that keeps constraints and the most relevant bounded evidence. Add a test that a truncation marker remains in context and the original history remains unchanged.

Before opening the solution, write one learner test in a separate `test_learner_11.py`. Include one success assertion, one deliberate failure assertion, and one assertion about the boundary/effect. Choose state, identifiers, call counts, and stop reasons rather than incidental model wording.

Progressive hints:

1. Distinguish per-message from aggregate limits.
2. Select complete semantic groups rather than slicing messages blindly.
3. Test preservation of host constraints with a unique marker.

[Reference solution and test reasoning](../../solutions/11.md). Try the first hint and your own test before reading it.

Wait before revealing the separate worked solution. Then ask the learner to
explain the boundary in their own words:

What may a summary lose? Why is an estimate labeled? Where would you look for evidence omitted from a model request?

Plain-language explanation: Context is a view of history for one call. Its limits help control work, but omitted evidence remains a real uncertainty.

Use the course rubric: needs guidance means you can follow the solution; independent means you can complete the edit and write a useful test; advanced means you can diagnose an unfamiliar failure and compare alternatives using evidence.

## Continue the same engine

Compare two deterministic selection strategies against an outcome check.

Keep this extension small and reversible. Commit your reviewed exercise diff on your learning branch before moving on. There is no capstone or separate final project.
