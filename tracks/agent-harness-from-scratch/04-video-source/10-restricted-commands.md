# Lesson 10: Restricted commands and verified remediation: narration script

This is a readable recording script, not a published recording. It is adapted
from the canonical lesson text; keep that lab open for exact source snippets,
commands and separate solutions. Caption future recordings and describe arrows
and state changes aloud. The examples use synthetic fixtures and an offline fake
provider. Do not run demonstrations on the source-only authoring Mac.

## Opening and purpose

Run only named course-owned commands, then verify effects rather than trust exit status alone. Work in one growing `course_harness` package. The checkpoint selects cumulative behavior; it does not replace your source or wipe your exercise changes.

## Describe the diagram aloud

```text
approved named action → fixed argv + limits → bounded result → postcondition check → stop/escalate
```

Text equivalent: approved named action passes into fixed argv + limits passes into bounded result passes into postcondition check passes into stop/escalate. Read the flow from left to right; a branch represents a controller decision, not a command from untrusted text.

Read each arrow in order. Explain what enters the boundary, which trusted
component decides, and what evidence comes out. Pause before displaying code.

## Source walkthrough

Read [the implementation](../../src/course_harness/tools.py) and locate restricted execution and synthetic SRE remediation handlers. Trace the successful path before editing.

A command runner accepts a named operation that maps to a fixed argument array and working directory. Avoid shell parsing and model-selected executables. Use a sanitized environment, output limit, timeout, and documented cleanup. Repository tests execute code, so expose only course-owned toy checks. Permit one synthetic service restart with a cooldown/attempt bound, then observe health. A zero return code is not proof that the intended state was reached.

The continuing examples remain a disposable coding repository, synthetic SRE observations/service state, and local automation events/artifacts. Reuse the same engine rather than copying it into three domain-specific loops.

Open the lesson's minimal snippet. Narrate arguments, preconditions and return
values before typing the learner change. Keep the reference implementation intact
on its branch; learner tests should expose an unfinished TODO or missing guard.

## Demonstration and successful trace

Use the checkpoint commands from the lab on an approved execution host. Capture
actual terminal output; the following trace is a semantic narration, not a claim
that these exact event names are printed by every helper.

```text
tool_requested -> policy_allowed -> action_started -> tool_completed -> verification -> final | escalation
```

At each transition, state what was requested, what trusted code decided, and what effect was observed. Engine trace events include `run_started`, `model_called`, `tool_requested`, `tool_completed`, and `run_stopped`; denial and approval paths add `tool_denied` or `approval_required`. A recorded final answer is not evidence an unrecorded side effect occurred.

Pause to inspect identifiers, stop reasons and effect counts. A fixture result
is evidence about this classroom mechanism, not production security or live
model quality.

## Controlled failure walkthrough

Supply shell metacharacters as an argument, then a command alias not in the allowlist. The metacharacters must never be interpreted by a shell; the unknown command must not start. Simulate restart success with unhealthy verification and require escalation.

Keep the failure fixture separate from the reference fixture. Record the first violated contract, the last completed event, and whether any side effect happened. Restore the controlled input before comparing a successful run.

Ask the learner to predict the last completed event, state and permitted effect
count before showing the result. Show the smallest violated boundary; restore the
controlled input before demonstrating success again.

## Learner pause and explanation

Run a course-owned toy function check after the approved edit from lesson 7. For SRE, permit one restart of the disposable fixture service and verify health. For automation, route a local check through the same gate. Add failure cases for unknown commands and failed postconditions.

Before opening the solution, write one learner test in a separate `test_learner_10.py`. Include one success assertion, one deliberate failure assertion, and one assertion about the boundary/effect. Choose state, identifiers, call counts, and stop reasons rather than incidental model wording.

Progressive hints:

1. Map a symbolic operation to argv; do not split arbitrary model text.
2. Test handler launch count for denial.
3. Inject a failing health fixture instead of restarting a real service.

[Reference solution and test reasoning](../../solutions/10.md). Try the first hint and your own test before reading it.

Wait before revealing the separate worked solution. Then ask the learner to
explain the boundary in their own words:

Why do timeouts need cleanup? Why is an allowlisted interpreter still powerful? How does verification differ from a command returning zero?

Plain-language explanation: Authorization establishes permission to attempt an action. Observation after the action establishes what happened.

Use the course rubric: needs guidance means you can follow the solution; independent means you can complete the edit and write a useful test; advanced means you can diagnose an unfamiliar failure and compare alternatives using evidence.

## Continue the same engine

Document/test platform-specific subprocess cleanup on an approved disposable worker.

Keep this extension small and reversible. Commit your reviewed exercise diff on your learning branch before moving on. There is no capstone or separate final project.
