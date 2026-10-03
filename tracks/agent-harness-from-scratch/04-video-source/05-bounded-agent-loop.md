# Lesson 5: The bounded agent loop: narration script

This is a readable recording script, not a published recording. It is adapted
from the canonical lesson text; keep that lab open for exact source snippets,
commands and separate solutions. Caption future recordings and describe arrows
and state changes aloud. The examples use synthetic fixtures and an offline fake
provider. Do not run demonstrations on the source-only authoring Mac.

## Opening and purpose

Connect model calls and tool results while keeping termination under controller control. Work in one growing `course_harness` package. The checkpoint selects cumulative behavior; it does not replace your source or wipe your exercise changes.

## Describe the diagram aloud

```text
model → validated tool request → tool result → model; controller budget guards every edge
```

Text equivalent: model passes into validated tool request passes into tool result passes into model; controller budget guards every edge. Read the flow from left to right; a branch represents a controller decision, not a command from untrusted text.

Read each arrow in order. Explain what enters the boundary, which trusted
component decides, and what evidence comes out. Pause before displaying code.

## Source walkthrough

Read [the implementation](../../src/course_harness/core.py) and locate `Engine.run`, `Limits`, and `RunResult`. Trace the successful path before editing.

Read one iteration of `Engine.run` aloud. Before a model call, check cancellation and remaining budgets. After a reply, distinguish final text from tool calls, validate unique identifiers, dispatch sequentially, and append matching results. A model that says 'keep going' cannot extend limits. Count failed and denied attempts according to the documented budget rules so retries cannot become free work.

The continuing examples remain a disposable coding repository, synthetic SRE observations/service state, and local automation events/artifacts. Reuse the same engine rather than copying it into three domain-specific loops.

Open the lesson's minimal snippet. Narrate arguments, preconditions and return
values before typing the learner change. Keep the reference implementation intact
on its branch; learner tests should expose an unfinished TODO or missing guard.

## Demonstration and successful trace

Use the checkpoint commands from the lab on an approved execution host. Capture
actual terminal output; the following trace is a semantic narration, not a claim
that these exact event names are printed by every helper.

```text
run_started -> model_called -> tool_requested -> tool_completed -> model_called -> run_stopped(final)
```

At each transition, state what was requested, what trusted code decided, and what effect was observed. Engine trace events include `run_started`, `model_called`, `tool_requested`, `tool_completed`, and `run_stopped`; denial and approval paths add `tool_denied` or `approval_required`. A recorded final answer is not evidence an unrecorded side effect occurred.

Pause to inspect identifiers, stop reasons and effect counts. A fixture result
is evidence about this classroom mechanism, not production security or live
model quality.

## Controlled failure walkthrough

Return duplicate call identifiers or request more calls than the call limit. Check rejection/stop before the extra handler executes. An unmatched result must not be presented as evidence for another request.

Keep the failure fixture separate from the reference fixture. Record the first violated contract, the last completed event, and whether any side effect happened. Restore the controlled input before comparing a successful run.

Ask the learner to predict the last completed event, state and permitted effect
count before showing the result. Show the smallest violated boundary; restore the
controlled input before demonstrating success again.

## Learner pause and explanation

Script two read-only calls then a final response for each scenario: read/list toy files; health/log evidence; event/plan inspection. Add a fake script that requests calls forever. Set a small step limit and verify a bounded stop.

Before opening the solution, write one learner test in a separate `test_learner_05.py`. Include one success assertion, one deliberate failure assertion, and one assertion about the boundary/effect. Choose state, identifiers, call counts, and stop reasons rather than incidental model wording.

Progressive hints:

1. Use a fresh scripted provider in every test.
2. Assert identifiers on recorded results, not just list length.
3. Place the limit check before work, then record the reason once.

[Reference solution and test reasoning](../../solutions/05.md). Try the first hint and your own test before reading it.

Wait before revealing the separate worked solution. Then ask the learner to
explain the boundary in their own words:

Why can the provider not decide its own retry count? Does a tool error end every run? Which component chooses the stop reason?

Plain-language explanation: The loop is ordinary control flow: request, validate, execute only permitted work, feed back results, stop for a recorded reason.

Use the course rubric: needs guidance means you can follow the solution; independent means you can complete the edit and write a useful test; advanced means you can diagnose an unfamiliar failure and compare alternatives using evidence.

## Continue the same engine

Create a recoverable tool error followed by a final answer and inspect the changed trace.

Keep this extension small and reversible. Commit your reviewed exercise diff on your learning branch before moving on. There is no capstone or separate final project.
