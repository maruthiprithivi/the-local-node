# Implementation and validation evidence

Specification: [issue #5](https://github.com/maruthiprithivi/the-local-node/issues/5)
and [authorized extensions](https://github.com/maruthiprithivi/the-local-node/issues/5#issuecomment-5964429655).
Source branch: `course/agent-harness-from-scratch-20261003`.
Verified base: `74e95ad67f74d6257b911efce9b7924cc6927031` (`main`, 2026-10-03).

## Source authored and reviewed

- Optional foundations plus 28 lessons, concrete learner deltas, progressive
  hints, separate solution snippets, diagrams/text equivalents, self-checks.
- Shared bounded controller, deterministic providers, contract validation,
  exact operation approvals, disposable coding tools, synthetic read-only SRE
  before allowlisted remediation, dry-run/allowlisted automation.
- Durable budget/action receipts, uncertain-effect reconciliation, bounded
  resident queue, deduplication, leases, retry/dead-letter, lifecycle/human stop,
  explicit elapsed-interval scheduling and cooperative worker limits.
- Memory/retention, bounded assembly, constrained handovers/configuration,
  trusted manifest gates, correlated redaction/usage, evaluations, read-only
  coordination, versioned cache and reviewed artifact promotion/rollback.
- Five provider helpers and synthetic contracts. Official references are in
  `03-labs/PROVIDERS.md`. Codex/Firstmate source claims are commit-pinned and
  licenses checked in lesson 28's `source-study.md`.
- Astro/Starlight course integration using existing versions and theme,
  canonical source syncing, navigation, self-check progress and recording fallback.
- Optional lessons29–32: separate pinned framework example, gated host operation
  bridge, signed offline mention replay to synthetic diff/check receipt/draft PR,
  authenticated fixture users sharing consented memory with conflicts/revocation,
  and bounded/fenced shared-task collaboration. No live integration activated.

Source review caught a premature SRE remediation exposure, a denied evaluation
baseline, missing native provider metadata, and nonfinite deadline budgets.
These were corrected in source; none is claimed to have passed execution.

## Actually executed

Repository/source/network reads, isolated sparse clone/branch creation, Git
inspection and source edits only. The host is Darwin `Maruthi-Mac.local`.
No tests, builds, lint, installs, active hooks, model calls, cloud provisioning,
merge, or deployment has run during this source-only implementation.

The clone had only Git sample hooks and no configured hooksPath. No guard was
disabled. No existing checkout or another agent's branch was modified.

## Pending validation and completion work

- Execute the entire Python suite, 99 checkpoints, and learner solution snippets
  on an approved GCP Linux worker; record Python version, ref and results.
- Execute `npm ci` and the new course build on Node 24; then assemble the whole
  website and inspect navigation/progress/accessibility. Full assembly needs the
  existing AI Field Engineer source/media; obtain it without modifying that track.
- Native live HTTP streaming remains unsupported; normalized offline stream
  assembly is an educational fixture boundary. Unsupported capabilities must
  fail clearly instead of silently downgrading.
- Recheck DeepSeek's full API/thinking references before live use: linked docs
  timed out during authoring; the official basic tool guide was accessible.
- Expand held-out task breadth, pilot the core path with a beginner, and address
  resulting teaching problems before declaring the course complete.
- Video narration is source text. Recordings, renders, captions of actual
  recordings, and poster media are pending; no empty media stands in for them.
- Live compatibility and actual billing are unverified. Fake token counts and
  injected logical clocks are not performance or cost measurements.

## Approved-worker needs

Python 3.11+, pytest 8.3.5, Node 24 and npm. No GPU or provider credentials.
A small Linux worker with 2 vCPU/4 GiB RAM is sufficient for planned checks;
allow disk for existing course media, npm dependencies and temporary fixtures.
Expected validation session is under one hour, subject to dependency downloads.
No worker/allocation or spend has been approved by these materials.

The parent separately obtained approval for one bounded GCP validation session
(Singapore Spot, at most one hour and US$2). Its sole provisioner is handling
authentication; this document does not authorize additional allocation or spend.

## Focused post-publication source repairs

Separate provider/controller duplicate-ID guards now have targeted fixtures and
negative-effect assertions. Context selection retains the complete current turn
or stops explicitly before a provider call. Synchronous Ollama length exhaustion
rejects truncated action proposals. Mention `plan` work completes read-only and
releases its queue claim before a later `fix`. These repairs are source-authored;
their regression tests remain unrun pending the approved worker.

Lessons 01/05/06 now begin with one learner-owned `exercises/harness.py`, not the
finished engine. Implement messages/reply validation, one dispatch, bounded loop
and external policy gates in phases. `solutions/early_harness.py` is the completed
reference. Default pytest includes `tests/unit/test_early_solutions.py`; explicit
`python -m pytest -q exercises/test_lesson_01.py` (then 05/06) selects deliberately
red starter tests until the learner implements each phase. Do not count those
initial red tests as a reference-suite regression.

From `03-labs/`, install the editable dev environment, then run
`sh scripts/validate.sh`. From `website/agent-harness-from-scratch/`, run
`npm ci --no-audit --no-fund` and `npm run build`. Then use the existing root
website build. These are a plan, not an execution report.
