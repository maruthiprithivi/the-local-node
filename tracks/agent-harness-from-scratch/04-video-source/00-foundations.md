# Optional lesson 0: Foundations without hidden prerequisites: narration script

This is a readable recording script, not a published recording. It is adapted
from the canonical lesson text; keep that lab open for exact source snippets,
commands and separate solutions. Caption future recordings and describe arrows
and state changes aloud. The examples use synthetic fixtures and an offline fake
provider. Do not run demonstrations on the source-only authoring Mac.

## Opening and purpose

Use the terminal, small Python functions, JSON, Git, and tests without guessing what each command does. Work in one growing `course_harness` package. The checkpoint selects cumulative behavior; it does not replace your source or wipe your exercise changes.

## Describe the diagram aloud

```text
JSON file → validate a task list → return values or a useful error
```

Text equivalent: JSON file passes into validate a task list passes into return values or a useful error. Read the flow from left to right; a branch represents a controller decision, not a command from untrusted text.

Read each arrow in order. Explain what enters the boundary, which trusted
component decides, and what evidence comes out. Pause before displaying code.

## Source walkthrough

Read [the implementation](../../src/course_harness/__main__.py) and locate the module entry point and the test files. Trace the successful path before editing.

Start with a function before adding a CLI. Read text with UTF-8, decode JSON, and require a list of objects with a string `title`. Raise `ValueError` with an explanation for malformed data. Keep reading separate from writing so a failed read cannot destroy the original. An HTTP request is a structured message to another program; the offline harness replaces that other program with a fixture. Git records reviewed source changes, not environments, state databases, or secrets.

The continuing examples remain a disposable coding repository, synthetic SRE observations/service state, and local automation events/artifacts. Reuse the same engine rather than copying it into three domain-specific loops.

Open the lesson's minimal snippet. Narrate arguments, preconditions and return
values before typing the learner change. Keep the reference implementation intact
on its branch; learner tests should expose an unfinished TODO or missing guard.

## Demonstration and successful trace

Use the checkpoint commands from the lab on an approved execution host. Capture
actual terminal output; the following trace is a semantic narration, not a claim
that these exact event names are printed by every helper.

```text
file_read -> json_decoded -> shape_validated -> values_returned
```

At each transition, state what was requested, what trusted code decided, and what effect was observed. Engine trace events include `run_started`, `model_called`, `tool_requested`, `tool_completed`, and `run_stopped`; denial and approval paths add `tool_denied` or `approval_required`. A recorded final answer is not evidence an unrecorded side effect occurred.

Pause to inspect identifiers, stop reasons and effect counts. A fixture result
is evidence about this classroom mechanism, not production security or live
model quality.

## Controlled failure walkthrough

Replace valid JSON with `{broken`. Investigate the parse error without deleting the file. If your program returns an empty list, you have hidden corruption rather than handled it.

Keep the failure fixture separate from the reference fixture. Record the first violated contract, the last completed event, and whether any side effect happened. Restore the controlled input before comparing a successful run.

Ask the learner to predict the last completed event, state and permitted effect
count before showing the result. Show the smallest violated boundary; restore the
controlled input before demonstrating success again.

## Learner pause and explanation

Create `examples/task_list.py` with a `load_tasks(path)` function. Accept an empty list; reject a top-level object, non-object items, and missing/non-string titles. Never rewrite the input. Write a test that stores malformed JSON and compares its bytes before and after the error.

Before opening the solution, write one learner test in a separate `test_learner_00.py`. Include one success assertion, one deliberate failure assertion, and one assertion about the boundary/effect. Choose state, identifiers, call counts, and stop reasons rather than incidental model wording.

Progressive hints:

1. First decode JSON; then validate its shape. These are different failures.
2. Use `isinstance(value, list)` and inspect every item, not just the first.
3. Read-only functions need no exception handler that writes an empty replacement.

[Reference solution and test reasoning](../../solutions/00.md). Try the first hint and your own test before reading it.

Wait before revealing the separate worked solution. Then ask the learner to
explain the boundary in their own words:

What is the difference between a JSON object and a Python dictionary? Why is `.venv/` excluded from Git? Where can a secret leak besides a source file?

Plain-language explanation: A function receives data and either returns a defined result or raises a defined error. Tests let us check both paths before a model enters the picture.

Use the course rubric: needs guidance means you can follow the solution; independent means you can complete the edit and write a useful test; advanced means you can diagnose an unfamiliar failure and compare alternatives using evidence.

## Continue the same engine

Add an optional `done` boolean with an explicit default, plus a test for an invalid string value.

Keep this extension small and reversible. Commit your reviewed exercise diff on your learning branch before moving on. There is no capstone or separate final project.
