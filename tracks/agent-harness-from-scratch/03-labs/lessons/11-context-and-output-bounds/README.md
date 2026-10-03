# Lesson 11: Context building and bounded outputs

Lesson 10. Read [setup](../../../02-lab-book/setup.md) before running commands.

## What we are building

Bound model input while retaining constraints and evidence relationships. Work in one growing `course_harness` package. The checkpoint selects cumulative behavior; it does not replace your source or wipe your exercise changes.

## Picture the flow

```text
durable history → select + bound + label → model-call context; original history retained
```

Text equivalent: durable history passes into select + bound + label passes into model-call context; original history retained. Read the flow from left to right; a branch represents a controller decision, not a command from untrusted text.

## Read first, then make one small change

Read [the implementation](../../src/course_harness/core.py) and locate `build_context` and history handling around `Engine.run`. Trace the successful path before editing.

Keep full recorded history separate from the selected request context. Bound individual excerpts and the aggregate request. Preserve host constraints and trust labels. If a tool result is truncated, show a marker and the amount omitted; do not present an incomplete result as full evidence. Keep call/result pairs valid during selection. Summaries are lossy model/data artifacts, not permission to replace host rules. Label character-derived token counts as estimates.

The continuing examples remain a disposable coding repository, synthetic SRE observations/service state, and local automation events/artifacts. Reuse the same engine rather than copying it into three domain-specific loops.

## Minimal code to inspect and extend

Construct a model-call view without altering stored history.

```python
from course_harness.core import build_context
history = [{"role": "system", "content": "host constraints"},
           {"role": "user", "content": "x" * 9000},
           {"role": "user", "content": "latest observation"}]
context = build_context(history, max_chars=512)
assert any("TRUNCATED" in m["content"] for m in context)
assert history[1]["content"] == "x" * 9000
```

Concrete exercise delta: Extend the fixture selection strategy with a bounded excerpt and provenance/omission record. Locate grouping in `build_context` and preserve full request/result groups. Write a case that would fail if selection orphaned a tool result.

The complete test fragment lives in the separate solution. Keep your new helper/test on your learning branch; baseline checkpoints remain available while you work.

## Run a checkpoint

From `tracks/agent-harness-from-scratch/03-labs`, with the environment installed as in setup:

```sh
python -m course_harness checkpoint 11 --scenario coding
python -m course_harness checkpoint 11 --scenario sre
python -m course_harness checkpoint 11 --scenario automation
pytest -q tests -k lesson_11
```

These are learner/approved-worker commands. Do not execute them on the source-only authoring Mac. Expected CLI output is JSON with `lesson`, `scenario`, `status`, `stop_reason`, `trace`, and `checks`. Inspect the check values and exit status; absence of selected tests is not a pass.

Selected context stays under its declared bound, retains essential constraints, marks missing evidence, and does not mutate durable history. The walkthrough below explains meaningful event order; helper/fixture events may be represented inside check records rather than as literal CLI event names.

Exact baseline expectation: Expect final termination and `truncation_visible: true`; original stored history remains unchanged.

## Read a successful trace

```text
history_recorded -> context_selected -> output_truncated -> model_called -> run_stopped(final)
```

At each transition, state what was requested, what trusted code decided, and what effect was observed. Engine trace events include `run_started`, `model_called`, `tool_requested`, `tool_completed`, and `run_stopped`; denial and approval paths add `tool_denied` or `approval_required`. A recorded final answer is not evidence an unrecorded side effect occurred.

## Break it on purpose

Trim away a tool request but retain its result, or omit a critical constraint. Use the acceptance test to expose the invalid context. Then fix selection by retaining/dropping related messages together.

Keep the failure fixture separate from the reference fixture. Record the first violated contract, the last completed event, and whether any side effect happened. Restore the controlled input before comparing a successful run.

## Your exercise

Feed a large toy file, SRE log, and automation event record. Implement an inspectable selection rule that keeps constraints and the most relevant bounded evidence. Add a test that a truncation marker remains in context and the original history remains unchanged.

Before opening the solution, write one learner test in a separate `test_learner_11.py`. Include one success assertion, one deliberate failure assertion, and one assertion about the boundary/effect. Choose state, identifiers, call counts, and stop reasons rather than incidental model wording.

Progressive hints:

1. Distinguish per-message from aggregate limits.
2. Select complete semantic groups rather than slicing messages blindly.
3. Test preservation of host constraints with a unique marker.

[Reference solution and test reasoning](../../solutions/11.md). Try the first hint and your own test before reading it.

## Acceptance checks

Bounded requests; unchanged history; constraints retained; truncation visible; call/result relationships valid. Add a result exactly at the size boundary.

The selected delivered checks are a baseline. Your extra test should fail when your exercise change is removed and pass when it is restored. Use controlled fixtures and injected time; required checks need no network or real infrastructure. Record unimplemented or unvalidated assertions honestly.

## Explain it back

What may a summary lose? Why is an estimate labeled? Where would you look for evidence omitted from a model request?

Plain-language explanation: Context is a view of history for one call. Its limits help control work, but omitted evidence remains a real uncertainty.

Use the course rubric: needs guidance means you can follow the solution; independent means you can complete the edit and write a useful test; advanced means you can diagnose an unfamiliar failure and compare alternatives using evidence.

## Optional next extension

Compare two deterministic selection strategies against an outcome check.

Keep this extension small and reversible. Commit your reviewed exercise diff on your learning branch before moving on. There is no capstone or separate final project.

## Reviewed boundary clarification

Current-turn retention: prune complete old turns only. Keep the current user goal and its entire recent tool exchange together. If they cannot fit alongside trusted constraints, the controller stops with `context_limit` before calling the provider. It must not silently send only a truncation marker.
