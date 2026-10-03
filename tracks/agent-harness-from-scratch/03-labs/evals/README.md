# Task outcome evaluations

`course_harness.advanced.Evaluation`, `evaluate`, and `compare_evaluations`
separate task outcomes from code correctness. Lesson 22 runs the actual offline
engine under a read-only policy and compares a successful observation with a
denied mutation. The injected logical clock supports reproducibility; it is not
a real latency benchmark. Token usage remains unknown when the fake omits it.

To extend the evaluation, define separate development and held-out task IDs for
each of coding, SRE, and automation. Check actual target state, permission failures,
and remaining budgets. An answer's wording is not an outcome check. Record the
fixture/configuration versions with every result. Use `tests/unit/test_advanced.py`
as the contract for comparison and per-task regression rejection.

No live evaluation or performance claim has been validated in this source-only
implementation. Held-out pedagogical task breadth still needs a learner pilot.
