# Optional lesson 0: Foundations without hidden prerequisites

None. This is optional; skip only if you can already write and test a small Python function.

## What we are building

Use the terminal, small Python functions, JSON, Git, and tests without guessing what each command does. Work in one growing `course_harness` package. The checkpoint selects cumulative behavior; it does not replace your source or wipe your exercise changes.

## Picture the flow

```text
JSON file → validate a task list → return values or a useful error
```

Text equivalent: JSON file passes into validate a task list passes into return values or a useful error. Read the flow from left to right; a branch represents a controller decision, not a command from untrusted text.

## Read first, then make one small change

Read [the implementation](../../src/course_harness/__main__.py) and locate the module entry point and the test files. Trace the successful path before editing.

Start with a function before adding a CLI. Read text with UTF-8, decode JSON, and require a list of objects with a string `title`. Raise `ValueError` with an explanation for malformed data. Keep reading separate from writing so a failed read cannot destroy the original. An HTTP request is a structured message to another program; the offline harness replaces that other program with a fixture. Git records reviewed source changes, not environments, state databases, or secrets.

The continuing examples remain a disposable coding repository, synthetic SRE observations/service state, and local automation events/artifacts. Reuse the same engine rather than copying it into three domain-specific loops.

## Minimal code to inspect and extend

Create a JSON reader before a mutation API. The checkpoint's tiny JSON example is separate from your richer task-list exercise.

```python
from pathlib import Path
import json

def load_tasks(path):
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    # TODO: validate list/items/titles and return a defensive copy.
    raise NotImplementedError("validate before returning tasks")
```

Concrete exercise delta: The first failing test calls `load_tasks` with an empty valid list. Implement validation in this function; then add malformed-input/no-rewrite tests.

The complete test fragment lives in the separate solution. Keep your new helper/test on your learning branch; baseline checkpoints remain available while you work.

## Run a checkpoint

From `tracks/agent-harness-from-scratch/03-labs`, with the environment installed as in setup:

```sh
python -m course_harness checkpoint 0 --scenario coding
python -m course_harness checkpoint 0 --scenario sre
python -m course_harness checkpoint 0 --scenario automation
pytest -q tests -k lesson_00
```

These are learner/approved-worker commands. Do not execute them on the source-only authoring Mac. Expected CLI output is JSON with `lesson`, `scenario`, `status`, `stop_reason`, `trace`, and `checks`. Inspect the check values and exit status; absence of selected tests is not a pass.

The foundation checkpoint reports a successful offline check. Your task-list function returns two titles in file order; malformed JSON raises a descriptive error and leaves the bytes unchanged. The walkthrough below explains meaningful event order; helper/fixture events may be represented inside check records rather than as literal CLI event names.

Exact baseline expectation: The checkpoint's baseline `checks` include `task_loaded` and `malformed_preserves_original`; its model path stops as `final`. The richer list-of-objects task reader is your separate exercise.

## Read a successful trace

```text
file_read -> json_decoded -> shape_validated -> values_returned
```

At each transition, state what was requested, what trusted code decided, and what effect was observed. Engine trace events include `run_started`, `model_called`, `tool_requested`, `tool_completed`, and `run_stopped`; denial and approval paths add `tool_denied` or `approval_required`. A recorded final answer is not evidence an unrecorded side effect occurred.

## Break it on purpose

Replace valid JSON with `{broken`. Investigate the parse error without deleting the file. If your program returns an empty list, you have hidden corruption rather than handled it.

Keep the failure fixture separate from the reference fixture. Record the first violated contract, the last completed event, and whether any side effect happened. Restore the controlled input before comparing a successful run.

## Your exercise

Create `examples/task_list.py` with a `load_tasks(path)` function. Accept an empty list; reject a top-level object, non-object items, and missing/non-string titles. Never rewrite the input. Write a test that stores malformed JSON and compares its bytes before and after the error.

Before opening the solution, write one learner test in a separate `test_learner_00.py`. Include one success assertion, one deliberate failure assertion, and one assertion about the boundary/effect. Choose state, identifiers, call counts, and stop reasons rather than incidental model wording.

Progressive hints:

1. First decode JSON; then validate its shape. These are different failures.
2. Use `isinstance(value, list)` and inspect every item, not just the first.
3. Read-only functions need no exception handler that writes an empty replacement.

[Reference solution and test reasoning](../../solutions/00.md). Try the first hint and your own test before reading it.

## Acceptance checks

A valid list loads; empty input list loads; malformed JSON and invalid shapes fail clearly; original bytes are unchanged. Add the malformed-second-item case yourself.

The selected delivered checks are a baseline. Your extra test should fail when your exercise change is removed and pass when it is restored. Use controlled fixtures and injected time; required checks need no network or real infrastructure. Record unimplemented or unvalidated assertions honestly.

## Explain it back

What is the difference between a JSON object and a Python dictionary? Why is `.venv/` excluded from Git? Where can a secret leak besides a source file?

Plain-language explanation: A function receives data and either returns a defined result or raises a defined error. Tests let us check both paths before a model enters the picture.

Use the course rubric: needs guidance means you can follow the solution; independent means you can complete the edit and write a useful test; advanced means you can diagnose an unfamiliar failure and compare alternatives using evidence.

## Optional next extension

Add an optional `done` boolean with an explicit default, plus a test for an invalid string value.

Keep this extension small and reversible. Commit your reviewed exercise diff on your learning branch before moving on. There is no capstone or separate final project.
