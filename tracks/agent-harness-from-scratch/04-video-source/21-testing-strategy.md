# Lesson 21 narration: Tests organized by boundary

Transcript and recording script; no recording is claimed. Read the lab alongside
this text. Caption future recordings with these words and describe visual changes
aloud; do not rely on color or audio alone.

## Opening

Today we extend the same small Python harness. Tests have existed since lesson 1. Now separate pure value checks, provider contract checks, controller/policy/store integration and CLI/lifecycle checks. A unit test narrows diagnosis; integration catches interactions. Use temporary workspaces and injected clocks. The offline guard rejects unexpected network access.

## Describe the diagram

Small checks isolate rules; joined checks verify that components preserve those rules together; interface checks verify usable behavior. Read every arrow in order. The host-owned boundary is ordinary program
logic, visible outside the model's suggestions.

## Walk through source

Open tests/conftest.py; tests/contract/test_providers.py; tests/unit, tests/integration and tests/e2e; shared test fixtures. Follow input values to the decision and then to the recorded
result. Move a learner test into the narrowest appropriate test folder without changing its meaning. Add an integration test that closes and reopens a store while an exact approval or stop control is pending. Run single tests and then the suite on an approved execution host.

## Narrate the successful run

Say: unit: changed action invalidates approval.

Say: contract: native response normalizes.

Say: integration: restart preserves pending state.

Say: E2E: CLI selects fake fixture and returns bounded stop reason.

Run checkpoint 21 for coding, SRE and automation. Pause to inspect each result.
The lab's trace describes meaning, not exact terminal formatting.

## Investigate a failure

Deliberately remove the human-stop read from the claim path in your learner branch. An in-memory test may still pass; a reopen-store integration test must fail. Restore the guard before continuing. Ask learners to predict the effect count and recovery state before
showing the result. Leave time to try the progressive hints before revealing the
separate solution.

## Learner pause

Write a regression test covering enqueue, pending approval, persistent stop, reopen and rejected admission/claim. Run it by itself and after an unrelated provider contract test; it must not depend on order. Ask learners to write the acceptance test and explain:
Which test should fail if wire encoding changes but controller behavior does not? Which should fail if restart clears stop?

## Continuing

Add Windows-specific subprocess cleanup coverage on a permitted Windows runner; document gaps rather than simulating proof from Linux. This remains an incremental extension of the existing engine.

