# Lesson 1: Models, agents, harnesses, and fake responses

Lesson 0. Read [setup](../../../02-lab-book/setup.md) before running commands.

## What we are building

Explain a model's contribution and build a repeatable response boundary before permitting any action. Work in one growing `course_harness` package. The checkpoint selects cumulative behavior; it does not replace your source or wipe your exercise changes.

## Picture the flow

```text
fixture prompt → FakeProvider → Reply → controller termination
```

Text equivalent: fixture prompt passes into FakeProvider passes into Reply passes into controller termination. Read the flow from left to right; a branch represents a controller decision, not a command from untrusted text.

## Build this boundary yourself before reading the completed package

Start in [exercises/harness.py](../../exercises/harness.py), not the finished provider module. This one learner-owned file continues through lessons 5 and 6. It imports only standard-library helpers and contains real `NotImplementedError` TODOs.

Implement `make_message`, `validate_reply`, and `ScriptedProvider.complete` in that order. A message has `role` and string `content`; allow system/user/assistant/tool roles and at most 1024 characters. A reply has exactly `text` and `call`. A final reply has `call=None`; a request has empty text and exactly one call dictionary with nonempty bounded `id`/`name` and JSON-object `arguments` of at most 512 UTF-8 bytes. Keep this small teaching contract distinct from the richer completed package types.

```python
# Your first target behavior, after implementing the TODOs:
from exercises.harness import make_message, ScriptedProvider

message = make_message("user", "inspect synthetic evidence")
provider = ScriptedProvider([{"text": "fixture answer", "call": None}])
assert provider.complete([message])["text"] == "fixture answer"
```

Run `python -m pytest -q exercises/test_lesson_01.py`. It is intentionally red at first; `NotImplementedError` is the starting evidence, not a repository regression. Implement a defensive copy so editing the original message cannot change a captured request. Malformed replies and exhausted scripts must raise useful `ValueError` failures.

Progressive implementation hints: first return a validated message dictionary; then distinguish final versus request shape; finally capture a copied request and validate the next scripted reply. Catch `StopIteration` specifically to explain script exhaustion.

The normal reference check is `python -m pytest -q tests/unit/test_early_solutions.py -k lesson_01`. It tests the separate completed [early_harness.py](../../solutions/early_harness.py), so it should pass independently of your unfinished starter. These commands await approved runtime validation; none were run on the authoring Mac. Add your own malformed-argument test before comparing the solution.

## Read first, then make one small change

Read [the implementation](../../src/course_harness/providers.py) and locate `Reply`, `ToolCall`, and `FakeProvider`. Trace the successful path before editing.

Read the reply types, then script one final response per scenario. Keep the prompt as input data and termination as a controller decision. A token is a model-specific text unit; context is the input supplied to one call. A fluent answer can be incorrect. The fake provider deliberately removes that uncertainty so you can reason about control flow. Add a fixture response without adding any HTTP path.

The continuing examples remain a disposable coding repository, synthetic SRE observations/service state, and local automation events/artifacts. Reuse the same engine rather than copying it into three domain-specific loops.

## Minimal code to inspect and extend

At the provider boundary, create a fresh scripted instance and inspect its captured request.

```python
from course_harness.providers import FakeProvider, Reply
provider = FakeProvider([Reply("coding: inspect the toy function")])
reply = provider.complete([{"role": "user", "content": "inspect fixture"}])
assert reply.text == "coding: inspect the toy function"
assert len(provider.requests) == 1
```

Concrete exercise delta: Add your own final fixture beside this one. Then feed `Reply(calls=[])` as a deliberately malformed call container and assert `ProviderError`: calls must be a tuple.

The complete test fragment lives in the separate solution. Keep your new helper/test on your learning branch; baseline checkpoints remain available while you work.

## Run a checkpoint

From `tracks/agent-harness-from-scratch/03-labs`, with the environment installed as in setup:

```sh
python -m course_harness checkpoint 1 --scenario coding
python -m course_harness checkpoint 1 --scenario sre
python -m course_harness checkpoint 1 --scenario automation
pytest -q tests -k lesson_01
```

These are learner/approved-worker commands. Do not execute them on the source-only authoring Mac. Expected CLI output is JSON with `lesson`, `scenario`, `status`, `stop_reason`, `trace`, and `checks`. Inspect the check values and exit status; absence of selected tests is not a pass.

The same scenario and fixture produce the same final/stop decision with no credentials and no network request. The walkthrough below explains meaningful event order; helper/fixture events may be represented inside check records rather than as literal CLI event names.

Exact baseline expectation: The baseline stops as `final` and records no tool request. Assert check booleans and stop reason rather than reproducing complete JSON wording.

## Read a successful trace

```text
run_started -> model_called -> run_stopped(final)
```

At each transition, state what was requested, what trusted code decided, and what effect was observed. Engine trace events include `run_started`, `model_called`, `tool_requested`, `tool_completed`, and `run_stopped`; denial and approval paths add `tool_denied` or `approval_required`. A recorded final answer is not evidence an unrecorded side effect occurred.

## Break it on purpose

Use a fixture whose response has the wrong shape, then try an exhausted script. Observe a clear provider/contract failure, not a fabricated successful response.

Keep the failure fixture separate from the reference fixture. Record the first violated contract, the last completed event, and whether any side effect happened. Restore the controlled input before comparing a successful run.

## Your exercise

Add a scripted reply describing the next read-only observation for each scenario: inspect a toy function, inspect service health, and inspect an event. Add a malformed fixture that requests a tool without a usable identifier. Predict whether parsing or the controller rejects it.

Before opening the solution, write one learner test in a separate `test_learner_01.py`. Include one success assertion, one deliberate failure assertion, and one assertion about the boundary/effect. Choose state, identifiers, call counts, and stop reasons rather than incidental model wording.

Progressive hints:

1. Construct the shared reply type instead of pretending all providers return the same raw JSON.
2. Give fake scripts stable call identifiers when they request tools.
3. A fixture containing 'I approve' still contains only model text.

[Reference solution and test reasoning](../../solutions/01.md). Try the first hint and your own test before reading it.

## Acceptance checks

Final replies terminate; malformed replies fail; an exhausted fake script fails predictably; repeated fixture runs preserve meaningful decisions. Write your own malformed-fixture test.

The selected delivered checks are a baseline. Your extra test should fail when your exercise change is removed and pass when it is restored. Use controlled fixtures and injected time; required checks need no network or real infrastructure. Record unimplemented or unvalidated assertions honestly.

## Explain it back

Which component owns the stop reason? Can generated text authorize a write? Which uncertainty does the fake remove, and which bugs can it still expose?

Plain-language explanation: The model suggests content. The harness records state, checks contracts, applies policy, and decides when a run stops.

Use the course rubric: needs guidance means you can follow the solution; independent means you can complete the edit and write a useful test; advanced means you can diagnose an unfamiliar failure and compare alternatives using evidence.

## Optional next extension

Add a fake provider with two alternative scripts and compare traces without changing the engine.

Keep this extension small and reversible. Commit your reviewed exercise diff on your learning branch before moving on. There is no capstone or separate final project.
