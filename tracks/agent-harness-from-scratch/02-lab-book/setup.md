# Set up a disposable learning environment

Use Python 3.11 for the course baseline; [the lab project](../03-labs/pyproject.toml) declares Python >=3.11 and pins the development test dependency to pytest 8.3.5. The harness has no third-party runtime dependencies. Additional Python versions/platforms require their own recorded validation rather than an inferred pass. All required runs use a fake provider and synthetic fixtures. You do not need a GPU, model download, API account, or API key.

These commands are for the learner's own development machine or an approved validation worker. The Mac used to author this course is source-only: do not run tests, builds, lint, or hooks there.

From a fresh checkout, enter `tracks/agent-harness-from-scratch/03-labs`. On macOS/Linux:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m course_harness checkpoint 0 --scenario coding
pytest -q tests -k lesson_00
```

On Windows PowerShell, create the environment with `py -m venv .venv`, then activate with `.venv\Scripts\Activate.ps1`. If local policy prevents activation, use `.venv\Scripts\python.exe` directly; do not weaken a shared machine's policy. Use that interpreter for both `-m pip` and `-m pytest`.

An editable install makes your source changes visible without reinstalling. The dot means “this project,” not the entire repository. Installing development dependencies may need package-index access once; required exercise execution itself is offline. For disconnected workers, provision a reviewed wheel cache before entering the offline run.

Begin with [foundations](../03-labs/lessons/00-foundations/README.md) if functions, dictionaries, exceptions, or terminal paths are unfamiliar. Experienced learners can start at lesson 1, but still read [the threat model](threat-model.md).

## A repeatable working rhythm

1. Read the lesson and locate the named code. Predict the next trace before running it.
2. Run the checkpoint and its selected acceptance checks.
3. Make the smallest exercise edit on your own learning branch.
4. Add a test that would fail without your edit. Run it and inspect the Git diff.
5. Explain the permission boundary in a sentence before opening the solution.

A checkpoint selects cumulative behavior in one growing package. It does not overwrite your files or reset your branch. Keep exercise changes as small Git commits so you can return to a known version yourself. Do not use a destructive checkout or reset as a navigation command.

## Fixtures and state

Use a new temporary directory for mutable examples. Source fixtures are the reference inputs, not a place to store credentials or durable learner state. A coding workspace is a disposable copy of a toy repository; an SRE service is simulated classroom state; an automation artifact is a local temporary file. Never point course commands at a production service or personal repository.

Set no provider keys for required exercises. The existence of a key does not opt you into live use. Optional live experiments require the documented explicit live flag, chosen model and endpoint, and bounded request settings. Do not run them as acceptance checks.

## Platform notes

Path separators and case sensitivity differ. Use `pathlib` rather than concatenating slashes. Symlink exercises may require privileges on Windows; do not silently skip the policy assertion—use the test's supported fixture/skip explanation. A process timeout needs platform-specific process cleanup; POSIX process groups and Windows process management are not interchangeable. The restricted runner is a teaching example, not an OS sandbox.

## Evidence to record

Save Python version, commit identifier, scenario, checkpoint number, selected test command, and exit status. Separate expected output in a lesson from observed output in your own run. During initial authoring, commands and examples await approved Linux validation; none are claimed to have passed on the source-only Mac.
