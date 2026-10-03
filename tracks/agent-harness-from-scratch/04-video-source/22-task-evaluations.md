# Lesson 22 narration: Task outcomes and regression evidence

Transcript and recording script; no recording is claimed. Read the lab alongside
this text. Caption future recordings with these words and describe visual changes
aloud; do not rely on color or audio alone.

## Opening

Today we extend the same small Python harness. A code test says a component followed its contract. A task evaluation asks whether the goal was achieved safely. Record task ID, scenario, development/held-out split, executable outcome, unsafe attempts, steps, latency, usage and config/fixture versions. Held-out tasks are withheld during tuning; do not tune on their failures repeatedly.

## Describe the diagram

Versioned tasks produce outcomes and measurements, then a comparison checks individual regressions alongside totals. Read every arrow in order. The host-owned boundary is ordinary program
logic, visible outside the model's suggestions.

## Walk through source

Open advanced.py: Evaluation, evaluate and compare_evaluations; evals fixtures. Follow input values to the decision and then to the recorded
result. Add one denied or impossible task to the held-out fixtures. Its correct result may be a refusal or escalation, not completion. Compare baseline and candidate over the same task/split/fixture identities.

## Narrate the successful run

Say: baseline safe successes=3.

Say: candidate safe successes=3; fewer steps.

Say: same task/split/fixture IDs -> comparable.

Say: unsafe_attempts=0 -> candidate may be acceptable.

Run checkpoint 22 for coding, SRE and automation. Pause to inspect each result.
The lab's trace describes meaning, not exact terminal formatting.

## Investigate a failure

Make a candidate faster but introduce one unsafe attempt. evaluate must exclude that completion from successes; compare_evaluations must reject it even if aggregate latency improves. Ask learners to predict the effect count and recovery state before
showing the result. Leave time to try the progressive hints before revealing the
separate solution.

## Learner pause

Create coding, SRE and automation Evaluation records. Change one outcome from true to false and verify the task ID appears in regressions. Add a test proving mismatched fixture versions cannot be compared. Ask learners to write the acceptance test and explain:
Why can't a higher average success rate excuse a new permission failure? Explain how a held-out case differs from a unit test.

## Continuing

Compare two bounded context strategies across multiple fixture versions. Report sample size, tradeoffs and limits; fake evaluations do not establish live-model quality. This remains an incremental extension of the existing engine.

