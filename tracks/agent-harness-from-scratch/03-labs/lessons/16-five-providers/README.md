# Lesson 16: Five provider adapters, one honest contract

Prerequisite: Lessons 3, 12 and 15; M5. Work from `03-labs/` after setup. Split this lesson into
three short sessions: read/trace, change/test, and explain/review. This is another
increment to the shared engine, not a separate project.

## Build and purpose

Compare native envelopes before sharing parsing. OpenAI, DeepSeek and NVIDIA use chat-shaped requests here; Gemini uses content parts; Ollama uses native chat responses. Preserve native round-trip metadata where needed. Missing usage stays unknown. Configurable models are fixture names in offline examples, not promises of provider availability.

## Diagram and text equivalent

```text
shared messages -> native adapter -> injected transport -> native fixture -> Reply
```

The shared request passes through a provider-specific encoder and a fake transport; the decoder returns normalized text, tool calls, usage and metadata.

## Read, then make the smallest change

Open [providers.py](../../src/course_harness/providers.py) and follow the named APIs.

Read `providers.py: _HTTPProvider, _ChatProvider, OpenAIProvider, GeminiProvider, DeepSeekProvider, OllamaProvider and NVIDIAProvider; tests/contract/test_providers.py; provider_fixtures/`. Trace the relevant arguments and return values before editing.

Add a provider-specific malformed-response case to the contract suite using FixtureTransport. Record the payload sent by the helper and assert its native fields rather than calling a live endpoint.

Create `tests/learner/test_lesson_16.py` on your branch for the exercise. Keep
solution reading separate until you have tried the first hint. Do not replace the
whole engine with the solution: compare only the boundary you are learning.

## Run the checkpoint

### Learner code delta

Add this function to your learner test file, then replace the TODO with the
smallest implementation using the named reference API. The starter deliberately
raises so an unfinished exercise cannot look complete. Use an injected transport and return Reply. NVIDIA tool capability is configured separately before passing tools.

```python
def fixture_reply(provider_class, native_response):
    # TODO: implement this boundary using the reference API.
    raise NotImplementedError("Complete lesson 16's learner delta")
```

Write a successful case and the lesson's edge case against this helper. The
separate solution shows the implementation after the hints; its test is a starting
point, and you must add the helper-specific assertions yourself.

## Checkpoint commands

```sh
python -m course_harness checkpoint 16 --scenario coding
python -m course_harness checkpoint 16 --scenario sre
python -m course_harness checkpoint 16 --scenario automation
pytest -q tests -k lesson_16
pytest -q tests/learner/test_lesson_16.py
```

The CLI prints structured offline checkpoint evidence tagged with lesson/scenario.
Exact JSON fields follow the implementation; inspect them alongside the semantic
trace below. Pytest should report selected checks passing, not merely zero tests.
The final command exists after you write your learner test. These are intended
learner commands, not an authoring test report; see the track's validation status.

Also run `pytest -q tests/contract/test_providers.py` for the five native adapters.

## Successful path to inspect

```text
fixture transport receives bounded request
native tool arguments normalize to a dictionary
Reply carries call ID and provider metadata
no network; no credentials; no tool execution
```

This is a narrated semantic trace rather than a byte-for-byte CLI transcript.
Find the corresponding state/record in the checkpoint output. Across the three
paths, coding uses disposable files, SRE uses synthetic observations, and
automation uses fixture events. The same host gates continue to apply.

## Controlled failure

Configure NVIDIA without enabling a known model's tool capability, then pass tools. Expect unsupported_tools before transport. For Gemini, remove a required content envelope. For Ollama, replace object arguments with a malformed value. Diagnose the native boundary, not a controller failure.

Run this fault only against your disposable learner fixtures. Predict the state
and effect count before running it; compare your prediction with the result.

## Exercise and progressive hints

Run the same read-only tool request through all five fixture adapters. Add one test for absent token usage and one malformed fixture test. Explain which native fields are preserved for follow-up turns.

1. Start from the parameterized shared contract in tests/contract/test_providers.py.
2. Use the injected transport even when a dummy API key is present.
3. Inspect assistant_message: normalization must not erase needed native metadata.

## Acceptance checks

All five mocked adapters normalize text and tools; malformed responses and unsupported tools fail explicitly; absent usage is not zero; fake credentials do not enter errors; default execution never sends a live request.

The shipped checkpoint tests cover the reference path and an edge case. Your
learner test must assert a meaningful invariant and fail when that invariant is
removed. Run it alone, then with the suite; never claim a test passed from reading
its source. [Separate worked solution](../../solutions/16.md).

## Explain before continuing

What does 'OpenAI-compatible' prove? Only a starting request shape; each model/endpoint still needs its own tool, error, usage and streaming checks.

In plain language: identify the input, the host-owned boundary, the evidence that
crosses it, and the stop/recovery decision. A correct explanation plus a useful
new test demonstrates independence; copying a passing example demonstrates only
that you can follow it.

## Return point and optional extension

Re-run checkpoint 16 to return to a known reference demonstration without
changing your files. Preserve your own branch/diff before experimenting.

Read the official docs linked in the provider guide. A bounded live smoke experiment requires a separately authorized opt-in, explicit model/endpoint and credentials; it is not required here.
