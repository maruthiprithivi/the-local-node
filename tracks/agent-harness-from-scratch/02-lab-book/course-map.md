# Course map

Build one harness in small increments. A harness is the program that supplies a
model with context, checks its requested actions, records results, and decides
when to stop. The model proposes; the host program supplies authority. There are
no capstones: the same coding, synthetic SRE, and resident automation examples
continue throughout the course.

Start with [setup](setup.md). Work from `03-labs/`, read a lesson, inspect the named
functions, make its small change on your own branch, and write the requested test.
The reference implementation and separate solutions provide a way back when
stuck. Checkpoint commands select a demonstration; they do not reset your files or
replace learner work. A later checkpoint may use shared code introduced earlier.

| Lesson | Increment | Progress |
|---|---|---|
| 0 | Optional Python, terminal, HTTP, Git and pytest foundations | M0 |
| 1 | Messages, fake responses and termination | M1 |
| 2 | Conversations and visible state | M1 |
| 3 | Shared API boundary and explicit live opt-in | M1 |
| 4 | Validated tool contracts | M2 |
| 5 | Controller with finite steps and calls | M2 |
| 6 | Trust labels, allow/deny/ask and exact approvals | M3 |
| 7 | Disposable coding workspace and stale patches | M3 |
| 8 | Read-only SRE evidence and uncertainty | M3 |
| 9 | Dry-run and bounded automation | M3 |
| 10 | Restricted commands and verified toy remediation | M3 |
| 11 | Bounded context and explicit truncation | M4 |
| 12 | Retry classification, cancellation and deadlines | M4 |
| 13 | Durable actions and reconciliation | M4 |
| 14 | Queue, deduplication, leases and resident lifecycle | M4 |
| 15 | Explicit memory, correction and retention | M5 |
| 16 | Five provider adapters and capability contracts | M5 |
| 17 | Assemble streams before tool dispatch | M5 |
| 18 | Constrained model handover | M5 |
| 19 | Validated configuration, skills and trusted plugins | M5 |
| 20 | Correlated traces, usage and service health | M5 |
| 21 | Unit, contract, integration and end-to-end checks | M6 |
| 22 | Outcome evaluations and held-out regression cases | M6 |
| 23 | Failure injection and adversarial fixtures | M6 |
| 24 | Two bounded workers with one coordinator | M7 |
| 25 | Versioned caches and measured efficiency | M7 |
| 26 | Resident operations and degradation | M7 |
| 27 | Reviewed improvement and rollback | M7 |
| 28 | Pinned public source study and one justified change | M7 |

Optional extensions continue the same engine after M0–M7:

| Lesson | Increment | Progress |
|---|---|---|
| 29 | Optional framework bridge with host-owned tools/policy/state | Extension |
| 30 | Authenticated GitHub mention replay to approved fake draft work | Extension |
| 31 | Two-user consented memory, versions, deletion and revocation | Extension |
| 32 | Separate harness envelopes, reauthorization, leases and fencing | Extension |

Read the corresponding folder under `03-labs/lessons/`. Each lesson gives a
diagram and text equivalent, a successful trace, an edge case, a small exercise,
progressive hints, and acceptance checks. Narration scripts are available in
`04-video-source/`; understanding does not depend on watching a recording.

Lessons 29–32 extend the completed framework-free mechanisms; the optional
framework stays in a separate example. Follow [advanced extensions](advanced-extensions.md)
for official source study and the distinction between offline fixtures and
separately authorized live integration. There are still no capstones.

For a progress checkpoint, run the lesson number ending the milestone for each
scenario, then the acceptance suite. For example, M4 uses lesson 14:

```sh
python -m course_harness checkpoint 14 --scenario coding
python -m course_harness checkpoint 14 --scenario sre
python -m course_harness checkpoint 14 --scenario automation
pytest -q tests
```

The commands are learner instructions. The authoring Mac is source-only; current
validation evidence lives in the track README. Do not interpret a printed example
or an authored test as a passing test report.

Take a useful stopping point at M4. Return for M5–M7 when you can explain the
controller, demonstrate a denied action, and recover an uncertain action without
blind repetition. No advanced module requires credentials, a model download,
production incidents, real personal files, or paid calls.

Use this rubric after every milestone:

- **Needs guidance:** I can follow the solution but cannot explain the boundary.
- **Independent:** I can complete the change, explain it, and write a useful test.
- **Advanced:** I can diagnose an unfamiliar failure and compare alternatives
  using traces and outcome evidence.

Written answers or narrated walkthroughs both count. If a result is surprising,
inspect the trace first, reproduce the smallest failure, and only then change the
implementation. Keep failed experiments: they are evidence about what the
harness can and cannot guarantee.
