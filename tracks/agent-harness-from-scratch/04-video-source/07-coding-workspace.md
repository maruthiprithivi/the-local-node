# Lesson 7: Coding tools in a disposable workspace: narration script

This is a readable recording script, not a published recording. It is adapted
from the canonical lesson text; keep that lab open for exact source snippets,
commands and separate solutions. Caption future recordings and describe arrows
and state changes aloud. The examples use synthetic fixtures and an offline fake
provider. Do not run demonstrations on the source-only authoring Mac.

## Opening and purpose

Read, preview, and apply one approved edit with visible preconditions. Work in one growing `course_harness` package. The checkpoint selects cumulative behavior; it does not replace your source or wipe your exercise changes.

## Describe the diagram aloud

```text
toy repository → bounded read → proposed diff + digest → approval → patch → verify
```

Text equivalent: toy repository passes into bounded read passes into proposed diff + digest passes into approval passes into patch passes into verify. Read the flow from left to right; a branch represents a controller decision, not a command from untrusted text.

Read each arrow in order. Explain what enters the boundary, which trusted
component decides, and what evidence comes out. Pause before displaying code.

## Source walkthrough

Read [the implementation](../../src/course_harness/tools.py) and locate `FixtureWorld`, `scenario_tools`, and coding handlers. Trace the successful path before editing.

Start by reading a toy function and capturing the content digest. Build a small proposed edit, display the diff, bind approval to the intended path and expected old content, then apply it. Reject absolute/outside paths and symlink traversal under the documented policy. Read/write with explicit encoding and size limits. Keep a recoverable original or recorded change. Describe a concurrent-write race as a residual risk rather than claiming path resolution is isolation.

The continuing examples remain a disposable coding repository, synthetic SRE observations/service state, and local automation events/artifacts. Reuse the same engine rather than copying it into three domain-specific loops.

Open the lesson's minimal snippet. Narrate arguments, preconditions and return
values before typing the learner change. Keep the reference implementation intact
on its branch; learner tests should expose an unfinished TODO or missing guard.

## Demonstration and successful trace

Use the checkpoint commands from the lab on an approved execution host. Capture
actual terminal output; the following trace is a semantic narration, not a claim
that these exact event names are printed by every helper.

```text
tool_requested(read) -> tool_completed -> tool_requested(patch) -> approval_required -> tool_completed -> verification
```

At each transition, state what was requested, what trusted code decided, and what effect was observed. Engine trace events include `run_started`, `model_called`, `tool_requested`, `tool_completed`, and `run_stopped`; denial and approval paths add `tool_denied` or `approval_required`. A recorded final answer is not evidence an unrecorded side effect occurred.

Pause to inspect identifiers, stop reasons and effect counts. A fixture result
is evidence about this classroom mechanism, not production security or live
model quality.

## Controlled failure walkthrough

After preview, alter the toy file before applying the approved proposal. The stale-content check must fail and preserve the changed file rather than overwrite it.

Keep the failure fixture separate from the reference fixture. Record the first violated contract, the last completed event, and whether any side effect happened. Restore the controlled input before comparing a successful run.

Ask the learner to predict the last completed event, state and permitted effect
count before showing the result. Show the smallest violated boundary; restore the
controlled input before demonstrating success again.

## Learner pause and explanation

Correct a small arithmetic bug in a copied toy repository. Show the original, proposed diff, and new content. Add tests for a stale digest, `../` traversal, and a symlink aimed outside the fixture root. Work only in disposable data.

Before opening the solution, write one learner test in a separate `test_learner_07.py`. Include one success assertion, one deliberate failure assertion, and one assertion about the boundary/effect. Choose state, identifiers, call counts, and stop reasons rather than incidental model wording.

Progressive hints:

1. Approve the proposed content and precondition, not merely a path.
2. Compare file bytes before and after rejected attempts.
3. Keep temporary external-target fixtures separate from the workspace.

[Reference solution and test reasoning](../../solutions/07.md). Try the first hint and your own test before reading it.

Wait before revealing the separate worked solution. Then ask the learner to
explain the boundary in their own words:

Why is a test file untrusted code? What race remains after a path check? How does the content digest affect approval?

Plain-language explanation: A safe classroom patch is a specific proposed change to disposable content with checked preconditions. It is not permission to edit any repository.

Use the course rubric: needs guidance means you can follow the solution; independent means you can complete the edit and write a useful test; advanced means you can diagnose an unfamiliar failure and compare alternatives using evidence.

## Continue the same engine

Test rejection of invalid UTF-8 with a clear encoding error.

Keep this extension small and reversible. Commit your reviewed exercise diff on your learning branch before moving on. There is no capstone or separate final project.
