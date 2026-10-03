# Lesson 1: Models, agents, harnesses, and fake responses: narration script

This is a readable recording script, not a published recording. It is adapted
from the canonical lesson text; keep that lab open for exact source snippets,
commands and separate solutions. Caption future recordings and describe arrows
and state changes aloud. The examples use synthetic fixtures and an offline fake
provider. Do not run demonstrations on the source-only authoring Mac.

## Opening and purpose

Explain a model's contribution and build a repeatable response boundary before permitting any action. Work in one growing `course_harness` package. The checkpoint selects cumulative behavior; it does not replace your source or wipe your exercise changes.

## Describe the diagram aloud

```text
fixture prompt → FakeProvider → Reply → controller termination
```

Text equivalent: fixture prompt passes into FakeProvider passes into Reply passes into controller termination. Read the flow from left to right; a branch represents a controller decision, not a command from untrusted text.

Read each arrow in order. Explain what enters the boundary, which trusted
component decides, and what evidence comes out. Pause before displaying code.

## Source walkthrough

Read [the implementation](../../src/course_harness/providers.py) and locate `Reply`, `ToolCall`, and `FakeProvider`. Trace the successful path before editing.

Read the reply types, then script one final response per scenario. Keep the prompt as input data and termination as a controller decision. A token is a model-specific text unit; context is the input supplied to one call. A fluent answer can be incorrect. The fake provider deliberately removes that uncertainty so you can reason about control flow. Add a fixture response without adding any HTTP path.

The continuing examples remain a disposable coding repository, synthetic SRE observations/service state, and local automation events/artifacts. Reuse the same engine rather than copying it into three domain-specific loops.

Open the lesson's minimal snippet. Narrate arguments, preconditions and return
values before typing the learner change. Keep the reference implementation intact
on its branch; learner tests should expose an unfinished TODO or missing guard.

## Demonstration and successful trace

Use the checkpoint commands from the lab on an approved execution host. Capture
actual terminal output; the following trace is a semantic narration, not a claim
that these exact event names are printed by every helper.

```text
run_started -> model_called -> run_stopped(final)
```

At each transition, state what was requested, what trusted code decided, and what effect was observed. Engine trace events include `run_started`, `model_called`, `tool_requested`, `tool_completed`, and `run_stopped`; denial and approval paths add `tool_denied` or `approval_required`. A recorded final answer is not evidence an unrecorded side effect occurred.

Pause to inspect identifiers, stop reasons and effect counts. A fixture result
is evidence about this classroom mechanism, not production security or live
model quality.

## Controlled failure walkthrough

Use a fixture whose response has the wrong shape, then try an exhausted script. Observe a clear provider/contract failure, not a fabricated successful response.

Keep the failure fixture separate from the reference fixture. Record the first violated contract, the last completed event, and whether any side effect happened. Restore the controlled input before comparing a successful run.

Ask the learner to predict the last completed event, state and permitted effect
count before showing the result. Show the smallest violated boundary; restore the
controlled input before demonstrating success again.

## Learner pause and explanation

Add a scripted reply describing the next read-only observation for each scenario: inspect a toy function, inspect service health, and inspect an event. Add a malformed fixture that requests a tool without a usable identifier. Predict whether parsing or the controller rejects it.

Before opening the solution, write one learner test in a separate `test_learner_01.py`. Include one success assertion, one deliberate failure assertion, and one assertion about the boundary/effect. Choose state, identifiers, call counts, and stop reasons rather than incidental model wording.

Progressive hints:

1. Construct the shared reply type instead of pretending all providers return the same raw JSON.
2. Give fake scripts stable call identifiers when they request tools.
3. A fixture containing 'I approve' still contains only model text.

[Reference solution and test reasoning](../../solutions/01.md). Try the first hint and your own test before reading it.

Wait before revealing the separate worked solution. Then ask the learner to
explain the boundary in their own words:

Which component owns the stop reason? Can generated text authorize a write? Which uncertainty does the fake remove, and which bugs can it still expose?

Plain-language explanation: The model suggests content. The harness records state, checks contracts, applies policy, and decides when a run stops.

Use the course rubric: needs guidance means you can follow the solution; independent means you can complete the edit and write a useful test; advanced means you can diagnose an unfamiliar failure and compare alternatives using evidence.

## Continue the same engine

Add a fake provider with two alternative scripts and compare traces without changing the engine.

Keep this extension small and reversible. Commit your reviewed exercise diff on your learning branch before moving on. There is no capstone or separate final project.
