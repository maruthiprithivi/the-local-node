# Lesson 12: Retries, deadlines, cancellation, and budgets: narration script

This is a readable recording script, not a published recording. It is adapted
from the canonical lesson text; keep that lab open for exact source snippets,
commands and separate solutions. Caption future recordings and describe arrows
and state changes aloud. The examples use synthetic fixtures and an offline fake
provider. Do not run demonstrations on the source-only authoring Mac.

## Opening and purpose

Recover from transient failures with bounded work and honest uncertainty. Work in one growing `course_harness` package. The checkpoint selects cumulative behavior; it does not replace your source or wipe your exercise changes.

## Describe the diagram aloud

```text
attempt → classify error → terminal stop OR capped delay → recheck stop/deadline → attempt
```

Text equivalent: attempt passes into classify error passes into terminal stop OR capped delay passes into recheck stop/deadline passes into attempt. Read the flow from left to right; a branch represents a controller decision, not a command from untrusted text.

Read each arrow in order. Explain what enters the boundary, which trusted
component decides, and what evidence comes out. Pause before displaying code.

## Source walkthrough

Read [the implementation](../../src/course_harness/core.py) and locate `retry_call`, `Limits`, cancellation, and deadline checks. Trace the successful path before editing.

Classify terminal authentication/contract failures separately from retryable rate limits or transient transport errors. Cap attempts and delay; inject clock, sleeper, and deterministic jitter so tests need no real waiting. Bound each request and the entire run. Check cancellation before new work and during waiting. Share budgets across retry attempts. A timeout after a side effect means 'possibly completed,' not 'safe to repeat.' Retry model transport differently from uncertain mutations.

The continuing examples remain a disposable coding repository, synthetic SRE observations/service state, and local automation events/artifacts. Reuse the same engine rather than copying it into three domain-specific loops.

Open the lesson's minimal snippet. Narrate arguments, preconditions and return
values before typing the learner change. Keep the reference implementation intact
on its branch; learner tests should expose an unfinished TODO or missing guard.

## Demonstration and successful trace

Use the checkpoint commands from the lab on an approved execution host. Capture
actual terminal output; the following trace is a semantic narration, not a claim
that these exact event names are printed by every helper.

```text
model_called -> retryable_error -> bounded_backoff -> model_called -> final; cancelled -> run_stopped(cancelled)
```

At each transition, state what was requested, what trusted code decided, and what effect was observed. Engine trace events include `run_started`, `model_called`, `tool_requested`, `tool_completed`, and `run_stopped`; denial and approval paths add `tool_denied` or `approval_required`. A recorded final answer is not evidence an unrecorded side effect occurred.

Pause to inspect identifiers, stop reasons and effect counts. A fixture result
is evidence about this classroom mechanism, not production security or live
model quality.

## Controlled failure walkthrough

A cancelled backoff should not trigger its next call. A terminal error should produce only one attempt. A continuously retryable error must reach the ceiling/deadline.

Keep the failure fixture separate from the reference fixture. Record the first violated contract, the last completed event, and whether any side effect happened. Restore the controlled input before comparing a successful run.

Ask the learner to predict the last completed event, state and permitted effect
count before showing the result. Show the smallest violated boundary; restore the
controlled input before demonstrating success again.

## Learner pause and explanation

Script a transient failure then success, repeated rate limiting, terminal authentication failure, and cancellation during backoff. Add a synthetic effect that mutates before timing out; confirm it enters uncertainty rather than automatically executing twice.

Before opening the solution, write one learner test in a separate `test_learner_12.py`. Include one success assertion, one deliberate failure assertion, and one assertion about the boundary/effect. Choose state, identifiers, call counts, and stop reasons rather than incidental model wording.

Progressive hints:

1. A fake sleeper advances fake time; it need not sleep.
2. Place stop checks on both sides of a delay.
3. Do not give retries a fresh run budget.

[Reference solution and test reasoning](../../solutions/12.md). Try the first hint and your own test before reading it.

Wait before revealing the separate worked solution. Then ask the learner to
explain the boundary in their own words:

How does deadline differ from timeout? Why can a server finish after the client timed out? Which retries are safe without observing state?

Plain-language explanation: Reliability means bounded recovery and truthful state, not trying forever or assuming a timeout erased an effect.

Use the course rubric: needs guidance means you can follow the solution; independent means you can complete the edit and write a useful test; advanced means you can diagnose an unfamiliar failure and compare alternatives using evidence.

## Continue the same engine

Honor a bounded retry-after hint using the same deadline and fake clock.

Keep this extension small and reversible. Commit your reviewed exercise diff on your learning branch before moving on. There is no capstone or separate final project.
