# Build the early harness yourself

Edit only `harness.py` in lesson order: 01 messages/provider, 05 dispatch/ceilings, 06 permission gate. This is one evolving file; no finished `course_harness` imports or agent frameworks are used.

```sh
python -m pytest -q exercises/test_lesson_01.py
python -m pytest -q exercises/test_lesson_05.py
python -m pytest -q exercises/test_lesson_06.py
```

These tests intentionally fail with `NotImplementedError` until you implement the relevant TODOs. They are outside the default `testpaths = ["tests"]`, so the course reference suite does not silently execute unfinished learner code. Later phases depend on earlier phases. Save your edits in Git; checkpoint navigation never replaces this file.

Compare against `solutions/early_harness.py` after attempting the exercise. The default suite checks that reference with the same behavioral cases. Run `python -m pytest -q tests/unit/test_early_solutions.py` for that passing-reference contract.

Expected reference behavior is documented, not claimed executed on the authoring Mac. Use an ordinary learner machine or approved worker. The minimal protocol permits one call per reply and stops before another model call when the call ceiling is reached. It does not implement live transport, persistence, subprocess isolation, per-tool schemas, duplicate IDs across turns, cancellation, or retries; those belong to later boundaries in the growing course package.

