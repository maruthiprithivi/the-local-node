# Lesson 7: Coding tools in a disposable workspace

Lesson 6. Read [setup](../../../02-lab-book/setup.md) before running commands.

## What we are building

Read, preview, and apply one approved edit with visible preconditions. Work in one growing `course_harness` package. The checkpoint selects cumulative behavior; it does not replace your source or wipe your exercise changes.

## Picture the flow

```text
toy repository → bounded read → proposed diff + digest → approval → patch → verify
```

Text equivalent: toy repository passes into bounded read passes into proposed diff + digest passes into approval passes into patch passes into verify. Read the flow from left to right; a branch represents a controller decision, not a command from untrusted text.

## Read first, then make one small change

Read [the implementation](../../src/course_harness/tools.py) and locate `FixtureWorld`, `scenario_tools`, and coding handlers. Trace the successful path before editing.

Start by reading a toy function and capturing the content digest. Build a small proposed edit, display the diff, bind approval to the intended path and expected old content, then apply it. Reject absolute/outside paths and symlink traversal under the documented policy. Read/write with explicit encoding and size limits. Keep a recoverable original or recorded change. Describe a concurrent-write race as a residual risk rather than claiming path resolution is isolation.

The continuing examples remain a disposable coding repository, synthetic SRE observations/service state, and local automation events/artifacts. Reuse the same engine rather than copying it into three domain-specific loops.

## Minimal code to inspect and extend

The file helper checks content/path preconditions; an authorized executor must still perform policy approval before calling it.

```python
from tempfile import TemporaryDirectory
from pathlib import Path
from course_harness.tools import Workspace
with TemporaryDirectory() as root:
    path = Path(root) / "calculator.py"
    path.write_text("return a - b\n", encoding="utf-8")
    workspace = Workspace(root)
    diff = workspace.preview("calculator.py", "return a - b\n", "return a + b\n")
    assert "+return a + b" in diff
```

Concrete exercise delta: Write a small trusted executor wrapper that binds the path/expected/replacement to `Policy` before calling `Workspace.apply`. A direct helper invocation bypasses policy and is suitable only for the isolated helper test. Add stale/symlink/outside tests around `Workspace.path` and `preview`.

The complete test fragment lives in the separate solution. Keep your new helper/test on your learning branch; baseline checkpoints remain available while you work.

## Run a checkpoint

From `tracks/agent-harness-from-scratch/03-labs`, with the environment installed as in setup:

```sh
python -m course_harness checkpoint 7 --scenario coding
python -m course_harness checkpoint 7 --scenario sre
python -m course_harness checkpoint 7 --scenario automation
pytest -q tests -k lesson_07
```

These are learner/approved-worker commands. Do not execute them on the source-only authoring Mac. Expected CLI output is JSON with `lesson`, `scenario`, `status`, `stop_reason`, `trace`, and `checks`. Inspect the check values and exit status; absence of selected tests is not a pass.

Exactly the intended toy file changes once; outside, stale, and symlink attempts produce errors without touching their targets. The walkthrough below explains meaningful event order; helper/fixture events may be represented inside check records rather than as literal CLI event names.

Exact baseline expectation: Coding/automation scenario runs stop as `approval_required` at the requested write. The separate `Workspace` helper check exercises a local patch and stale rejection; it is not a continuation of that paused engine run. SRE remains read-only at this point.

## Read a successful trace

```text
phase 1: tool_requested(read) -> tool_completed -> tool_requested(patch) -> approval_required -> run_stopped
phase 2: review exact proposal -> approve -> trusted helper invocation -> verify changed bytes
```

At each transition, state what was requested, what trusted code decided, and what effect was observed. Engine trace events include `run_started`, `model_called`, `tool_requested`, `tool_completed`, and `run_stopped`; denial and approval paths add `tool_denied` or `approval_required`. A recorded final answer is not evidence an unrecorded side effect occurred.

## Break it on purpose

After preview, alter the toy file before applying the approved proposal. The stale-content check must fail and preserve the changed file rather than overwrite it.

Keep the failure fixture separate from the reference fixture. Record the first violated contract, the last completed event, and whether any side effect happened. Restore the controlled input before comparing a successful run.

## Your exercise

Correct a small arithmetic bug in a copied toy repository. Show the original, proposed diff, and new content. Add tests for a stale digest, `../` traversal, and a symlink aimed outside the fixture root. Work only in disposable data.

Before opening the solution, write one learner test in a separate `test_learner_07.py`. Include one success assertion, one deliberate failure assertion, and one assertion about the boundary/effect. Choose state, identifiers, call counts, and stop reasons rather than incidental model wording.

Progressive hints:

1. Approve the proposed content and precondition, not merely a path.
2. Compare file bytes before and after rejected attempts.
3. Keep temporary external-target fixtures separate from the workspace.

[Reference solution and test reasoning](../../solutions/07.md). Try the first hint and your own test before reading it.

## Acceptance checks

Intended edit; no unrelated file changes; stale/outside rejection; symlink rejection; original recoverability. Add an oversized-read test.

The selected delivered checks are a baseline. Your extra test should fail when your exercise change is removed and pass when it is restored. Use controlled fixtures and injected time; required checks need no network or real infrastructure. Record unimplemented or unvalidated assertions honestly.

## Explain it back

Why is a test file untrusted code? What race remains after a path check? How does the content digest affect approval?

Plain-language explanation: A safe classroom patch is a specific proposed change to disposable content with checked preconditions. It is not permission to edit any repository.

Use the course rubric: needs guidance means you can follow the solution; independent means you can complete the edit and write a useful test; advanced means you can diagnose an unfamiliar failure and compare alternatives using evidence.

## Optional next extension

Test rejection of invalid UTF-8 with a clear encoding error.

Keep this extension small and reversible. Commit your reviewed exercise diff on your learning branch before moving on. There is no capstone or separate final project.
