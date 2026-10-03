# Agent Harness from Scratch

A self-paced Python course that grows one small harness from a deterministic model
reply into bounded coding, SRE, and resident automation workflows. No orchestration
frameworks, no capstones, and no paid calls in the default exercises.

Source implementation is in progress against [issue #5](https://github.com/maruthiprithivi/the-local-node/issues/5).
Start with the [course map](02-lab-book/course-map.md), [setup](02-lab-book/setup.md),
and [runnable labs](03-labs/README.md). Optional foundations and 28 lessons extend
one reference package, with learner deltas, hints, separate solutions, and offline
acceptance checks. See [validation evidence and remaining work](VALIDATION.md).
This course does not establish a production security boundary.

Four optional [advanced extensions](02-lab-book/advanced-extensions.md), lessons
29–32, add an isolated framework bridge, GitHub mention replay, shared team memory,
and collaboration between separately scoped harness instances. All required
checks still run offline. The core has no orchestration dependency.

## Learning materials

- `01-videos/`: video index; recordings are optional learning aids.
- `02-lab-book/`: progressive reading and exercise guide.
- `03-labs/`: one framework-free Python harness, fixtures, solutions, and checks.
- `04-video-source/`: lesson-aligned narration and source material.
- `assets/posters/`: course media assets.

The website is maintained separately under the repository's `website/` directory.

## Default execution contract

The exercises use a deterministic offline provider and synthetic files, service
health, alerts, and automation events. Students can inspect every decision without
API keys, model downloads, a GPU, or access to a real host. Optional live helpers
cover OpenAI, Gemini, DeepSeek, Ollama, and NVIDIA API LLMs. Live execution
requires an explicit opt-in and is separate from offline acceptance checks.

The same examples continue across lessons: a coding assistant examines a synthetic
repository, an SRE assistant observes synthetic service health before allowlisted
remediation, and a resident assistant handles synthetic events using durable state.
Autonomous mode still obeys budgets and tool policy; semi-autonomous mode pauses at
explicit approval gates.

## Validation status

This source checkout is on a Mac restricted to source/review work. No builds,
tests, lint, or hooks have been executed here. Runtime checks must run on a
parent-approved GCP Linux worker. No worker is currently confirmed. No cloud
resource, credential, grant, model call, or deployment is authorized by these materials.
