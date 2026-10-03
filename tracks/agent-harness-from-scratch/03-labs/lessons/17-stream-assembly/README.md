# Lesson 17: Streaming without partial tool execution

Prerequisite: Lesson 16; M5. Work from `03-labs/` after setup. Split this lesson into
three short sessions: read/trace, change/test, and explain/review. This is another
increment to the shared engine, not a separate project.

## Build and purpose

A stream is a series of fragments, not a series of authorized actions. Assemble ordered normalized text/tool/end events; bound bytes, bind fragments to a stable call ID/name, parse complete JSON, then validate every call. Disconnect, cancellation and malformed siblings discard pending calls. `streaming.py` also decodes supplied native SSE fixtures for OpenAI/DeepSeek/NVIDIA/Gemini and native Ollama NDJSON fixtures. HTTP adapters remain synchronous; live streaming transport and its cancellation are unsupported.

## Diagram and text equivalent

```text
fragments -> bounded assembler -> end -> JSON + contract validation -> complete calls
```

Fragments accumulate in a bounded buffer. Only an explicit end followed by complete JSON and contract validation can expose a tool call.

## Read, then make the smallest change

Open [advanced.py](../../src/course_harness/advanced.py) and follow the named APIs.

Read `advanced.py: StreamAssembler.feed and finish; providers.py synchronous boundary`. Trace the relevant arguments and return values before editing.

Then read [streaming.py](../../src/course_harness/streaming.py), especially
`read_stream(provider, chunks, validate, cancelled=...)`. It returns
`DecodedStream` with assembled response, native usage, normalized events and
metadata. Required completion signals and native provider rules are checked
before complete calls can become visible. This API consumes byte fixtures; it
does not open a connection. Providers do not claim live streaming support.

Add a named toy-tool validator to StreamAssembler, then feed a JSON argument across two fragments. Keep the executor outside the assembler. The minimal change is a validator and test fixture, not streaming network code.

Create `tests/learner/test_lesson_17.py` on your branch for the exercise. Keep
solution reading separate until you have tried the first hint. Do not replace the
whole engine with the solution: compare only the boundary you are learning.

## Run the checkpoint

### Learner code delta

Add this function to your learner test file, then replace the TODO with the
smallest implementation using the named reference API. The starter deliberately
raises so an unfinished exercise cannot look complete. Return the assembled response; never call an executor while feeding fragments.

```python
def assemble_fixture(events, validator):
    # TODO: implement this boundary using the reference API.
    raise NotImplementedError("Complete lesson 17's learner delta")
```

Write a successful case and the lesson's edge case against this helper. The
separate solution shows the implementation after the hints; its test is a starting
point, and you must add the helper-specific assertions yourself.

## Checkpoint commands

```sh
python -m course_harness checkpoint 17 --scenario coding
python -m course_harness checkpoint 17 --scenario sre
python -m course_harness checkpoint 17 --scenario automation
pytest -q tests -k lesson_17
pytest -q tests/learner/test_lesson_17.py
```

Use `pytest -q tests/contract/test_streaming.py` for native decoder cases. Add a test that splits a UTF-8
character across supplied byte chunks, plus one missing terminal signal.

Inspect an actual offline native fixture from `03-labs/`:

```python
from pathlib import Path
from course_harness.streaming import read_stream

validated = []  # A production validator checks the registry contract; no effects.
decoded = read_stream("openai",
    [Path("provider_fixtures/chat-stream.sse").read_bytes()], validated.append)
assert not decoded.response.interrupted
assert decoded.response.calls
```

Repeat with `gemini-stream.sse` and `ollama-stream.ndjson` under their respective
provider names. DeepSeek and NVIDIA share the chat fixture envelope here, but
capability declarations and model selection remain explicit. A list append only
records validation in this fixture; replace it with the real pure contract check
before exposing complete calls to the controller.

The CLI prints structured offline checkpoint evidence tagged with lesson/scenario.
Exact JSON fields follow the implementation; inspect them alongside the semantic
trace below. Pytest should report selected checks passing, not merely zero tests.
The final command exists after you write your learner test. These are intended
learner commands, not an authoring test report; see the track's validation status.

## Successful path to inspect

```text
sequence 0: tool id=read-1 delta={"path":
sequence 1: same tool delta="toy.py"}
sequence 2: end
finish -> one validated call; repeated finish returns same result
```

This is a narrated semantic trace rather than a byte-for-byte CLI transcript.
Find the corresponding state/record in the checkpoint output. Across the three
paths, coding uses disposable files, SRE uses synthetic observations, and
automation uses fixture events. The same host gates continue to apply.

## Controlled failure

Omit end or feed sequence 2 before sequence 1. finish must label interruption and return zero calls. If one sibling is malformed, no sibling executes. Cancellation after a partial request also returns zero calls.

Run this fault only against your disposable learner fixtures. Predict the state
and effect count before running it; compare your prediction with the result.

## Exercise and progressive hints

Write tests for split arguments, changed tool names, out-of-order fragments, disconnect and cancelled finish. Count validator invocations and prove repeated finish does not validate twice.

1. Give the validator a list to append validated calls.
2. feed accepts dictionaries with sequence/kind/delta and, for tools, id/name.
3. There is no executor callback in this API; absence is deliberate.

## Acceptance checks

Complete streams expose validated calls once; partial/malformed/cancelled streams expose none; size limits hold; interrupted text carries a reason; no claimed native streaming capability is silently downgraded.

The shipped checkpoint tests cover the reference path and an edge case. Your
learner test must assert a meaningful invariant and fail when that invariant is
removed. Run it alone, then with the suite; never claim a test passed from reading
its source. [Separate worked solution](../../solutions/17.md).

## Explain before continuing

Why can displaying partial text be acceptable while executing a partial tool request is not? Display itself still needs redaction and bounded capture.

In plain language: identify the input, the host-owned boundary, the evidence that
crosses it, and the stop/recovery decision. A correct explanation plus a useful
new test demonstrates independence; copying a passing example demonstrates only
that you can follow it.

## Return point and optional extension

Re-run checkpoint 17 to return to a known reference demonstration without
changing your files. Preserve your own branch/diff before experimenting.

Implement one provider-specific decoder from its documented stream format, preserving terminal rules, then add fixtures before enabling transport.
