# Lesson 29: Integrate a framework after learning the internals — narration script

Readable script; no recording is claimed. Caption future narration and describe
all diagram arrows and state changes in words. Keep the canonical lab open for
exact APIs, commands, hints and the separate solution.

## Opening

A framework may supply suggestions or call a host operation. It must not become a second policy, session or side-effect owner. The optional OpenAI Agents SDK example is isolated from core dependencies; its no-tool/no-session callback returns a suggestion. FrameworkToolBridge routes a requested tool through the existing Engine, registry, Policy and optional journal.

## Diagram description

Both directions cross the same host boundary. The framework produces evidence; the controller and policy retain termination and authority.

## Source walkthrough

Open extensions.py and FrameworkProvider.complete and FrameworkToolBridge.invoke; examples/framework/. Follow the concrete host decision before
implementing the learner TODO. Use FrameworkToolBridge with a finite call budget; request only observe_health.

## Successful path

Say: framework invokes observe_health -> validation -> policy allow -> result -> final.

Say: framework invokes restart_service -> policy denied; restarts=0.

Say: suggestion callback -> bounded Reply; extra call -> framework_budget.

Pause to inspect the actual checkpoint evidence and distinguish semantic narration
from literal output. Identify every simulated identity, effect and receipt.

## Failure and learner pause

Let the framework request restart_service under a host policy permitting only observe_health. The bridge must stop denied with no restart. Then cancel before a callback and exhaust its call bound. The wrapper checks cooperative elapsed time after return; it cannot forcibly stop hung code.

Compare the same read-only synthetic health task through FakeProvider and through the bridge. Add one permitted custom diagnostics tool and one gated remediation request. Explain which lines become simpler and which boundary checks remain. Test cancellation and denied nested calls.

Ask learners to predict the state/effect count, then write the test. Give the
progressive hints one at a time before showing the solution.

## Explain and continue

What can the framework replace, and which responsibilities must remain host-owned? Why isn't an SDK tool decorator sufficient permission enforcement?

After separate authorization and remote validation, compare the pinned SDK callback with the offline callback using the same evaluation fixtures; installation/live inference is not part of this checkpoint.

