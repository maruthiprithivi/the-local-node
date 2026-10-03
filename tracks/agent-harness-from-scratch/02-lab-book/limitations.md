# What this course demonstrates

This is an educational, inspectable harness over deterministic fixtures. Completion means you can trace decisions, extend boundaries, test failure paths, and justify changes. It does not certify production security, SRE operational readiness, or reliable arbitrary-model behavior.

A fake provider proves behavior for scripted replies. It does not prove a live model will select the same tools or give correct diagnoses. Mocked adapter contracts check parsing and request construction against controlled protocol samples; optional live smoke tests give limited evidence about one explicit endpoint/model at one time.

Application allowlists do not form an OS sandbox. An approved subprocess can execute code. Path and symlink policies do not eliminate adversarial races. Timeouts do not prove absence of effects. Queue deduplication has a documented identity/retention scope; it is not universal exactly-once delivery. Recovery must preserve uncertainty rather than fabricate a successful completion.

Estimated token usage and cost are advisory where exact values are unavailable. Missing usage is unknown, never automatically zero. A configured output bound is not a provider-enforced spending guarantee. Required exercises make no live paid requests.

The resident example is deliberately small: bounded active work, durable local state, inspectable admission, one worker before coordination, and a human stop. Active queue capacity is bounded, but stored events/completed tasks/deduplication keys persist for the database lifetime without a pruning policy; database size is not globally bounded. Scheduling uses elapsed UTC intervals with a display timezone rather than a full civil-time cron/DST engine. It does not promise distributed consensus, high availability, hardware-failure recovery, production secret management, or automatically safe third-party plugins.

## Authoring and validation status

No builds, tests, lint, hooks, or live-provider calls were run on the source-only authoring Mac. Read the repository/PR validation record for approved worker results and their exact commit. Lesson expected traces describe assertions to verify; they are not a claim that every command has already passed. Dependency pins and platform support must be interpreted against the versions actually tested.

Record beginner pilot feedback separately from automated checks. A clear solution is not evidence that an unaided beginner can complete the exercise. An unexplained test pass is not mastery.

## A useful completion explanation

“I can show the action that was proposed, why it was allowed or refused, the budget that bounded it, the effect we observed, and the uncertainty that remains.” Support that explanation with a trace and a test, then choose the next small extension of the same harness. There is no separate final project or capstone.
