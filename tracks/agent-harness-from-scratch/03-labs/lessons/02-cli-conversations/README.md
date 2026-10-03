# Lesson 2: CLI conversations and visible state

Lesson 1. Read [setup](../../../02-lab-book/setup.md) before running commands.

## What we are building

Separate terminal input, ordered conversation history, and model execution. Work in one growing `course_harness` package. The checkpoint selects cumulative behavior; it does not replace your source or wipe your exercise changes.

## Picture the flow

```text
terminal command → session history → one bounded run → displayed result
```

Text equivalent: terminal command passes into session history passes into one bounded run passes into displayed result. Read the flow from left to right; a branch represents a controller decision, not a command from untrusted text.

## Read first, then make one small change

Read [the implementation](../../src/course_harness/__main__.py) and locate the CLI command handlers and the ordered message dictionaries in `core.py`. Trace the successful path before editing.

Trace how the CLI obtains input and passes it to the engine. Add a small session wrapper with help/reset/exit operations. A turn is one model interaction; a run is a bounded task attempt; a session owns ordered history across runs. Reject oversized input before appending it. Reset clears the documented conversation history, not permissions or durable state. Handle EOF and KeyboardInterrupt at the interface boundary.

The continuing examples remain a disposable coding repository, synthetic SRE observations/service state, and local automation events/artifacts. Reuse the same engine rather than copying it into three domain-specific loops.

## Minimal code to inspect and extend

Read `conversation` in the CLI. Add a recording seam if you need to inspect internal history rather than only display text.

```python
from course_harness.__main__ import conversation
commands = iter(["/help", "inspect fixture", "/reset", "/exit"])
output = []
conversation(input_fn=lambda prompt: next(commands), output_fn=output.append)
assert "session reset" in output
assert output[-1] == "bye"
```

Concrete exercise delta: The baseline UI reconstructs a fixture provider per ordinary turn while retaining history. For the exercise, inject a provider factory/recording seam into `conversation`; assert the second request has the first turn, but a request after `/reset` does not. Keep the policy boundary host-owned.

The complete test fragment lives in the separate solution. Keep your new helper/test on your learning branch; baseline checkpoints remain available while you work.

## Run a checkpoint

From `tracks/agent-harness-from-scratch/03-labs`, with the environment installed as in setup:

```sh
python -m course_harness checkpoint 2 --scenario coding
python -m course_harness checkpoint 2 --scenario sre
python -m course_harness checkpoint 2 --scenario automation
pytest -q tests -k lesson_02
```

These are learner/approved-worker commands. Do not execute them on the source-only authoring Mac. Expected CLI output is JSON with `lesson`, `scenario`, `status`, `stop_reason`, `trace`, and `checks`. Inspect the check values and exit status; absence of selected tests is not a pass.

Messages remain in user/assistant order, help performs no model call, reset removes only session messages, and exit/interruption end input handling. The walkthrough below explains meaningful event order; helper/fixture events may be represented inside check records rather than as literal CLI event names.

Exact baseline expectation: Run `python -m course_harness chat` for the interactive path. Try `/help`, a short prompt, `/reset`, then `/exit`; expected messages include `session reset` and final `bye`. The checkpoint itself is one bounded run, not a transcript of this session.

## Read a successful trace

```text
input_received -> message_appended -> model_called -> reply_appended -> reset -> input_closed
```

At each transition, state what was requested, what trusted code decided, and what effect was observed. Engine trace events include `run_started`, `model_called`, `tool_requested`, `tool_completed`, and `run_stopped`; denial and approval paths add `tool_denied` or `approval_required`. A recorded final answer is not evidence an unrecorded side effect occurred.

## Break it on purpose

Feed an input above the size limit, then EOF. No oversized message should enter history; EOF should exit cleanly rather than spin and repeatedly call the provider.

Keep the failure fixture separate from the reference fixture. Record the first violated contract, the last completed event, and whether any side effect happened. Restore the controlled input before comparing a successful run.

## Your exercise

Create a scripted two-turn conversation for coding, SRE, and automation. Add a reset command that clears history without replacing the provider or policy. Test reset between the two turns and compare the messages seen by a recording fake.

Before opening the solution, write one learner test in a separate `test_learner_02.py`. Include one success assertion, one deliberate failure assertion, and one assertion about the boundary/effect. Choose state, identifiers, call counts, and stop reasons rather than incidental model wording.

Progressive hints:

1. Put command parsing before ordinary message handling.
2. Keep history in an explicit list, not a global variable.
3. Inspect the recording fake's request list to test ordering without matching terminal decoration.

[Reference solution and test reasoning](../../solutions/02.md). Try the first hint and your own test before reading it.

## Acceptance checks

Ordered two-turn requests; reset's exact state boundary; input limit before provider call; clean EOF and interruption. Add a test that help leaves history and provider call count unchanged.

The selected delivered checks are a baseline. Your extra test should fail when your exercise change is removed and pass when it is restored. Use controlled fixtures and injected time; required checks need no network or real infrastructure. Record unimplemented or unvalidated assertions honestly.

## Explain it back

Why should reset not erase policy or approval state? Where should Ctrl-C be translated into a clean interface exit? Can one session contain several runs?

Plain-language explanation: The CLI is an interface. It should translate user input into well-defined operations rather than contain provider or permission logic.

Use the course rubric: needs guidance means you can follow the solution; independent means you can complete the edit and write a useful test; advanced means you can diagnose an unfamiliar failure and compare alternatives using evidence.

## Optional next extension

Add a transcript command that redacts secrets and preserves trust labels.

Keep this extension small and reversible. Commit your reviewed exercise diff on your learning branch before moving on. There is no capstone or separate final project.
