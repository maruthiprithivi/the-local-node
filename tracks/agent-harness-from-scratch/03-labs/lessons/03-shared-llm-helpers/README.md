# Lesson 3: Shared LLM helpers and a first optional API call

Lesson 2. Read [setup](../../../02-lab-book/setup.md) before running commands.

## What we are building

Create a stable request/reply boundary while preserving provider-specific capability differences. Work in one growing `course_harness` package. The checkpoint selects cumulative behavior; it does not replace your source or wipe your exercise changes.

## Picture the flow

```text
shared request → provider adapter → bounded transport → normalized Reply
```

Text equivalent: shared request passes into provider adapter passes into bounded transport passes into normalized Reply. Read the flow from left to right; a branch represents a controller decision, not a command from untrusted text.

## Read first, then make one small change

Read [the implementation](../../src/course_harness/providers.py) and locate shared reply/call types, transport helpers, configuration, and provider adapters. Trace the successful path before editing.

Follow fake replies through the shared interface before reading the live helpers. Keep model IDs/endpoints explicit and configurable. A transport timeout bounds one request; an output setting is an adapter/provider contract rather than a universal spending guarantee. Normalize authentication, rate-limit, transient, and malformed-response failures without retaining credentials. Locate entry points for OpenAI, Gemini, DeepSeek, Ollama, and NVIDIA. Read the official documentation linked beside each adapter; compatible-looking URLs do not prove identical tools or streaming semantics.

The continuing examples remain a disposable coding repository, synthetic SRE observations/service state, and local automation events/artifacts. Reuse the same engine rather than copying it into three domain-specific loops.

## Minimal code to inspect and extend

Use a transport fixture to inspect wire construction without enabling live calls.

```python
from course_harness.providers import OpenAIProvider, FixtureTransport
transport = FixtureTransport([{
    "choices": [{"message": {"content": "fixture"}, "finish_reason": "stop"}]
}])
provider = OpenAIProvider("fixture-model", transport=transport,
                          timeout=2, max_output_tokens=32)
assert provider.complete([{"role": "user", "content": "inspect"}]).text == "fixture"
assert transport.requests[0]["timeout"] == 2
```

Concrete exercise delta: Add an authentication-error transport fixture and assert one terminal normalized failure. Inspect the same adapter's request helper before adding any feature; provider fixtures belong at the boundary, not in `Engine.run`.

The complete test fragment lives in the separate solution. Keep your new helper/test on your learning branch; baseline checkpoints remain available while you work.

## Run a checkpoint

From `tracks/agent-harness-from-scratch/03-labs`, with the environment installed as in setup:

```sh
python -m course_harness checkpoint 3 --scenario coding
python -m course_harness checkpoint 3 --scenario sre
python -m course_harness checkpoint 3 --scenario automation
pytest -q tests -k lesson_03
pytest -q tests/contract/test_providers.py
```

These are learner/approved-worker commands. Do not execute them on the source-only authoring Mac. Expected CLI output is JSON with `lesson`, `scenario`, `status`, `stop_reason`, `trace`, and `checks`. Inspect the check values and exit status; absence of selected tests is not a pass.

Fake remains the default; mock transport captures a bounded request; missing credentials and unsupported required capabilities fail explicitly. The walkthrough below explains meaningful event order; helper/fixture events may be represented inside check records rather than as literal CLI event names.

Exact baseline expectation: The checkpoint remains fake and stops as `final`; provider contract tests use injected transports. No live API call is part of this lesson's required commands.

## Read a successful trace

```text
config_checked -> request_bounded -> mock_transport_called -> reply_normalized
```

At each transition, state what was requested, what trusted code decided, and what effect was observed. Engine trace events include `run_started`, `model_called`, `tool_requested`, `tool_completed`, and `run_stopped`; denial and approval paths add `tool_denied` or `approval_required`. A recorded final answer is not evidence an unrecorded side effect occurred.

## Break it on purpose

Omit a required key for a hosted adapter. Failure must occur before the recording transport is called. Then request a capability the adapter does not declare.

Keep the failure fixture separate from the reference fixture. Record the first violated contract, the last completed event, and whether any side effect happened. Restore the controlled input before comparing a successful run.

## Your exercise

Inject a recording transport into one adapter. Return a valid provider fixture, then an authentication error. Test normalized replies and errors without making HTTP requests. Supply a synthetic secret and assert it is absent from serialized diagnostic output.

Before opening the solution, write one learner test in a separate `test_learner_03.py`. Include one success assertion, one deliberate failure assertion, and one assertion about the boundary/effect. Choose state, identifiers, call counts, and stop reasons rather than incidental model wording.

Progressive hints:

1. Inspect request construction separately from parsing.
2. Choose a fake key with a distinctive string so leakage is easy to assert.
3. Test a missing key with zero captured requests.

[Reference solution and test reasoning](../../solutions/03.md). Try the first hint and your own test before reading it.

## Acceptance checks

No default network; explicit live opt-in; missing credentials fail early; output/time settings are present; authentication is terminal; secrets are redacted. Add one malformed-response fixture test.

The selected delivered checks are a baseline. Your extra test should fail when your exercise change is removed and pass when it is restored. Use controlled fixtures and injected time; required checks need no network or real infrastructure. Record unimplemented or unvalidated assertions honestly.

## Explain it back

Why does a key in the environment not mean live permission? Which features differ across providers? Why is unknown usage not zero usage?

Plain-language explanation: An adapter translates a real protocol. It does not own tools, budgets, policy, or the decision to use live services.

Use the course rubric: needs guidance means you can follow the solution; independent means you can complete the edit and write a useful test; advanced means you can diagnose an unfamiliar failure and compare alternatives using evidence.

## Optional next extension

Compare two provider fixtures with the same normalized reply and different usage metadata.

Keep this extension small and reversible. Commit your reviewed exercise diff on your learning branch before moving on. There is no capstone or separate final project.
