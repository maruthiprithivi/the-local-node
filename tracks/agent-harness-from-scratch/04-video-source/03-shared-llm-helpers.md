# Lesson 3: Shared LLM helpers and a first optional API call: narration script

This is a readable recording script, not a published recording. It is adapted
from the canonical lesson text; keep that lab open for exact source snippets,
commands and separate solutions. Caption future recordings and describe arrows
and state changes aloud. The examples use synthetic fixtures and an offline fake
provider. Do not run demonstrations on the source-only authoring Mac.

## Opening and purpose

Create a stable request/reply boundary while preserving provider-specific capability differences. Work in one growing `course_harness` package. The checkpoint selects cumulative behavior; it does not replace your source or wipe your exercise changes.

## Describe the diagram aloud

```text
shared request → provider adapter → bounded transport → normalized Reply
```

Text equivalent: shared request passes into provider adapter passes into bounded transport passes into normalized Reply. Read the flow from left to right; a branch represents a controller decision, not a command from untrusted text.

Read each arrow in order. Explain what enters the boundary, which trusted
component decides, and what evidence comes out. Pause before displaying code.

## Source walkthrough

Read [the implementation](../../src/course_harness/providers.py) and locate shared reply/call types, transport helpers, configuration, and provider adapters. Trace the successful path before editing.

Follow fake replies through the shared interface before reading the live helpers. Keep model IDs/endpoints explicit and configurable. A transport timeout bounds one request; an output setting is an adapter/provider contract rather than a universal spending guarantee. Normalize authentication, rate-limit, transient, and malformed-response failures without retaining credentials. Locate entry points for OpenAI, Gemini, DeepSeek, Ollama, and NVIDIA. Read the official documentation linked beside each adapter; compatible-looking URLs do not prove identical tools or streaming semantics.

The continuing examples remain a disposable coding repository, synthetic SRE observations/service state, and local automation events/artifacts. Reuse the same engine rather than copying it into three domain-specific loops.

Open the lesson's minimal snippet. Narrate arguments, preconditions and return
values before typing the learner change. Keep the reference implementation intact
on its branch; learner tests should expose an unfinished TODO or missing guard.

## Demonstration and successful trace

Use the checkpoint commands from the lab on an approved execution host. Capture
actual terminal output; the following trace is a semantic narration, not a claim
that these exact event names are printed by every helper.

```text
config_checked -> request_bounded -> mock_transport_called -> reply_normalized
```

At each transition, state what was requested, what trusted code decided, and what effect was observed. Engine trace events include `run_started`, `model_called`, `tool_requested`, `tool_completed`, and `run_stopped`; denial and approval paths add `tool_denied` or `approval_required`. A recorded final answer is not evidence an unrecorded side effect occurred.

Pause to inspect identifiers, stop reasons and effect counts. A fixture result
is evidence about this classroom mechanism, not production security or live
model quality.

## Controlled failure walkthrough

Omit a required key for a hosted adapter. Failure must occur before the recording transport is called. Then request a capability the adapter does not declare.

Keep the failure fixture separate from the reference fixture. Record the first violated contract, the last completed event, and whether any side effect happened. Restore the controlled input before comparing a successful run.

Ask the learner to predict the last completed event, state and permitted effect
count before showing the result. Show the smallest violated boundary; restore the
controlled input before demonstrating success again.

## Learner pause and explanation

Inject a recording transport into one adapter. Return a valid provider fixture, then an authentication error. Test normalized replies and errors without making HTTP requests. Supply a synthetic secret and assert it is absent from serialized diagnostic output.

Before opening the solution, write one learner test in a separate `test_learner_03.py`. Include one success assertion, one deliberate failure assertion, and one assertion about the boundary/effect. Choose state, identifiers, call counts, and stop reasons rather than incidental model wording.

Progressive hints:

1. Inspect request construction separately from parsing.
2. Choose a fake key with a distinctive string so leakage is easy to assert.
3. Test a missing key with zero captured requests.

[Reference solution and test reasoning](../../solutions/03.md). Try the first hint and your own test before reading it.

Wait before revealing the separate worked solution. Then ask the learner to
explain the boundary in their own words:

Why does a key in the environment not mean live permission? Which features differ across providers? Why is unknown usage not zero usage?

Plain-language explanation: An adapter translates a real protocol. It does not own tools, budgets, policy, or the decision to use live services.

Use the course rubric: needs guidance means you can follow the solution; independent means you can complete the edit and write a useful test; advanced means you can diagnose an unfamiliar failure and compare alternatives using evidence.

## Continue the same engine

Compare two provider fixtures with the same normalized reply and different usage metadata.

Keep this extension small and reversible. Commit your reviewed exercise diff on your learning branch before moving on. There is no capstone or separate final project.
