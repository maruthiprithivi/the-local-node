# Framework-free harness labs

The growing `src/course_harness/` package contains an offline controller, five
provider helpers, tool contracts/policy, synthetic domains, durable resident
state, and advanced exercises. Runtime dependencies are Python's standard
library; `pytest==8.3.5` is the pinned development dependency. Python 3.11 is the
initial validation target, with platform differences described in [setup](../02-lab-book/setup.md).

Default examples do not open network connections or inspect the student's real
system. File exercises create temporary disposable workspaces. See
[PROVIDERS.md](PROVIDERS.md) for optional live boundaries.

## Start from a fresh checkout

On a learner machine or approved Linux worker:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
python -m course_harness checkpoint 1 --scenario coding
python -m pytest -q tests -k lesson_01
```

Required execution is offline; the initial dependency install can use a reviewed
package cache. Editable installation is required by the source-linked fixture
checkpoints. No command automatically downloads a model or uses environment keys.

Read [lesson 0](lessons/00-foundations/README.md) if Python or terminal use is new.
Then follow [the course map](../02-lab-book/course-map.md). `checkpoint N` exposes
an inspectable reference demonstration; it never overwrites your exercise files.
Each lesson specifies a small learner change plus a test to write separately.
The delivered final reference is for comparison, not a replacement for that work.

## Check a milestone

Each milestone maps to a terminal lesson: M0=0, M1=3, M2=5, M3=10,
M4=14, M5=20, M6=23, M7=28. Run that lesson for all three scenarios and
the acceptance suite as shown in the course map. To check all delivered references:

```sh
sh scripts/validate.sh
```

This runs pytest plus 99 checkpoint demonstrations. A printed `status: ok` is
a reference check result; it does not grade your exercise or assert live API
compatibility. Recorded execution evidence is required before a release claim.

## Code map

- `core.py`: controller, context bounding, retry/cancellation primitives.
- `providers.py`: fake and explicit live HTTP boundaries; native metadata.
- `tools.py`: validation, allow/deny/ask, synthetic domains, disposable files,
  exact course-owned command execution.
- `persistence.py` and `resident.py`: receipts, uncertainty, queue, leases,
  persistent human stop, schedules, and shared-engine tasks.
- `advanced.py`: memory, stream assembly, handovers, configuration, trusted
  manifest gates, read-only workers, cache, evaluations, promotion/rollback.
- `observability.py`: bounded redacted capture and unknown usage/cost.
- `extensions.py`: optional callback bridge and authenticated offline GitHub
  replay; the pinned optional SDK example is isolated under `examples/framework/`.
- `team.py`: single-host authenticated fixture memory service and fenced
  collaboration envelopes; no multi-host service is configured.
- `tests/`: unit, contract, integration, CLI/checkpoint, and adversarial cases.

Read the named function before introducing an abstraction. Native live HTTP
streaming and loading external plugin code remain unsupported; offline native
stream decoders/assembly and trusted manifest exercises teach their boundaries
without granting new authority. [Lessons 29–32](../02-lab-book/advanced-extensions.md)
are optional later extensions, not hidden prerequisites for the core.

Runtime validation is pending an approved GCP route. Do not run this repository's
build/test/lint/hook workloads on the source-only Mac used for this implementation.
