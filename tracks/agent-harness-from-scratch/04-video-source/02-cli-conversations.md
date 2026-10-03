# Lesson 2: CLI conversations and visible state: narration script

This is a readable recording script, not a published recording. It is adapted
from the canonical lesson text; keep that lab open for exact source snippets,
commands and separate solutions. Caption future recordings and describe arrows
and state changes aloud. The examples use synthetic fixtures and an offline fake
provider. Do not run demonstrations on the source-only authoring Mac.

## Opening and purpose

Separate terminal input, ordered conversation history, and model execution. Work in one growing `course_harness` package. The checkpoint selects cumulative behavior; it does not replace your source or wipe your exercise changes.

## Describe the diagram aloud

```text
terminal command → session history → one bounded run → displayed result
```

Text equivalent: terminal command passes into session history passes into one bounded run passes into displayed result. Read the flow from left to right; a branch represents a controller decision, not a command from untrusted text.

Read each arrow in order. Explain what enters the boundary, which trusted
component decides, and what evidence comes out. Pause before displaying code.

## Source walkthrough

Read [the implementation](../../src/course_harness/__main__.py) and locate the CLI command handlers and the ordered message dictionaries in `core.py`. Trace the successful path before editing.

Trace how the CLI obtains input and passes it to the engine. Add a small session wrapper with help/reset/exit operations. A turn is one model interaction; a run is a bounded task attempt; a session owns ordered history across runs. Reject oversized input before appending it. Reset clears the documented conversation history, not permissions or durable state. Handle EOF and KeyboardInterrupt at the interface boundary.

The continuing examples remain a disposable coding repository, synthetic SRE observations/service state, and local automation events/artifacts. Reuse the same engine rather than copying it into three domain-specific loops.

Open the lesson's minimal snippet. Narrate arguments, preconditions and return
values before typing the learner change. Keep the reference implementation intact
on its branch; learner tests should expose an unfinished TODO or missing guard.

## Demonstration and successful trace

Use the checkpoint commands from the lab on an approved execution host. Capture
actual terminal output; the following trace is a semantic narration, not a claim
that these exact event names are printed by every helper.

```text
input_received -> message_appended -> model_called -> reply_appended -> reset -> input_closed
```

At each transition, state what was requested, what trusted code decided, and what effect was observed. Engine trace events include `run_started`, `model_called`, `tool_requested`, `tool_completed`, and `run_stopped`; denial and approval paths add `tool_denied` or `approval_required`. A recorded final answer is not evidence an unrecorded side effect occurred.

Pause to inspect identifiers, stop reasons and effect counts. A fixture result
is evidence about this classroom mechanism, not production security or live
model quality.

## Controlled failure walkthrough

Feed an input above the size limit, then EOF. No oversized message should enter history; EOF should exit cleanly rather than spin and repeatedly call the provider.

Keep the failure fixture separate from the reference fixture. Record the first violated contract, the last completed event, and whether any side effect happened. Restore the controlled input before comparing a successful run.

Ask the learner to predict the last completed event, state and permitted effect
count before showing the result. Show the smallest violated boundary; restore the
controlled input before demonstrating success again.

## Learner pause and explanation

Create a scripted two-turn conversation for coding, SRE, and automation. Add a reset command that clears history without replacing the provider or policy. Test reset between the two turns and compare the messages seen by a recording fake.

Before opening the solution, write one learner test in a separate `test_learner_02.py`. Include one success assertion, one deliberate failure assertion, and one assertion about the boundary/effect. Choose state, identifiers, call counts, and stop reasons rather than incidental model wording.

Progressive hints:

1. Put command parsing before ordinary message handling.
2. Keep history in an explicit list, not a global variable.
3. Inspect the recording fake's request list to test ordering without matching terminal decoration.

[Reference solution and test reasoning](../../solutions/02.md). Try the first hint and your own test before reading it.

Wait before revealing the separate worked solution. Then ask the learner to
explain the boundary in their own words:

Why should reset not erase policy or approval state? Where should Ctrl-C be translated into a clean interface exit? Can one session contain several runs?

Plain-language explanation: The CLI is an interface. It should translate user input into well-defined operations rather than contain provider or permission logic.

Use the course rubric: needs guidance means you can follow the solution; independent means you can complete the edit and write a useful test; advanced means you can diagnose an unfamiliar failure and compare alternatives using evidence.

## Continue the same engine

Add a transcript command that redacts secrets and preserves trust labels.

Keep this extension small and reversible. Commit your reviewed exercise diff on your learning branch before moving on. There is no capstone or separate final project.
