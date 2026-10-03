# Lesson 4: Tool contracts and explicit dispatch: narration script

This is a readable recording script, not a published recording. It is adapted
from the canonical lesson text; keep that lab open for exact source snippets,
commands and separate solutions. Caption future recordings and describe arrows
and state changes aloud. The examples use synthetic fixtures and an offline fake
provider. Do not run demonstrations on the source-only authoring Mac.

## Opening and purpose

Validate a structured request before any handler executes. Work in one growing `course_harness` package. The checkpoint selects cumulative behavior; it does not replace your source or wipe your exercise changes.

## Describe the diagram aloud

```text
ToolCall → named contract validation → registry lookup → handler → structured result
```

Text equivalent: ToolCall passes into named contract validation passes into registry lookup passes into handler passes into structured result. Read the flow from left to right; a branch represents a controller decision, not a command from untrusted text.

Read each arrow in order. Explain what enters the boundary, which trusted
component decides, and what evidence comes out. Pause before displaying code.

## Source walkthrough

Read [the implementation](../../src/course_harness/tools.py) and locate `Tool`, `Registry`, and tool argument validators. Trace the successful path before editing.

Add a pure tool before a file operation. The registry maps names to explicit handlers; it never evaluates generated Python. Validate required fields, extra fields, types, and size bounds. Python booleans are a subtle case: `bool` is a subclass of `int`, so decide deliberately whether a boolean satisfies a numeric field. Return structured errors that identify the boundary without dumping huge inputs. Keep tool result shape independent of conversational prose.

The continuing examples remain a disposable coding repository, synthetic SRE observations/service state, and local automation events/artifacts. Reuse the same engine rather than copying it into three domain-specific loops.

Open the lesson's minimal snippet. Narrate arguments, preconditions and return
values before typing the learner change. Keep the reference implementation intact
on its branch; learner tests should expose an unfinished TODO or missing guard.

## Demonstration and successful trace

Use the checkpoint commands from the lab on an approved execution host. Capture
actual terminal output; the following trace is a semantic narration, not a claim
that these exact event names are printed by every helper.

```text
tool_requested -> arguments_validated -> handler_selected -> tool_completed
```

At each transition, state what was requested, what trusted code decided, and what effect was observed. Engine trace events include `run_started`, `model_called`, `tool_requested`, `tool_completed`, and `run_stopped`; denial and approval paths add `tool_denied` or `approval_required`. A recorded final answer is not evidence an unrecorded side effect occurred.

Pause to inspect identifiers, stop reasons and effect counts. A fixture result
is evidence about this classroom mechanism, not production security or live
model quality.

## Controlled failure walkthrough

Request an unknown tool, a missing required field, and a numeric string where an integer is required. The registry should reject each before calling a handler.

Keep the failure fixture separate from the reference fixture. Record the first violated contract, the last completed event, and whether any side effect happened. Restore the controlled input before comparing a successful run.

Ask the learner to predict the last completed event, state and permitted effect
count before showing the result. Show the smallest violated boundary; restore the
controlled input before demonstrating success again.

## Learner pause and explanation

Add `count_records` over a supplied fixture list with a maximum record count. Define the exact allowed arguments and result. Test valid empty/non-empty input, an unexpected field, and an oversized list. Use a handler spy to prove rejected requests never execute.

Before opening the solution, write one learner test in a separate `test_learner_04.py`. Include one success assertion, one deliberate failure assertion, and one assertion about the boundary/effect. Choose state, identifiers, call counts, and stop reasons rather than incidental model wording.

Progressive hints:

1. Write the allowed argument names before implementing the handler.
2. Validate limits before allocating or producing an unbounded result.
3. A handler counter is stronger evidence than checking only error wording.

[Reference solution and test reasoning](../../solutions/04.md). Try the first hint and your own test before reading it.

Wait before revealing the separate worked solution. Then ask the learner to
explain the boundary in their own words:

Why is a natural-language description insufficient? What is the difference between validation and policy? Why not use `eval` for a clever tool?

Plain-language explanation: Contracts make operations predictable. They establish shape and bounds; policy will separately establish whether an otherwise valid operation is permitted.

Use the course rubric: needs guidance means you can follow the solution; independent means you can complete the edit and write a useful test; advanced means you can diagnose an unfamiliar failure and compare alternatives using evidence.

## Continue the same engine

Add a structured error code and assert it without depending on full prose.

Keep this extension small and reversible. Commit your reviewed exercise diff on your learning branch before moving on. There is no capstone or separate final project.
